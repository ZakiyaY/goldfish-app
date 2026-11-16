// Typed client for the Goldfish local service.
export const BASE_URL = "http://127.0.0.1:8000";
export const USE_MOCKS = true;

export type Folder = { id: string; name: string; enabled: boolean };
export type FoldersResponse = {
  folders: Folder[];
  memory: string;
  receipt: { bytesLeftDevice: number; kept: string };
};
export type ItemState = "clear" | "check" | "not_found";
export type Source = { date: string; file: string; quote: string };
export type BriefItem = { id: string; text: string; state: ItemState; stale: boolean; ageLabel?: string; sources: Source[] };
export type Brief = { person: string; time: string; items: BriefItem[] };
export type CalendarEvent = { id: string; title: string; start: string; end: string; briefReady?: boolean };
export type CalendarDay = { date: string; events: CalendarEvent[] };
export type AskResponse = { answer: string; sources: Source[] };

async function get<T>(path: string, mock: string): Promise<T> {
  const url = USE_MOCKS ? `/mocks/${mock}.json` : `${BASE_URL}${path}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return res.json() as Promise<T>;
}

export const api = {
  folders: () => get<FoldersResponse>("/folders", "folders"),
  brief: (eventId: string) => get<Brief>(`/brief/${eventId}`, "brief"),
  calendar: (date: string) => get<CalendarDay>(`/calendar/${date}`, "calendar"),
  async ask(question: string): Promise<AskResponse> {
    if (USE_MOCKS) return { answer: `No notes matched “${question}”.`, sources: [] };
    const res = await fetch(`${BASE_URL}/ask`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question }) });
    if (!res.ok) throw new Error(`Request failed (${res.status})`);
    return res.json();
  },
};
