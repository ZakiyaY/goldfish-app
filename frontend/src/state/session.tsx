import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
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
  const [enabledFolders, setEnabled] = useState(defaultFolders);
  const [excludedDocs, setExcludedDocs] = useState<string[]>([]);
  const [selectedMeetingId, setSelectedMeetingId] = useState<string | null>(null);
  const setFolder = useCallback((id: FolderId, on: boolean) => setEnabled((f) => ({ ...f, [id]: on })), []);
  const req = useMemo<Req>(() => ({ folders: FOLDER_IDS.filter((f) => enabledFolders[f]), excludedDocs }), [enabledFolders, excludedDocs]);
  const wipe = useCallback(async () => {
    await api.wipeSession();
    setEnabled(defaultFolders());
    setExcludedDocs([]);
    setSelectedMeetingId(null);
    qc.clear();
  }, [qc]);
  const value = { date, enabledFolders, setFolder, excludedDocs, setExcludedDocs, selectedMeetingId, setSelectedMeetingId, req, wipe };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSession() {
  const s = useContext(Ctx);
  if (!s) throw new Error("useSession must be used inside SessionProvider");
  return s;
}
