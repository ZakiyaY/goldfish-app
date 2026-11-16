import type { AskAnswer, CalendarStatus, OpenResult, Brief, GoldfishApi, Meeting, Receipt } from "./types";

// The only module allowed to make network calls.
const BASE = (import.meta.env["VITE_API_BASE"] as string | undefined) ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { ...init, headers: { "Content-Type": "application/json", ...init?.headers } });
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}
const post = <T>(path: string, body: unknown) => request<T>(path, { method: "POST", body: JSON.stringify(body) });

export const httpClient: GoldfishApi = {
  getMeetings: (date, folders) => request<Meeting[]>(`/api/meetings?date=${encodeURIComponent(date)}&folders=${encodeURIComponent(folders.join(","))}`),
  getBrief: (meetingId, req) => post<Brief>("/api/brief", { meetingId, ...req }),
  ask: (question, req) => post<AskAnswer>("/api/ask", { question, ...req }),
  getReceipt: () => request<Receipt>("/api/receipt"),
  wipeSession: () => post<void>("/api/session/wipe", {}),
  getCalendarStatus: () => request<CalendarStatus>("/api/calendar/status"),
  refreshCalendar: () => post<CalendarStatus>("/api/calendar/refresh", {}),
  openSource: (docId, mode) => post<OpenResult>("/api/open", { docId, mode }),
  openFolder: (folder) => post<OpenResult>("/api/open-folder", { folder }),
};
