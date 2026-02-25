import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import type { LibraryItem, SaveBookPayload } from "@/types"

export function useLibrary() {
  return useQuery<LibraryItem[]>({
    queryKey: ["library"],
    queryFn: api.library.list,
  })
}

export function useSaveBook() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (book: SaveBookPayload) => api.library.save(book),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["library"] })
    },
  })
}

export function useRemoveBook() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.library.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["library"] })
    },
  })
}
