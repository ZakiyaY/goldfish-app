import socket

LOCAL_ONLY = {"127.0.0.1", "localhost", "::1"}

if not hasattr(socket, "_goldfish_blocked"):
    socket._goldfish_blocked = []
    _real_connect = socket.socket.connect
    _real_connect_ex = socket.socket.connect_ex

    def _is_local(address):
        return not isinstance(address, tuple) or str(address[0]) in LOCAL_ONLY

    def _guarded_connect(self, address):
        if not _is_local(address):
            socket._goldfish_blocked.append(str(address[0]))
            raise ConnectionRefusedError(f"Goldfish blocked a connection to {address[0]}")
        return _real_connect(self, address)

    def _guarded_connect_ex(self, address):
        if not _is_local(address):
            socket._goldfish_blocked.append(str(address[0]))
            return 61
        return _real_connect_ex(self, address)

    socket.socket.connect = _guarded_connect
    socket.socket.connect_ex = _guarded_connect_ex

import os
import platform
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
sys.dont_write_bytecode = True

import numpy as np
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from bridge.core import (
    CALENDAR_TYPE,
    TEXT_TYPES,
    Document,
    Session,
    brief_items,
    changed_file_count,
    default_folders,
    evidence_for_line,
    fingerprint,
    folder_records,
    list_files,
    load_documents,
    parse_ics,
    person_in,
)
from bridge.schemas import (
    AskAnswer,
    AskRequest,
    Brief,
    BriefRequest,
    CalendarStatus,
    Evidence,
    Folder,
    Meeting,
    OpenFolderRequest,
    OpenRequest,
    OpenResult,
    Receipt,
)


SOURCE_LABEL = "Demo calendar (local .ics file)"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
SESSION = Session()


def notes_root() -> Path:
    return Path(os.environ.get("NOTES_ROOT", "./GoldfishVault")).expanduser().resolve()


def _active_folders(root: Path, folder_ids: Iterable[str]) -> set[str]:
    requested = set(folder_ids)
    valid = {folder["id"] for folder in folder_records(root)}
    invalid = requested - valid
    if invalid:
        raise HTTPException(status_code=400, detail="One or more folder IDs are not available.")
    SESSION.enabled_folders = requested
    return requested


def _default_active_folders(root: Path) -> set[str]:
    if SESSION.enabled_folders is None:
        SESSION.enabled_folders = default_folders(root)
    return SESSION.enabled_folders


def _meeting_id(title: str, start: datetime) -> str:
    import hashlib

    return hashlib.sha256(f"{title}\0{start.isoformat()}".encode("utf-8")).hexdigest()[:16]


def _folder_names_for_people(root: Path, folder_ids: set[str]) -> list[str]:
    return [
        path.stem
        for path in list_files(root, folder_ids, TEXT_TYPES)
    ]


def _calendar_docs(
    root: Path,
    folder_ids: set[str],
    excluded_docs: Iterable[str] = (),
) -> list[Document]:
    calendar_folders = {
        folder_id for folder_id in folder_ids if folder_id.casefold() == "calendar"
    }
    return load_documents(root, calendar_folders, excluded_docs, SESSION, {CALENDAR_TYPE})


def _calendar_meetings(
    root: Path,
    folder_ids: set[str],
    selected_date: date | None = None,
    excluded_docs: Iterable[str] = (),
) -> list[dict]:
    if not any(folder.casefold() == "calendar" for folder in folder_ids):
        return []
    calendar_docs = _calendar_docs(root, folder_ids, excluded_docs)
    note_titles = _folder_names_for_people(root, folder_ids)
    meetings = []
    for document in calendar_docs:
        for event in parse_ics(document.text):
            start = event["start"]
            if selected_date is not None and start.date() != selected_date:
                continue
            person = person_in(event["title"], note_titles)
            meetings.append({
                "id": _meeting_id(event["title"], start),
                "title": event["title"],
                "start": start.strftime("%H:%M"),
                "end": event["end"].strftime("%H:%M"),
                "attendees": event["attendees"],
                "briefReady": person is not None,
                "_start": start,
            })
    meetings.sort(key=lambda meeting: (meeting["_start"], meeting["title"]))
    return meetings


def _search_model():
    if SESSION.embedding_model is None:
        from sentence_transformers import SentenceTransformer

        SESSION.embedding_model = SentenceTransformer(MODEL_NAME)
    return SESSION.embedding_model


def _evidence(document: Document, quote: str, matched_by: str) -> Evidence:
    return Evidence(**evidence_for_line(document, quote, matched_by))


