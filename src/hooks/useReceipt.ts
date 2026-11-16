import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { useSession } from "@/state/session";

export function useReceipt() {
  const { req } = useSession();
  return useQuery({ queryKey: ["receipt", req.folders, req.excludedDocs], queryFn: api.getReceipt });
}
