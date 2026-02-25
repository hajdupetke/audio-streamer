import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"
import type { BookDetail } from "@/types"

export function useBook(addonId: string, itemId: string) {
  return useQuery<BookDetail>({
    queryKey: ["book", addonId, itemId],
    queryFn: () => api.search.getDetail(addonId, itemId),
    enabled: !!addonId && !!itemId,
  })
}
