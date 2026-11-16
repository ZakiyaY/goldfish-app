import { useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { useSession } from "@/state/session";

export function useBrief(meetingId: string | null) {
  const { req } = useSession();
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["brief", meetingId, req.folders, req.excludedDocs],
    queryFn: () => api.getBrief(meetingId as string, req),
    enabled: !!meetingId,
  });
  useEffect(() => { if (q.data) void qc.invalidateQueries({ queryKey: ["receipt"] }); }, [q.data, qc]);
  return q;
}
