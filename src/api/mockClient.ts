import { briefs, i3Evidence, i3Reason, i5Evidence, meetings } from "./fixtures";
import type { AskAnswer, Brief, Evidence, GoldfishApi, Receipt, Req } from "./types";

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));
const emptyReceipt = (): Receipt => ({ filesRead: 0, bytesSentOffDevice: 0, blockedOutboundAttempts: 0, filesWrittenByAssistant: 0, itemsRetained: 0 });

let lastPaths = { brief: new Set<string>(), ask: new Set<string>() };
const allowed = (e: Evidence, req: Req) => req.folders.includes(e.folder) && !req.excludedDocs.includes(e.path);

export const mockClient: GoldfishApi = {
  async getMeetings(_date, folders) {
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
    out.searched.notes = lastPaths.ask.size;
    return out;
  },
  async getReceipt() {
    return { ...emptyReceipt(), filesRead: new Set([...lastPaths.brief, ...lastPaths.ask]).size };
  },
  async wipeSession() {
    lastPaths = { brief: new Set(), ask: new Set() };
  },
};
