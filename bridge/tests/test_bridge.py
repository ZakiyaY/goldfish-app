from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bridge import main
from bridge.core import fingerprint, parse_ics


ROOT = Path(__file__).resolve().parents[2] / "GoldfishVault"
CLIENT = TestClient(main.app, headers={"host": "127.0.0.1:8000"})


class FakeEmbeddingModel:
    def encode(self, texts, **kwargs):
        assert kwargs["normalize_embeddings"] is True
        if "secondment" in texts[0].casefold():
            return main.np.asarray([[1.0, 0.0]] + [[0.0, 1.0]] * (len(texts) - 1))
        return main.np.asarray([[1.0, 0.0]] * len(texts))


@pytest.fixture(autouse=True)
def reset_session(monkeypatch):
    monkeypatch.setenv("NOTES_ROOT", str(ROOT))
    main.SESSION.clear()
    main.SESSION.embedding_model = FakeEmbeddingModel()
    main.socket._goldfish_blocked.clear()
    yield
    main.SESSION.clear()


def _meeting_id() -> str:
    response = CLIENT.get(
        "/api/meetings",
        params={"date": date.today().isoformat(), "folders": "Calendar,People,Meetings,Inbox"},
    )
    assert response.status_code == 200
    meeting = next(item for item in response.json() if "Priya" in item["title"])
    return meeting["id"]


def test_folders_use_real_vault_names_and_sensitive_default():
    response = CLIENT.get("/api/folders")

    assert response.status_code == 200
    folders = {item["id"]: item for item in response.json()}
    assert {"Attachments", "Calendar", "Inbox", "Meetings", "People"} <= folders.keys()
    assert folders["People"]["defaultEnabled"] is True
    assert folders["People"]["sensitive"] is False


def test_hidden_folders_are_skipped_and_sensitive_folders_default_off(tmp_path, monkeypatch):
    (tmp_path / "HR-private").mkdir()
    (tmp_path / "Notes").mkdir()
    (tmp_path / ".hidden").mkdir()
    monkeypatch.setenv("NOTES_ROOT", str(tmp_path))

    folders = {item["id"]: item for item in CLIENT.get("/api/folders").json()}

    assert set(folders) == {"HR-private", "Notes"}
    assert folders["HR-private"]["sensitive"] is True
    assert folders["HR-private"]["defaultEnabled"] is False


def test_brief_quotes_are_exact_source_substrings_and_exclusions_apply():
    meeting_id = _meeting_id()
    folders = ["Calendar", "People", "Meetings", "Inbox"]
    brief = CLIENT.post(
        "/api/brief",
        json={"meetingId": meeting_id, "folders": folders, "excludedDocs": []},
    ).json()
    without_inbox = CLIENT.post(
        "/api/brief",
        json={"meetingId": meeting_id, "folders": ["Calendar", "People", "Meetings"], "excludedDocs": []},
    ).json()

    assert brief["subject"] == "Priya"
    assert brief["items"]
    assert any(item["evidence"][0]["folder"] == "Inbox" for item in brief["items"])
    assert all(
        evidence["quote"] in (ROOT / evidence["path"]).read_text(encoding="utf-8")
        for item in brief["items"]
        for evidence in item["evidence"]
    )
    assert all(
        evidence["path"] != "Inbox/todo.md"
        for item in without_inbox["items"]
        for evidence in item["evidence"]
    )


def test_ics_end_time_falls_back_to_thirty_minutes_and_attendees_default_empty():
    event = parse_ics(
        "BEGIN:VCALENDAR\nBEGIN:VEVENT\nSUMMARY:One to one\n"
        "DTSTART:20261121T120000\nEND:VEVENT\nEND:VCALENDAR\n"
    )[0]

    assert (event["end"] - event["start"]).total_seconds() == 1800
    assert event["attendees"] == []


