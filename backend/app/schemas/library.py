import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class SaveBookRequest(BaseModel):
    addon_id: str
    external_id: str
    title: str
    author: str | None = None
    cover_url: str | None = None
    metadata: dict[str, Any] | None = None


class LibraryItemResponse(BaseModel):
    id: uuid.UUID
    addon_id: str
    external_id: str
    title: str
    author: str | None
    cover_url: str | None
    metadata: dict[str, Any] | None = None
    added_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_item(cls, item: Any) -> "LibraryItemResponse":
        return cls(
            id=item.id,
            addon_id=item.addon_id,
            external_id=item.external_id,
            title=item.title,
            author=item.author,
            cover_url=item.cover_url,
            metadata=item.extra_metadata,
            added_at=item.added_at,
        )
