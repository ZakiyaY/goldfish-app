import type { Brief, Evidence, FolderId, Meeting } from "./types";

export const FIXTURE_DATE = "2026-11-16";

const ev = (folder: FolderId, path: string, docDate: string, quote: string, matchedBy: string): Evidence => ({
  docId: path, folder, path, docDate, quote, matchedBy,
});

export const meetings: Meeting[] = [
  { id: "m1", title: "Team standup", start: "09:30", end: "10:00", attendees: [], briefReady: false },
  { id: "m2", title: "Roadmap review", start: "11:00", end: "12:00", attendees: ["Marcus Lee"], briefReady: true },
  { id: "m3", title: "1:1 with Priya", start: "14:00", end: "14:45", attendees: ["Priya Shah"], briefReady: true },
  { id: "m4", title: "Focus time", start: "15:30", end: "17:00", attendees: [], briefReady: false },
];

const notConnected = ["Outlook", "Teams", "OneNote"];

export const i3Reason = "Two notes give different interview weeks: w/c 24 Nov (12 Nov) and w/c 1 Dec (13 Nov).";
export const i3Evidence: Evidence[] = [
  ev("meetings", "meetings/design-sync.md", "2026-11-12", "Design role: interviews w/c 24 Nov.", "Priya named in note"),
  ev("meetings", "meetings/staff.md", "2026-11-13", "Design role: push interviews to w/c 1 Dec.", "Priya named in note"),
];
export const i5Evidence: Evidence = ev("hr-private", "hr-private/priya-leave-plan.md", "2026-11-04", "Parental leave: start 5 Jan 2027.", "Name in file name");

export const briefs: Record<string, Omit<Brief, "sourcesChecked">> = {
  m3: {
    meetingId: "m3", title: "1:1 with Priya", subject: "Priya Shah", notConnected,
    items: [
      { id: "i1", kind: "commitment", state: "clear", flags: [], text: "She asked for feedback on the Q3 roadmap draft.", reason: "Single clear mention.",
        evidence: [ev("1-1s", "1-1s/priya-2026-11-09.md", "2026-11-09", "Priya asked for feedback on the Q3 roadmap draft.", "Name in file name")] },
      { id: "i2", kind: "commitment", state: "check", flags: ["stale"], text: "Promotion conversation noted as promised 'after the offsite'.", reason: "Last mentioned 7 weeks ago. No later note says it happened.",
        evidence: [ev("1-1s", "1-1s/priya-2026-09-28.md", "2026-09-28", "Promotion chat after the offsite. Promised.", "Name in file name")] },
      { id: "i3", kind: "decision", state: "check", flags: ["conflict"], text: "Hiring plan for the design role.", reason: i3Reason, evidence: i3Evidence },
      { id: "i4", kind: "question", state: "not_found", flags: [], text: "Agreed date for her parental leave handover.", reason: "No note in the folders I can read gives a date.", evidence: [] },
      { id: "i5", kind: "commitment", state: "clear", flags: ["sensitive"], text: "Parental leave starts 5 Jan 2027.", reason: "From a private HR note. Handle with care.", evidence: [i5Evidence] },
    ],
  },
  m2: {
    meetingId: "m2", title: "Roadmap review", subject: "Marcus Lee", notConnected,
    items: [
      { id: "r1", kind: "decision", state: "clear", flags: [], text: "Ship search before dashboards.", reason: "Single clear mention.",
        evidence: [ev("meetings", "meetings/roadmap-2026-11-02.md", "2026-11-02", "Decision: search before dashboards.", "Meeting title match")] },
    ],
  },
};