def test_unknown_person_has_no_brief_items(tmp_path, monkeypatch):
    calendar = tmp_path / "Calendar"
    calendar.mkdir()
    (calendar / "unknown.ics").write_text(
        "BEGIN:VCALENDAR\nBEGIN:VEVENT\nSUMMARY:1:1 with Alex\n"
        "DTSTART:20261121T120000\nEND:VEVENT\nEND:VCALENDAR\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("NOTES_ROOT", str(tmp_path))
    main.SESSION.clear()
    meetings = CLIENT.get(
        "/api/meetings",
        params={"date": "2026-11-21", "folders": "Calendar"},
    ).json()

    brief = CLIENT.post(
        "/api/brief",
        json={"meetingId": meetings[0]["id"], "folders": ["Calendar"], "excludedDocs": []},
    ).json()

    assert brief["subject"] == "1:1 with Alex"
    assert brief["items"] == []


def test_ask_secondment_is_not_found():
    response = CLIENT.post(
        "/api/ask",
        json={
            "question": "What do my notes say about secondment?",
            "folders": ["People", "Meetings", "Inbox"],
            "excludedDocs": [],
        },
    )

    assert response.status_code == 200
    assert response.json()["state"] == "not_found"
    assert response.json()["answer"] is None


def test_ask_returns_an_exact_source_line():
    response = CLIENT.post(
        "/api/ask",
        json={
            "question": "When does the Priya course booking close?",
            "folders": ["People", "Meetings", "Inbox"],
            "excludedDocs": [],
        },
    )

    answer = response.json()
    assert answer["state"] in {"clear", "check"}
    evidence = answer["evidence"][0]
    assert evidence["quote"] == answer["answer"]
    assert evidence["quote"] in (ROOT / evidence["path"]).read_text(encoding="utf-8")


def test_ask_returns_service_error_when_offline_model_is_unavailable(monkeypatch):
    def no_local_model():
        raise OSError("model weights missing")

    monkeypatch.setattr(main, "_search_model", no_local_model)
    main.SESSION.embedding_model = None

    response = CLIENT.post(
        "/api/ask",
        json={"question": "anything?", "folders": ["People"], "excludedDocs": []},
    )

    assert response.status_code == 503
    assert "offline" in response.json()["detail"]


def test_all_read_endpoints_leave_vault_fingerprint_unchanged():
    before = fingerprint(ROOT)
    meeting_id = _meeting_id()
    request = {
        "meetingId": meeting_id,
        "folders": ["Calendar", "People", "Meetings", "Inbox"],
        "excludedDocs": [],
    }

    assert CLIENT.get("/api/folders").status_code == 200
    assert CLIENT.post("/api/brief", json=request).status_code == 200
    assert CLIENT.post(
        "/api/ask",
        json={"question": "When does the Priya course booking close?", "folders": request["folders"], "excludedDocs": []},
    ).status_code == 200
    assert CLIENT.get("/api/receipt").status_code == 200
    assert CLIENT.get("/api/calendar/status").status_code == 200
    assert CLIENT.post("/api/calendar/refresh", json={}).status_code == 200

    assert fingerprint(ROOT) == before


def test_receipt_counts_changed_and_added_paths_from_initial_snapshot(tmp_path, monkeypatch):
    inbox = tmp_path / "Inbox"
    inbox.mkdir()
    note = inbox / "note.md"
    note.write_text("An original local note line.", encoding="utf-8")
    monkeypatch.setenv("NOTES_ROOT", str(tmp_path))

    CLIENT.post(
        "/api/ask",
        json={"question": "find a note line", "folders": ["Inbox"], "excludedDocs": []},
    )
    note.write_text("A changed local note line.", encoding="utf-8")
    (inbox / "added.md").write_text("A newly added note line.", encoding="utf-8")

    receipt = CLIENT.get("/api/receipt").json()

    assert receipt["filesWrittenByAssistant"] == 2


def test_open_source_uses_only_enabled_paths_and_never_a_shell(tmp_path, monkeypatch):
    people = tmp_path / "People"
    people.mkdir()
    note = people / "Priya.md"
    note.write_text("A local note.", encoding="utf-8")
    monkeypatch.setenv("NOTES_ROOT", str(tmp_path))
    main.SESSION.enabled_folders = {"People"}
    calls = []
    monkeypatch.setattr(main.subprocess, "Popen", lambda args, **kwargs: calls.append((args, kwargs)))

    opened = CLIENT.post("/api/open", json={"docId": "People/Priya.md", "mode": "open"}).json()
    escaped = CLIENT.post("/api/open", json={"docId": "../outside.txt", "mode": "open"}).json()

    assert opened["ok"] is True
    assert calls[0][1]["shell"] is False
    assert escaped["ok"] is False


def test_wipe_returns_empty_204_and_resets_receipt():
    _meeting_id()
    assert main.SESSION.read_files
    response = CLIENT.post("/api/session/wipe", json={})

    assert response.status_code == 204
    assert response.content == b""
    receipt = CLIENT.get("/api/receipt").json()
    assert receipt == {
        "filesRead": 0,
        "bytesSentOffDevice": 0,
        "blockedOutboundAttempts": 0,
        "filesWrittenByAssistant": 0,
        "itemsRetained": 0,
    }


def test_host_header_must_be_local():
    response = CLIENT.get("/api/folders", headers={"host": "example.com"})

    assert response.status_code == 400
