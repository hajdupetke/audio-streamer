import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"
import type { SearchResponse } from "@/types"

export function useSearch(q: string, addonId?: string) {
  return useQuery<SearchResponse>({
    queryKey: ["search", q, addonId],
    queryFn: () => api.search.search(q, addonId),
    enabled: q.length > 0,
  })
}
