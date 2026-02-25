import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import type { Addon, AddonSettings } from "@/types"

export function useAddons() {
  return useQuery<Addon[]>({
    queryKey: ["addons"],
    queryFn: api.addons.list,
  })
}

export function useToggleAddon() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      api.addons.patch(id, enabled),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["addons"] })
    },
  })
}

export function useAddonSettings(id: string) {
  return useQuery<AddonSettings>({
    queryKey: ["addon-settings", id],
    queryFn: () => api.addons.getSettings(id),
    enabled: !!id,
  })
}

export function useSaveAddonSettings(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (settings: Record<string, unknown>) =>
      api.addons.putSettings(id, settings),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["addon-settings", id] })
      queryClient.invalidateQueries({ queryKey: ["addons"] })
    },
  })
}

export function useInstallAddon() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (manifestUrl: string) => api.addons.install(manifestUrl),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["addons"] })
    },
  })
}

export function useUninstallAddon() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.addons.uninstall(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["addons"] })
    },
  })
}
