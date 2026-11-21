import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { Folder, FolderId, Req } from "@/api/types";
import { useFolders } from "@/hooks/useFolders";

const defaultsFor = (folders: Folder[]): Record<FolderId, boolean> =>
  Object.fromEntries(folders.map((folder) => [folder.id, folder.defaultEnabled]));

type Session = {
  date: string;
  folders: Folder[];
  foldersLoading: boolean;
  foldersError: boolean;
  refetchFolders: () => void;
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
  const foldersQuery = useFolders();
  const folders = foldersQuery.data ?? [];
  const [sessionDate, setSessionDate] = useState(date);
  const [enabledFolders, setEnabled] = useState<Record<FolderId, boolean>>({});
  const [excludedDocs, setExcludedDocs] = useState<string[]>([]);
  const [selectedMeetingId, setSelectedMeetingId] = useState<string | null>(null);
  const setFolder = useCallback((id: FolderId, on: boolean) => setEnabled((f) => ({ ...f, [id]: on })), []);
  const req = useMemo<Req>(
    () => ({ folders: folders.filter((folder) => enabledFolders[folder.id]).map((folder) => folder.id), excludedDocs }),
    [folders, enabledFolders, excludedDocs],
  );
  useEffect(() => {
    const availableFolders = foldersQuery.data;
    if (!availableFolders) return;
    setEnabled((current) => Object.fromEntries(
      availableFolders.map((folder) => [folder.id, current[folder.id] ?? folder.defaultEnabled]),
    ));
  }, [foldersQuery.data]);
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
    setEnabled(defaultsFor(foldersQuery.data ?? []));
    setExcludedDocs([]);
    setSelectedMeetingId(null);
    qc.clear();
  }, [foldersQuery.data, qc]);
  const value = {
    date: sessionDate,
    folders,
    foldersLoading: foldersQuery.isPending,
    foldersError: foldersQuery.isError,
    refetchFolders: () => { void foldersQuery.refetch(); },
    enabledFolders,
    setFolder,
    excludedDocs,
    setExcludedDocs,
    selectedMeetingId,
    setSelectedMeetingId,
    req,
    wipe,
  };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSession() {
  const s = useContext(Ctx);
  if (!s) throw new Error("useSession must be used inside SessionProvider");
  return s;
}
