import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { useSession } from "@/state/session";

export function useMeetings() {
  const { date, req } = useSession();
  return useQuery({ queryKey: ["meetings", date, req.folders, req.excludedDocs], queryFn: () => api.getMeetings(date, req.folders) });
}
