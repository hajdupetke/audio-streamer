import { useState, useEffect } from "react"
import type { SettingsField } from "@/types"
import { useAddonSettings, useSaveAddonSettings } from "@/hooks/useAddons"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { toast } from "sonner"

interface AddonSettingsFormProps {
  addonId: string
  schema: SettingsField[]
  onClose: () => void
}

export function AddonSettingsForm({ addonId, schema, onClose }: AddonSettingsFormProps) {
  const { data: addonSettings, isLoading } = useAddonSettings(addonId)
  const saveSettings = useSaveAddonSettings(addonId)

  const [values, setValues] = useState<Record<string, unknown>>({})

  useEffect(() => {
    if (addonSettings) {
      const initial: Record<string, unknown> = {}
      for (const field of schema) {
        initial[field.key] =
          addonSettings.settings[field.key] ?? field.default ?? ""
      }
      setValues(initial)
    } else {
      const initial: Record<string, unknown> = {}
      for (const field of schema) {
        initial[field.key] = field.default ?? ""
      }
      setValues(initial)
    }
  }, [addonSettings, schema])

  function setValue(key: string, value: unknown) {
    setValues((prev) => ({ ...prev, [key]: value }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    try {
      await saveSettings.mutateAsync(values)
      toast.success("Settings saved")
      onClose()
    } catch {
      toast.error("Failed to save settings")
    }
  }

  if (isLoading) {
    return <div className="text-sm text-muted-foreground">Loading settings...</div>
  }

  if (schema.length === 0) {
    return (
      <div className="text-sm text-muted-foreground">
        This addon has no configurable settings.
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {schema.map((field) => (
        <div key={field.key} className="space-y-1.5">
          <Label htmlFor={field.key}>
            {field.label}
            {field.required && <span className="text-destructive ml-1">*</span>}
          </Label>
          {field.type === "boolean" ? (
            <div className="flex items-center gap-2">
              <Switch
                id={field.key}
                checked={Boolean(values[field.key])}
                onCheckedChange={(checked) => setValue(field.key, checked)}
              />
              {field.description && (
                <span className="text-xs text-muted-foreground">{field.description}</span>
              )}
            </div>
          ) : (
            <>
              <Input
                id={field.key}
                type={
                  field.type === "password"
                    ? "password"
                    : field.type === "number"
                    ? "number"
                    : "text"
                }
                value={String(values[field.key] ?? "")}
                onChange={(e) =>
                  setValue(
                    field.key,
                    field.type === "number" ? Number(e.target.value) : e.target.value
                  )
                }
                maxLength={field.max_length}
                placeholder={field.description}
              />
              {field.description && (
                <p className="text-xs text-muted-foreground">{field.description}</p>
              )}
            </>
          )}
        </div>
      ))}
      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="ghost" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" disabled={saveSettings.isPending}>
          {saveSettings.isPending ? "Saving..." : "Save"}
        </Button>
      </div>
    </form>
  )
}
