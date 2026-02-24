"""
AddonManifest and SettingsField — the contract an addon declares to the core.

settings_schema drives the dynamic config form rendered in the frontend settings page.
Each SettingsField maps to one input in that form.
"""
from dataclasses import dataclass, field
from typing import Any, Literal


FieldType = Literal["string", "password", "number", "boolean", "path"]
Capability = Literal["content_source", "stream_resolver"]


@dataclass
class SettingsField:
    key: str
    type: FieldType
    label: str
    required: bool = True
    default: Any = None
    description: str | None = None
    # For "string"/"password" fields: optional max length hint for the UI
    max_length: int | None = None


@dataclass
class AddonManifest:
    id: str                              # stable, URL-safe slug: "librivox", "local-files"
    name: str                            # display name: "LibriVox"
    description: str
    version: str
    capabilities: list[Capability]
    settings_schema: list[SettingsField] = field(default_factory=list)
    author: str | None = None
    icon_url: str | None = None

    def requires_settings(self) -> bool:
        return any(f.required for f in self.settings_schema)

    def mask_secret_fields(self, settings: dict[str, Any]) -> dict[str, Any]:
        """Return a copy of settings with password fields replaced by a placeholder."""
        masked = dict(settings)
        for f in self.settings_schema:
            if f.type == "password" and f.key in masked:
                masked[f.key] = "••••••••"
        return masked
