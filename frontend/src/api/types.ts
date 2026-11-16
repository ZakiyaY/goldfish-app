export type FolderId = "calendar" | "1-1s" | "meetings" | "inbox" | "hr-private";
export type ItemState = "clear" | "check" | "not_found";
export type Flag = "stale" | "conflict" | "ambiguous_owner" | "relative_date" | "low_ocr" | "sensitive";
export interface Evidence { docId: string; folder: FolderId; path: string; docDate: string; quote: string; matchedBy: string }
export interface BriefItem { id: string; kind: "commitment" | "decision" | "question"; text: string; state: ItemState; reason: string; flags: Flag[]; evidence: Evidence[] }
export interface Meeting { id: string; title: string; start: string; end: string; attendees: string[]; briefReady: boolean }
export interface Brief { meetingId: string; title: string; subject: string; items: BriefItem[]; sourcesChecked: { notes: number; folders: number }; notConnected: string[] }
export interface AskAnswer { question: string; state: ItemState; answer: string | null; reason: string; evidence: Evidence[]; searched: { notes: number; folders: FolderId[] } }
export interface Receipt { filesRead: number; bytesSentOffDevice: number; blockedOutboundAttempts: number; filesWrittenByAssistant: number; itemsRetained: number }
export interface Req { folders: FolderId[]; excludedDocs: string[] }
export interface GoldfishApi {
  getMeetings(date: string, folders: FolderId[]): Promise<Meeting[]>;
  getBrief(meetingId: string, req: Req): Promise<Brief>;
  ask(question: string, req: Req): Promise<AskAnswer>;
  getReceipt(): Promise<Receipt>;
  wipeSession(): Promise<void>;
  getCalendarStatus(): Promise<CalendarStatus>;
  refreshCalendar(): Promise<CalendarStatus>;
  openSource(docId: string, mode: OpenMode): Promise<OpenResult>;
  openFolder(folder: FolderId): Promise<OpenResult>;
}
export type CalendarState = "connected" | "off" | "needs_permission" | "file_missing" | "empty" | "error";
export interface CalendarStatus { state: CalendarState; sourceLabel: string; lastReadAt: string | null; eventsToday: number; detail: string }
export type OpenMode = "open" | "reveal";
export interface OpenResult { ok: boolean; message: string }
