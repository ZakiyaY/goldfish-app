from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


ItemState = Literal["clear", "check", "not_found"]
Flag = Literal["stale", "conflict", "ambiguous_owner", "relative_date", "low_ocr", "sensitive"]
CalendarState = Literal["connected", "off", "needs_permission", "file_missing", "empty", "error"]
OpenMode = Literal["open", "reveal"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Folder(StrictModel):
    id: str
    label: str
    defaultEnabled: bool
    sensitive: bool


class Evidence(StrictModel):
    docId: str
    folder: str
    path: str
    docDate: str
    quote: str
    matchedBy: str


class BriefItem(StrictModel):
    id: str
    kind: Literal["commitment", "decision", "question"]
    text: str
    state: ItemState
    reason: str
    flags: list[Flag]
    evidence: list[Evidence]


class Meeting(StrictModel):
    id: str
    title: str
    start: str
    end: str
    attendees: list[str]
    briefReady: bool


class SourcesChecked(StrictModel):
    notes: int
    folders: int


class Brief(StrictModel):
    meetingId: str
    title: str
    subject: str
    items: list[BriefItem]
    sourcesChecked: SourcesChecked
    notConnected: list[str]


class Searched(StrictModel):
    notes: int
    folders: list[str]


class AskAnswer(StrictModel):
    question: str
    state: ItemState
    answer: str | None
    reason: str
    evidence: list[Evidence]
    searched: Searched


class Receipt(StrictModel):
    filesRead: int
    bytesSentOffDevice: int
    blockedOutboundAttempts: int
    filesWrittenByAssistant: int
    itemsRetained: int


class BriefRequest(StrictModel):
    meetingId: str
    folders: list[str]
    excludedDocs: list[str]


class AskRequest(StrictModel):
    question: str
    folders: list[str]
    excludedDocs: list[str]


class CalendarStatus(StrictModel):
    state: CalendarState
    sourceLabel: str
    lastReadAt: str | None
    eventsToday: int
    detail: str


class OpenRequest(StrictModel):
    docId: str
    mode: OpenMode


class OpenFolderRequest(StrictModel):
    folder: str


class OpenResult(StrictModel):
    ok: bool
    message: str
