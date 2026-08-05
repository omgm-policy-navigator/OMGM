import { useQuery } from "@tanstack/react-query";
import { fetchHealth } from "@/shared/api";

export function useHealthQuery() {
  return useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => fetchHealth({ signal }),
  });
}
