"""Pure helpers for the local bridge, adapted from app.py."""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


TEXT_TYPES = {".md", ".txt"}
CALENDAR_TYPE = ".ics"
READABLE_TYPES = TEXT_TYPES | {CALENDAR_TYPE}
PROMISE_WORDS = re.compile(
    r"need to tell|told (her|him|them) i|i said i|look into|follow up|chase|"
    r"get back to|remind (her|him|them)|still to|\(did i\?\)",
    re.I,
)
SENSITIVE_FOLDER = re.compile(r"(?:^|[^a-z])(?:hr|private|confidential)(?:$|[^a-z])", re.I)
RELATIVE_DATE = re.compile(
    r"\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|next\s+week)\b",
    re.I,
)
ALIAS_LINE = re.compile(r"aliases:\s*\[([^\]]*)\]", re.I)
UNTICKED_TASK = re.compile(r"^(?:[-*]\s*)?\[ \]\s*.+")
ATTENDEE_CN = re.compile(r"(?:^|;)CN=(?:\"([^\"]+)\"|([^;:]+))", re.I)


@dataclass
class Session:
    """Session-only counters and cached model; note text is never retained here."""

    read_files: set[str] = field(default_factory=set)
    initial_snapshot: dict[str, str] | None = None
    enabled_folders: set[str] | None = None
    last_calendar_read_at: str | None = None
    embedding_model: Any = None

    def clear(self) -> None:
        self.read_files.clear()
        self.initial_snapshot = None
        self.enabled_folders = None
        self.last_calendar_read_at = None
        self.embedding_model = None


@dataclass(frozen=True)
class Document:
    doc_id: str
    folder: str
    path: Path
    title: str
    modified_at: float
    text: str


def hidden(path: Path, root: Path) -> bool:
    """True for hidden files and anything inside a hidden folder."""
    return any(part.startswith(".") for part in path.relative_to(root).parts)


def _is_inside(path: Path, root: Path) -> bool:
    root_path = str(root.resolve())
    try:
        return os.path.commonpath((root_path, str(path.resolve()))) == root_path
    except ValueError:
        return False


def fingerprint(root: Path) -> dict[str, str]:
    """Hash visible paths and bytes without retaining their contents."""
    root = root.resolve()
    result: dict[str, str] = {}
    if not root.is_dir():
        return result
    for path in sorted(root.rglob("*")):
        if not path.is_file() or hidden(path, root) or not _is_inside(path, root):
            continue
        relative = path.relative_to(root).as_posix()
        result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def changed_file_count(before: dict[str, str] | None, after: dict[str, str]) -> int:
    if before is None:
        return 0
    paths = before.keys() | after.keys()
    return sum(before.get(path) != after.get(path) for path in paths)


def ago(when: float, now: datetime | None = None) -> str:
    now = now or datetime.now()
    days = (now - datetime.fromtimestamp(when)).days
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 14:
        return f"{days} days ago"
    if days < 70:
        return f"{round(days / 7)} weeks ago"
    return f"{round(days / 30)} months ago"


def folder_records(root: Path) -> list[dict[str, Any]]:
    root = root.resolve()
    if not root.is_dir():
        return []
    records = []
    for path in sorted(root.iterdir(), key=lambda item: item.name.casefold()):
        if not path.is_dir() or path.name.startswith(".") or not _is_inside(path, root):
            continue
        sensitive = bool(SENSITIVE_FOLDER.search(path.name))
        records.append({
            "id": path.name,
            "label": path.name,
            "defaultEnabled": not sensitive,
            "sensitive": sensitive,
        })
    return records


def normalize_folders(root: Path, folder_ids: Iterable[str]) -> set[str]:
    known = {folder["id"] for folder in folder_records(root)}
    return set(folder_ids) & known


def default_folders(root: Path) -> set[str]:
    return {folder["id"] for folder in folder_records(root) if folder["defaultEnabled"]}


