import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"
import type { PlaybackProgress } from "@/types"

export function useProgress(libraryItemId: string | null) {
  return useQuery<PlaybackProgress[]>({
    queryKey: ["progress", libraryItemId],
    queryFn: () => api.progress.get(libraryItemId!),
    enabled: libraryItemId !== null,
  })
}
