import { useState } from "react"
import { createFileRoute } from "@tanstack/react-router"
import { toast } from "sonner"
import { useAddons, useToggleAddon, useUninstallAddon } from "@/hooks/useAddons"
import { AddonSettingsForm } from "@/components/AddonSettingsForm"
import { InstallAddonDialog } from "@/components/InstallAddonDialog"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import type { Addon } from "@/types"

export const Route = createFileRoute("/_app/addons")({
  component: AddonsPage,
})

function AddonsPage() {
  const { data: addons, isLoading } = useAddons()
  const toggleAddon = useToggleAddon()
  const uninstallAddon = useUninstallAddon()
  const [settingsOpen, setSettingsOpen] = useState<string | null>(null)
  const [installOpen, setInstallOpen] = useState(false)

  const selectedAddon = addons?.find((a) => a.id === settingsOpen) ?? null

  function handleToggle(addon: Addon) {
    toggleAddon.mutate({ id: addon.id, enabled: !addon.enabled })
  }

  async function handleUninstall(addon: Addon) {
    if (!window.confirm(`Uninstall "${addon.name}"? This will also delete your saved settings for this addon.`)) {
      return
    }
    try {
      await uninstallAddon.mutateAsync(addon.id)
      toast.success(`${addon.name} uninstalled`)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to uninstall addon")
    }
  }

  return (
    <div className="container mx-auto px-6 py-8 max-w-4xl">
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-3xl font-bold tracking-tight">Addons</h1>
        <Button onClick={() => setInstallOpen(true)}>Install Addon</Button>
      </div>
      <p className="text-sm text-muted-foreground mb-6">Manage your content sources and stream resolvers</p>

      {isLoading && (
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-5 w-32" />
                <Skeleton className="h-4 w-64" />
              </CardHeader>
            </Card>
          ))}
        </div>
      )}

      {!isLoading && addons && (
        <div className="space-y-4">
          {addons.map((addon) => (
            <Card
              key={addon.id}
              className={`hover:border-primary/30 transition-colors ${addon.enabled ? "border-l-2 border-l-primary" : ""}`}
            >
              <CardHeader>
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1 flex-1 min-w-0">
                    <CardTitle className="text-base flex items-center gap-2">
                      {addon.name}
                      <span className="text-xs font-normal text-muted-foreground">
                        v{addon.version}
                      </span>
                      {addon.configured && (
                        <Badge className="text-xs bg-primary/15 text-primary border border-primary/20 hover:bg-primary/20">
                          Configured
                        </Badge>
                      )}
                      {addon.is_remote && (
                        <Badge variant="outline" className="text-xs">
                          Remote
                        </Badge>
                      )}
                    </CardTitle>
                    <CardDescription>{addon.description}</CardDescription>
                  </div>
                  <div className="flex items-center gap-3 flex-shrink-0">
                    <Switch
                      checked={addon.enabled}
                      onCheckedChange={() => handleToggle(addon)}
                      disabled={toggleAddon.isPending}
                    />
                    {addon.settings_schema.length > 0 && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setSettingsOpen(addon.id)}
                      >
                        Settings
                      </Button>
                    )}
                    {addon.is_remote && (
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => handleUninstall(addon)}
                        disabled={uninstallAddon.isPending}
                      >
                        Uninstall
                      </Button>
                    )}
                  </div>
                </div>
              </CardHeader>
              {addon.capabilities.length > 0 && (
                <CardContent className="pt-0">
                  <div className="flex flex-wrap gap-1.5">
                    {addon.capabilities.map((cap) => (
                      <Badge
                        key={cap}
                        variant="outline"
                        className="text-xs border-primary/30 text-primary/80"
                      >
                        {cap}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              )}
            </Card>
          ))}
        </div>
      )}

      {!isLoading && addons && addons.length === 0 && (
        <div className="text-center py-16 text-muted-foreground">
          No addons available
        </div>
      )}

      <Dialog open={!!settingsOpen} onOpenChange={(open) => !open && setSettingsOpen(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {selectedAddon ? `${selectedAddon.name} Settings` : "Settings"}
            </DialogTitle>
          </DialogHeader>
          {selectedAddon && (
            <AddonSettingsForm
              addonId={selectedAddon.id}
              schema={selectedAddon.settings_schema}
              onClose={() => setSettingsOpen(null)}
            />
          )}
        </DialogContent>
      </Dialog>

      <InstallAddonDialog open={installOpen} onOpenChange={setInstallOpen} />
    </div>
  )
}
