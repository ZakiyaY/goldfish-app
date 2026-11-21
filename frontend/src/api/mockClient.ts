import { briefs, i3Evidence as _i3, i3Evidence, i3Reason, i5Evidence, meetings } from "./fixtures";
import type { AskAnswer, Brief, CalendarStatus, Evidence, Folder, FolderId, GoldfishApi, Receipt, Req } from "./types";

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));
const emptyReceipt = (): Receipt => ({ filesRead: 0, bytesSentOffDevice: 0, blockedOutboundAttempts: 0, filesWrittenByAssistant: 0, itemsRetained: 0 });

// The mock learns which folders are on from the latest getMeetings call (made on every folder change).
let enabled: FolderId[] = ["calendar", "1-1s", "meetings", "inbox"];
const calStatus = (): CalendarStatus => enabled.includes("calendar")
  ? { state: "connected", sourceLabel: "Demo calendar (local .ics file)", lastReadAt: new Date().toISOString(), eventsToday: meetings.length, detail: "Read from a file on this laptop." }
  : { state: "off", sourceLabel: "", lastReadAt: null, eventsToday: 0, detail: "Calendar is off." };
const folderOf = (docId: string) =>
  [...Object.values(briefs).flatMap((b) => b.items.flatMap((i) => i.evidence)), ..._i3, i5Evidence].find((e) => e.path === docId)?.folder;

let lastPaths = { brief: new Set<string>(), ask: new Set<string>() };
const allowed = (e: Evidence, req: Req) => req.folders.includes(e.folder) && !req.excludedDocs.includes(e.path);

export const mockClient: GoldfishApi = {
  async getFolders(): Promise<Folder[]> {
    return [
      { id: "calendar", label: "Calendar", defaultEnabled: true, sensitive: false },
      { id: "1-1s", label: "1-1s", defaultEnabled: true, sensitive: false },
      { id: "meetings", label: "Meetings", defaultEnabled: true, sensitive: false },
      { id: "inbox", label: "Inbox", defaultEnabled: true, sensitive: false },
      { id: "hr-private", label: "HR-private", defaultEnabled: false, sensitive: true },
    ];
  },
  async getMeetings(_date, folders) {
    enabled = folders;
    return folders.includes("calendar") ? meetings : [];
  },
  async getBrief(meetingId, req) {
    await delay(500);
    const base = briefs[meetingId];
    const meeting = meetings.find((m) => m.id === meetingId);
    if (!base) {
      lastPaths.brief = new Set();
      return { meetingId, title: meeting?.title ?? "", subject: meeting?.attendees[0] ?? "", items: [], sourcesChecked: { notes: 0, folders: 0 }, notConnected: ["Outlook", "Teams", "OneNote"] };
    }
    const items = base.items
      .map((i) => ({ ...i, evidence: i.evidence.filter((e) => allowed(e, req)) }))
      .filter((i) => i.state === "not_found" || i.evidence.length > 0);
    const kept = items.flatMap((i) => i.evidence);
    lastPaths.brief = new Set(kept.map((e) => e.path));
    const brief: Brief = { ...base, items, sourcesChecked: { notes: lastPaths.brief.size, folders: new Set(kept.map((e) => e.folder)).size } };
    return brief;
  },
  async ask(question, req) {
    const q = question.toLowerCase();
    const searched = { notes: 0, folders: req.folders };
    let out: AskAnswer;
    if (q.includes("secondment")) {
      out = { question, state: "not_found", answer: null, reason: "Nothing in the folders I can read.", evidence: [], searched };
    } else if (q.includes("parental leave") && (q.includes("start") || q.includes("when"))) {
      out = allowed(i5Evidence, req)
        ? { question, state: "clear", answer: "Parental leave starts 5 Jan 2027.", reason: "From a private HR note. Handle with care.", evidence: [i5Evidence], searched }
        : { question, state: "not_found", answer: null, reason: "Nothing in the folders I can read.", evidence: [], searched };
    } else if (q.includes("design role") || q.includes("interview")) {
      out = { question, state: "check", answer: null, reason: i3Reason, evidence: i3Evidence, searched };
    } else {
      out = { question, state: "not_found", answer: null, reason: "Nothing in the folders I can read.", evidence: [], searched };
    }
    lastPaths.ask = new Set(out.evidence.map((e) => e.path));
    const readable = new Set([...Object.values(briefs).flatMap((b) => b.items.flatMap((i) => i.evidence)), ..._i3, i5Evidence].filter((e) => allowed(e, req)).map((e) => e.path));
    out.searched.notes = out.state === "not_found" ? readable.size : lastPaths.ask.size;
    return out;
  },
  async getReceipt() {
    return { ...emptyReceipt(), filesRead: new Set([...lastPaths.brief, ...lastPaths.ask]).size };
  },
  async getCalendarStatus() { return calStatus(); },
  async refreshCalendar() { await delay(400); return calStatus(); },
  async openSource(docId, mode) {
    const f = folderOf(docId);
    if (!f || !enabled.includes(f)) return { ok: false, message: "That folder is off." };
    await delay(300);
    return { ok: true, message: `Demo mode: would ${mode === "open" ? "open" : "show in its folder"} ${docId}` };
  },
  async openFolder(folder) {
    if (!enabled.includes(folder)) return { ok: false, message: "That folder is off." };
    await delay(300);
    return { ok: true, message: `Demo mode: would show the ${folder} folder` };
  },
  async wipeSession() {
    lastPaths = { brief: new Set(), ask: new Set() };
  },
};
