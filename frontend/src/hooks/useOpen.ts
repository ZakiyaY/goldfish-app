import { useRef } from "react";
import { toast } from "sonner";
import { api } from "@/api/client";
import type { FolderId, OpenMode, OpenResult } from "@/api/types";

// Opening is the manager's own action: it never touches the receipt. Double clicks are ignored while one is in flight.
export function useOpen() {
  const busy = useRef(false);
  const run = async (fn: () => Promise<OpenResult>) => {
    if (busy.current) return;
    busy.current = true;
    try {
      const r = await fn();
      if (r.ok) toast(r.message); else toast.error(r.message);
    } catch {
      toast.error("Can't reach the local helper on this laptop.");
    } finally {
      setTimeout(() => { busy.current = false; }, 400);
    }
  };
  return {
    openSource: (docId: string, mode: OpenMode) => run(() => api.openSource(docId, mode)),
    openFolder: (folder: FolderId) => run(() => api.openFolder(folder)),
  };
}