def list_files(
    root: Path,
    folder_ids: Iterable[str],
    suffixes: set[str] = READABLE_TYPES,
) -> list[Path]:
    root = root.resolve()
    folders = normalize_folders(root, folder_ids)
    paths: list[Path] = []
    for folder_id in sorted(folders):
        folder = root / folder_id
        for path in sorted(folder.rglob("*")):
            if (
                path.is_file()
                and path.suffix.lower() in suffixes
                and not hidden(path, root)
                and _is_inside(path, root)
            ):
                paths.append(path)
    return paths


def load_documents(
    root: Path,
    folder_ids: Iterable[str],
    excluded_docs: Iterable[str],
    session: Session,
    suffixes: set[str] = READABLE_TYPES,
) -> list[Document]:
    root = root.resolve()
    if session.initial_snapshot is None:
        session.initial_snapshot = fingerprint(root)
    excluded = {item.replace("\\", "/") for item in excluded_docs}
    documents = []
    for path in list_files(root, folder_ids, suffixes):
        doc_id = path.relative_to(root).as_posix()
        if doc_id in excluded:
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        stat = path.stat()
        session.read_files.add(doc_id)
        documents.append(Document(
            doc_id=doc_id,
            folder=path.relative_to(root).parts[0],
            path=path,
            title=path.stem,
            modified_at=stat.st_mtime,
            text=text,
        ))
    return documents


def _unescape_ics(value: str) -> str:
    return (
        value.replace("\\,", ",")
        .replace("\\;", ";")
        .replace("\\n", " ")
        .replace("\\N", " ")
        .replace("\\\\", "\\")
    ).strip()


def _parse_ics_datetime(value: str, tzid: str | None = None) -> datetime | None:
    try:
        if len(value) == 8:
            return datetime.combine(datetime.strptime(value, "%Y%m%d").date(), time.min)
        parsed = datetime.strptime(value[:15], "%Y%m%dT%H%M%S")
    except ValueError:
        return None

    if value.endswith("Z"):
        return parsed.replace(tzinfo=timezone.utc).astimezone().replace(tzinfo=None)
    if tzid:
        try:
            from zoneinfo import ZoneInfo

            return parsed.replace(tzinfo=ZoneInfo(tzid)).astimezone().replace(tzinfo=None)
        except (KeyError, ValueError):
            return None
    return parsed


def parse_ics(text: str) -> list[dict[str, Any]]:
    """Read local .ics events, including end times and attendees."""
    unfolded = text.replace("\r\n", "\n").replace("\n ", "").replace("\n\t", "")
    events: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for line in unfolded.split("\n"):
        line = line.strip()
        if line == "BEGIN:VEVENT":
            current = {"attendees": []}
            continue
        if line == "END:VEVENT":
            if current and current.get("start"):
                current.setdefault("title", "(no title)")
                current.setdefault("end", current["start"] + timedelta(minutes=30))
                events.append(current)
            current = None
            continue
        if current is None or ":" not in line:
            continue

        key, value = line.split(":", 1)
        field_name = key.split(";", 1)[0].upper()
        params = key.split(";")[1:]
        tzid = next((p.split("=", 1)[1].strip('"') for p in params if p.upper().startswith("TZID=")), None)
        if field_name == "SUMMARY":
            current["title"] = _unescape_ics(value) or "(no title)"
        elif field_name in {"DTSTART", "DTEND"}:
            parsed = _parse_ics_datetime(value.strip(), tzid)
            if parsed is not None:
                current["start" if field_name == "DTSTART" else "end"] = parsed
        elif field_name == "ATTENDEE":
            match = ATTENDEE_CN.search(key)
            attendee = _unescape_ics(match.group(1) or match.group(2)) if match else value.removeprefix("mailto:")
            if attendee and attendee not in current["attendees"]:
                current["attendees"].append(attendee)

    return sorted(events, key=lambda event: event["start"])