def _calendar_status() -> CalendarStatus:
    root = notes_root()
    folders = _default_active_folders(root)
    calendar_folder = next(
        (folder for folder in folders if folder.casefold() == "calendar"),
        None,
    )
    if calendar_folder is None:
        return CalendarStatus(
            state="off",
            sourceLabel=SOURCE_LABEL,
            lastReadAt=SESSION.last_calendar_read_at,
            eventsToday=0,
            detail="Calendar is off.",
        )

    files = list_files(root, {calendar_folder}, {CALENDAR_TYPE})
    if not files:
        return CalendarStatus(
            state="file_missing",
            sourceLabel=SOURCE_LABEL,
            lastReadAt=SESSION.last_calendar_read_at,
            eventsToday=0,
            detail="No local .ics file was found in the Calendar folder.",
        )

    try:
        documents = _calendar_docs(root, {calendar_folder})
    except OSError:
        return CalendarStatus(
            state="error",
            sourceLabel=SOURCE_LABEL,
            lastReadAt=SESSION.last_calendar_read_at,
            eventsToday=0,
            detail="The local calendar file could not be read.",
        )

    SESSION.last_calendar_read_at = datetime.now().astimezone().isoformat(timespec="seconds")
    today = date.today()
    count = sum(
        event["start"].date() == today
        for document in documents
        for event in parse_ics(document.text)
    )
    return CalendarStatus(
        state="connected" if count else "empty",
        sourceLabel=SOURCE_LABEL,
        lastReadAt=SESSION.last_calendar_read_at,
        eventsToday=count,
        detail="Read from a file on this laptop." if count else "No events today in the local calendar file.",
    )


app = FastAPI(title="Goldfish local bridge", docs_url=None, redoc_url=None)

