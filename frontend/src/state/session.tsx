import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { FolderId, Req } from "@/api/types";

export const FOLDER_IDS: FolderId[] = ["calendar", "1-1s", "meetings", "inbox", "hr-private"];
const defaultFolders = (): Record<FolderId, boolean> => ({ calendar: true, "1-1s": true, meetings: true, inbox: true, "hr-private": false });

type Session = {
  date: string;
  enabledFolders: Record<FolderId, boolean>;
  setFolder: (id: FolderId, on: boolean) => void;
  excludedDocs: string[];
  setExcludedDocs: (docs: string[]) => void;
  selectedMeetingId: string | null;
  setSelectedMeetingId: (id: string | null) => void;
  req: Req;
  wipe: () => Promise<void>;
};

const Ctx = createContext<Session | null>(null);

export function SessionProvider({ date, children }: { date: string; children: ReactNode }) {
  const qc = useQueryClient();
  const [sessionDate, setSessionDate] = useState(date);
  const [enabledFolders, setEnabled] = useState(defaultFolders);
  const [excludedDocs, setExcludedDocs] = useState<string[]>([]);
  const [selectedMeetingId, setSelectedMeetingId] = useState<string | null>(null);
  const setFolder = useCallback((id: FolderId, on: boolean) => setEnabled((f) => ({ ...f, [id]: on })), []);
  const req = useMemo<Req>(() => ({ folders: FOLDER_IDS.filter((f) => enabledFolders[f]), excludedDocs }), [enabledFolders, excludedDocs]);
  useEffect(() => {
    setSessionDate(date);
  }, [date]);
  useEffect(() => {
    const updateDate = () => {
      const now = new Date();
      const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
      setSessionDate((current) => current === today ? current : today);
    };
    const timer = window.setInterval(updateDate, 30_000);
    document.addEventListener("visibilitychange", updateDate);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", updateDate);
    };
  }, []);
  const wipe = useCallback(async () => {
    await api.wipeSession();
    setEnabled(defaultFolders());
    setExcludedDocs([]);
    setSelectedMeetingId(null);
    qc.clear();
  }, [qc]);
  const value = { date: sessionDate, enabledFolders, setFolder, excludedDocs, setExcludedDocs, selectedMeetingId, setSelectedMeetingId, req, wipe };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSession() {
  const s = useContext(Ctx);
  if (!s) throw new Error("useSession must be used inside SessionProvider");
  return s;
}
