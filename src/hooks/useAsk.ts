import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { useSession } from "@/state/session";

export function useAsk() {
  const { req } = useSession();
  const qc = useQueryClient();
  return useMutation({
    mutationKey: ["ask", req.folders, req.excludedDocs],
    mutationFn: (question: string) => api.ask(question, req),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["receipt"] }),
  });
}
