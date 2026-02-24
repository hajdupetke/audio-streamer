from typing import Any

from pydantic import BaseModel


class SettingsFieldSchema(BaseModel):
    key: str
    type: str
    label: str
    required: bool = True
    default: Any = None
    description: str | None = None
    max_length: int | None = None


class AddonResponse(BaseModel):
    id: str
    name: str
    description: str
    version: str
    capabilities: list[str]
    settings_schema: list[SettingsFieldSchema]
    enabled: bool
    configured: bool  # True when all required settings are saved


class AddonSettingsResponse(BaseModel):
    addon_id: str
    settings: dict[str, Any]


class AddonSettingsRequest(BaseModel):
    """Freeform dict — validated against the manifest's settings_schema in the service."""
    settings: dict[str, Any]


class AddonEnabledRequest(BaseModel):
    enabled: bool