def person_in(title: str, note_titles: Iterable[str]) -> str | None:
    names = {
        name for name in note_titles
        if len(name) >= 3 and len(name.split()) <= 2
    }
    for name in sorted(names, key=len, reverse=True):
        if re.search(rf"(?<![A-Za-z]){re.escape(name)}(?![A-Za-z])", title, re.I):
            return name
    return None


def aliases_for(name: str, documents: Iterable[Document]) -> list[str]:
    aliases: list[str] = []
    for document in documents:
        if document.title.casefold() != name.casefold():
            continue
        match = ALIAS_LINE.search(document.text)
        if match:
            aliases.extend(
                alias.strip().strip("\"'")
                for alias in match.group(1).split(",")
                if alias.strip()
            )
    return aliases


def refers_to(text: str, name: str, aliases: Iterable[str]) -> bool:
    if name.casefold() in text.casefold():
        return True
    return any(
        re.search(rf"(?<![A-Za-z]){re.escape(alias)}(?![A-Za-z])", text, re.I)
        for alias in aliases
    )


def _matched_by(text: str, aliases: list[str]) -> str:
    if any(re.search(rf"(?<![A-Za-z]){re.escape(alias)}(?![A-Za-z])", text, re.I) for alias in aliases):
        return "Alias in note"
    return "Name in note"


def brief_items(name: str, documents: list[Document], today: date | None = None) -> list[dict[str, Any]]:
    today = today or date.today()
    aliases = aliases_for(name, documents)
    items: list[tuple[float, str, int, dict[str, Any]]] = []

    for document in documents:
        first_line = next((line.strip() for line in document.text.splitlines() if line.strip()), "")
        about_person = refers_to(f"{document.title} {first_line}", name, aliases)
        doc_date = datetime.fromtimestamp(document.modified_at).date()
        age_days = max(0, (today - doc_date).days)
        for line_number, raw_line in enumerate(document.text.splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            task = bool(UNTICKED_TASK.match(line))
            if task and refers_to(line, name, aliases):
                kind = "task"
                matched_by = "Task names the person"
            elif PROMISE_WORDS.search(line) and (
                refers_to(line, name, aliases) or about_person
            ):
                kind = "promise"
                matched_by = _matched_by(line if refers_to(line, name, aliases) else first_line, aliases)
            else:
                continue

            flags = []
            reason = (
                "Unticked task in your notes."
                if kind == "task"
                else "Your own words suggest a promise. I can't tell from this note whether it was done."
            )
            if age_days >= 28:
                flags.append("stale")
                reason += f" This note is {age_days} days old."
            if RELATIVE_DATE.search(line):
                flags.append("relative_date")
            if SENSITIVE_FOLDER.search(document.folder):
                flags.append("sensitive")

            item_id = hashlib.sha256(
                f"{document.doc_id}\0{line_number}\0{kind}".encode("utf-8")
            ).hexdigest()[:16]
            item = {
                "id": item_id,
                "kind": "commitment",
                "text": line,
                "state": "clear" if kind == "task" else "check",
                "reason": reason,
                "flags": flags,
                "evidence": [{
                    "docId": document.doc_id,
                    "folder": document.folder,
                    "path": document.doc_id,
                    "docDate": doc_date.isoformat(),
                    "quote": line,
                    "matchedBy": matched_by,
                }],
            }
            items.append((document.modified_at, document.doc_id, line_number, item))

    items.sort(key=lambda result: (result[0], result[1], result[2]))
    return [item for _, _, _, item in items[:8]]


def evidence_for_line(document: Document, quote: str, matched_by: str) -> dict[str, str]:
    return {
        "docId": document.doc_id,
        "folder": document.folder,
        "path": document.doc_id,
        "docDate": datetime.fromtimestamp(document.modified_at).date().isoformat(),
        "quote": quote,
        "matchedBy": matched_by,
    }
