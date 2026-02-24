import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProgressRequest(BaseModel):
    library_item_id: uuid.UUID
    file_id: str
    position: float = Field(ge=0.0)
    duration: float | None = Field(default=None, ge=0.0)


class ProgressResponse(BaseModel):
    library_item_id: uuid.UUID
    file_id: str
    position: float
    duration: float | None
    last_played: datetime

    model_config = ConfigDict(from_attributes=True)
