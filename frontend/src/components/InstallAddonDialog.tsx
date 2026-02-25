import { useState } from "react"
import { toast } from "sonner"
import { useInstallAddon } from "@/hooks/useAddons"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function InstallAddonDialog({ open, onOpenChange }: Props) {
  const [url, setUrl] = useState("")
  const install = useInstallAddon()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!url.trim()) return
    try {
      await install.mutateAsync(url.trim())
      toast.success("Addon installed successfully")
      setUrl("")
      onOpenChange(false)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to install addon")
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Install Remote Addon</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="manifest-url">Manifest URL</Label>
            <Input
              id="manifest-url"
              type="url"
              placeholder="https://example.com/addon/manifest.json"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              autoFocus
            />
            <p className="text-xs text-muted-foreground">
              Enter the URL of the addon&apos;s manifest JSON file.
            </p>
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={!url.trim() || install.isPending}>
              {install.isPending ? "Installing…" : "Install"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
