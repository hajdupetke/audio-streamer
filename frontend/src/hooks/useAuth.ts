import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"
import type { User } from "@/types"

export function useAuth() {
  const { data: user, isLoading } = useQuery<User>({
    queryKey: ["me"],
    queryFn: api.auth.me,
    retry: false,
  })

  return {
    user: user ?? null,
    isLoading,
    isAuthenticated: !!user,
  }
}
