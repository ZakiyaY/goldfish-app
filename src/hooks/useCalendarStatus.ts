import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { useSession } from "@/state/session";
import { useMeetings } from "./useMeetings";

export function useCalendarStatus() {
  const { req } = useSession();
  const m = useMeetings();
  // Runs after meetings settle so the helper has seen the current folder choice.
  return useQuery({ queryKey: ["calendarStatus", req.folders], queryFn: api.getCalendarStatus, enabled: m.isFetched && !m.isFetching });
}

export function useRefreshCalendar() {
  const { req } = useSession();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.refreshCalendar,
    onSuccess: (s) => { qc.setQueryData(["calendarStatus", req.folders], s); void qc.invalidateQueries({ queryKey: ["meetings"] }); },
  });
}
