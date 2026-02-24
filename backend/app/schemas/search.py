from typing import Any

from pydantic import BaseModel


class AudiobookResultSchema(BaseModel):
    id: str
    title: str
    addon_id: str
    author: str | None = None
    description: str | None = None
    cover_url: str | None = None
    extra: dict[str, Any] = {}


class ChapterFileSchema(BaseModel):
    id: str
    title: str
    track_number: int | None = None
    duration: float | None = None
    url: str | None = None


class AudiobookDetailSchema(BaseModel):
    id: str
    title: str
    addon_id: str
    author: str | None = None
    description: str | None = None
    cover_url: str | None = None
    files: list[ChapterFileSchema] = []
    extra: dict[str, Any] = {}


class SearchResponse(BaseModel):
    query: str
    results: list[AudiobookResultSchema]
