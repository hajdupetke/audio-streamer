"""
HTTP-based proxy classes for remote addons.

Remote addons run as independent HTTP services. This module provides
ContentSource and StreamResolver implementations that forward calls
to those services via their declared api_url.
"""
from typing import Any

import httpx

from app.addons.base import (
    AudiobookDetail,
    AudiobookResult,
    ChapterFile,
    ContentSource,
    StreamResolver,
    StreamResult,
)

_TIMEOUT = httpx.Timeout(15.0)


class RemoteContentSource(ContentSource):
    def __init__(self, settings: dict[str, Any], api_url: str) -> None:
        super().__init__(settings)
        self._api_url = api_url.rstrip("/")

    async def search(self, query: str) -> list[AudiobookResult]:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{self._api_url}/search",
                json={"query": query, "settings": self.settings},
            )
            resp.raise_for_status()
        return [
            AudiobookResult(
                id=item["id"],
                title=item["title"],
                addon_id=item.get("addon_id", ""),
                author=item.get("author"),
                description=item.get("description"),
                cover_url=item.get("cover_url"),
                extra=item.get("extra", {}),
            )
            for item in resp.json()
        ]

    async def get_details(self, item_id: str) -> AudiobookDetail:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{self._api_url}/items/{item_id}",
                json={"settings": self.settings},
            )
            resp.raise_for_status()
        data = resp.json()
        return AudiobookDetail(
            id=data["id"],
            title=data["title"],
            addon_id=data.get("addon_id", ""),
            author=data.get("author"),
            description=data.get("description"),
            cover_url=data.get("cover_url"),
            files=[
                ChapterFile(
                    id=f["id"],
                    title=f["title"],
                    track_number=f.get("track_number"),
                    duration=f.get("duration"),
                    url=f.get("url"),
                )
                for f in data.get("files", [])
            ],
            extra=data.get("extra", {}),
        )


class RemoteStreamResolver(StreamResolver):
    def __init__(self, settings: dict[str, Any], api_url: str) -> None:
        super().__init__(settings)
        self._api_url = api_url.rstrip("/")

    async def resolve(self, item_id: str, file_id: str) -> StreamResult:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{self._api_url}/resolve",
                json={"item_id": item_id, "file_id": file_id, "settings": self.settings},
            )
            resp.raise_for_status()
        data = resp.json()
        if data.get("local_path") is not None:
            raise ValueError("Remote addons must not return local_path (security boundary)")
        return StreamResult(
            url=data.get("url", ""),
            proxy=data.get("proxy", False),
            local_path=None,
            headers=data.get("headers", {}),
            content_type=data.get("content_type", "audio/mpeg"),
        )