allowed_origins = [
    origin.strip().rstrip("/")
    for origin in os.environ.get(
        "GOLDFISH_ALLOWED_ORIGINS",
        "http://localhost:5173,http://localhost:4173,http://localhost:8080,http://127.0.0.1:5173,http://127.0.0.1:4173,http://127.0.0.1:8080",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def require_local_host(request: Request, call_next):
    host_header = request.headers.get("host", "")
    if host_header.startswith("["):
        hostname = host_header[1:].split("]", 1)[0].lower()
        valid_suffix = host_header[len(hostname) + 2:len(host_header) + 3] in {"", ":"}
        if not valid_suffix:
            raise HTTPException(status_code=400, detail="Invalid Host header.")
    else:
        hostname = host_header.rsplit(":", 1)[0] if host_header.count(":") == 1 else host_header
        hostname = hostname.lower()
    if hostname not in LOCAL_ONLY:
        return Response(status_code=400, content="Invalid Host header.")
    return await call_next(request)


@app.get("/api/folders", response_model=list[Folder])
def get_folders() -> list[Folder]:
    return [Folder(**folder) for folder in folder_records(notes_root())]


@app.get("/api/meetings", response_model=list[Meeting])
def get_meetings(date: date, folders: str = Query(default="")) -> list[Meeting]:
    root = notes_root()
    folder_ids = _active_folders(root, (item for item in folders.split(",") if item))
    meetings = _calendar_meetings(root, folder_ids, date)
    return [Meeting(**{key: value for key, value in meeting.items() if not key.startswith("_")}) for meeting in meetings]


@app.post("/api/brief", response_model=Brief)
def get_brief(request: BriefRequest) -> Brief:
    root = notes_root()
    folder_ids = _active_folders(root, request.folders)
    documents = load_documents(root, folder_ids, request.excludedDocs, SESSION, TEXT_TYPES)
    meetings = _calendar_meetings(root, folder_ids, excluded_docs=request.excludedDocs)
    meeting = next((item for item in meetings if item["id"] == request.meetingId), None)
    title = meeting["title"] if meeting else ""
    subject = person_in(title, (document.title for document in documents)) if title else None
    items = brief_items(subject, documents) if subject else []
    used_folders = {document.folder for document in documents}
    return Brief(
        meetingId=request.meetingId,
        title=title,
        subject=subject or title,
        items=items,
        sourcesChecked={"notes": len(documents), "folders": len(used_folders)},
        notConnected=["Outlook", "Teams", "OneNote"],
    )


@app.post("/api/ask", response_model=AskAnswer)
def ask(request: AskRequest) -> AskAnswer:
    root = notes_root()
    folder_ids = _active_folders(root, request.folders)
    documents = load_documents(root, folder_ids, request.excludedDocs, SESSION)
    lines: list[tuple[str, Document]] = []
    for document in documents:
        for line in document.text.splitlines():
            quote = line.strip()
            if len(quote.split()) >= 3:
                lines.append((quote, document))

    searched_folders = sorted({document.folder for _, document in lines})
    searched = {"notes": len(documents), "folders": searched_folders}
    if not lines:
        return AskAnswer(
            question=request.question,
            state="not_found",
            answer=None,
            reason="Nothing in the 0 notes I can read matches that.",
            evidence=[],
            searched=searched,
        )

    try:
        embeddings = _search_model().encode(
            [request.question, *(line for line, _ in lines)],
            normalize_embeddings=True,
        )
    except (ImportError, OSError) as exc:
        raise HTTPException(
            status_code=503,
            detail="The local search model is not installed or cached for offline use.",
        ) from exc
    scores = np.asarray(embeddings[1:]) @ np.asarray(embeddings[0])
    best_index = int(np.argmax(scores))
    score = float(scores[best_index])
    if score < 0.38:
        return AskAnswer(
            question=request.question,
            state="not_found",
            answer=None,
            reason=f"Nothing in the {len(documents)} notes I can read matches that.",
            evidence=[],
            searched=searched,
        )

    quote, document = lines[best_index]
    state = "clear" if score >= 0.50 else "check"
    return AskAnswer(
        question=request.question,
        state=state,
        answer=quote,
        reason="A note line matched this question." if state == "clear" else "This is the closest matching note line; check its context.",
        evidence=[_evidence(document, quote, "Local semantic match")],
        searched=searched,
    )


@app.get("/api/receipt", response_model=Receipt)
def get_receipt() -> Receipt:
    root = notes_root()
    current = fingerprint(root) if SESSION.initial_snapshot is not None else {}
    return Receipt(
        filesRead=len(SESSION.read_files),
        bytesSentOffDevice=0,
        blockedOutboundAttempts=len(socket._goldfish_blocked),
        filesWrittenByAssistant=changed_file_count(SESSION.initial_snapshot, current),
        itemsRetained=0,
    )


@app.post("/api/session/wipe", status_code=204)
def wipe_session() -> Response:
    SESSION.clear()
    socket._goldfish_blocked.clear()
    return Response(status_code=204)


@app.get("/api/calendar/status", response_model=CalendarStatus)
def calendar_status() -> CalendarStatus:
    return _calendar_status()


@app.post("/api/calendar/refresh", response_model=CalendarStatus)
def refresh_calendar() -> CalendarStatus:
    return _calendar_status()


def _open_command(path: Path, reveal: bool) -> list[str]:
    system = platform.system()
    if system == "Windows":
        return ["explorer.exe", "/select," if reveal else "", str(path)] if reveal else ["explorer.exe", str(path)]
    if system == "Darwin":
        return ["open", "-R", str(path)] if reveal else ["open", str(path)]
    return ["xdg-open", str(path.parent if reveal else path)]


def _run_open(path: Path, reveal: bool) -> OpenResult:
    subprocess.Popen(_open_command(path, reveal), shell=False)
    return OpenResult(ok=True, message="Opened locally.")


@app.post("/api/open", response_model=OpenResult)
def open_source(request: OpenRequest) -> OpenResult:
    root = notes_root()
    path = (root / request.docId).resolve()
    if not _inside_root(path, root):
        return OpenResult(ok=False, message="That source is not available.")
    if path.suffix.lower() not in {".md", ".txt", ".ics", ".png", ".jpg", ".jpeg"}:
        return OpenResult(ok=False, message="That file type cannot be opened.")
    relative = path.relative_to(root).as_posix()
    folder = relative.split("/", 1)[0]
    enabled = _default_active_folders(root)
    if folder not in enabled or not path.is_file():
        return OpenResult(ok=False, message="That folder is off or the source is unavailable.")
    return _run_open(path, request.mode == "reveal")


@app.post("/api/open-folder", response_model=OpenResult)
def open_folder(request: OpenFolderRequest) -> OpenResult:
    root = notes_root()
    folders = {folder["id"] for folder in folder_records(root)}
    path = (root / request.folder).resolve()
    if request.folder not in folders or request.folder not in _default_active_folders(root):
        return OpenResult(ok=False, message="That folder is off or unavailable.")
    if not _inside_root(path, root) or not path.is_dir():
        return OpenResult(ok=False, message="That folder is unavailable.")
    return _run_open(path, False)


def _inside_root(path: Path, root: Path) -> bool:
    try:
        return os.path.commonpath((str(root.resolve()), str(path.resolve()))) == str(root.resolve())
    except ValueError:
        return False
