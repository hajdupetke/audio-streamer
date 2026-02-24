"""
Base ABCs and result types for the addon system.

Every addon implements ContentSource, StreamResolver, or both.
The constructor receives the user's decrypted settings dict so each
instance is scoped to a single user's configuration.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AudiobookResult:
    """Lightweight search result returned by ContentSource.search()."""
    id: str           # addon-scoped ID, must be stable and URL-safe
    title: str
    addon_id: str     # which addon produced this result
    author: str | None = None
    description: str | None = None
    cover_url: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)  # addon-specific bonus data


@dataclass
class ChapterFile:
    """A single playable file (chapter / part) within an audiobook."""
    id: str           # stable file ID used in progress tracking + stream resolution
    title: str
    track_number: int | None = None
    duration: float | None = None   # seconds; None if unknown at detail-fetch time
    url: str | None = None          # direct URL if the addon knows it without resolve()


@dataclass
class AudiobookDetail:
    """Full audiobook info including the chapter list, returned by ContentSource.get_details()."""
    id: str
    title: str
    addon_id: str
    author: str | None = None
    description: str | None = None
    cover_url: str | None = None
    files: list[ChapterFile] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamResult:
    """
    Resolved stream info returned by StreamResolver.resolve().

    Three dispatch modes, checked in order by the stream endpoint:
      1. local_path is set → serve the file directly from disk (FileResponse + Range)
      2. proxy=True        → proxy bytes from `url` with Range header passthrough
      3. proxy=False       → HTTP redirect to `url` (cheapest; works for public URLs)
    """
    url: str = ""                    # redirect/proxy target; empty string for local-file mode
    proxy: bool = False
    local_path: str | None = None    # absolute server path; triggers direct file serving
    headers: dict[str, str] = field(default_factory=dict)
    content_type: str = "audio/mpeg"


class ContentSource(ABC):
    """Mixin for addons that can search for and describe audiobooks."""

    def __init__(self, settings: dict[str, Any]) -> None:
        self.settings = settings

    @abstractmethod
    async def search(self, query: str) -> list[AudiobookResult]:
        """Return matching audiobooks for `query`."""
        ...

    @abstractmethod
    async def get_details(self, item_id: str) -> AudiobookDetail:
        """Return full details + chapter list for `item_id`."""
        ...


class StreamResolver(ABC):
    """Mixin for addons that can turn an item/file reference into a playable URL."""

    def __init__(self, settings: dict[str, Any]) -> None:
        self.settings = settings

    @abstractmethod
    async def resolve(self, item_id: str, file_id: str) -> StreamResult:
        """Resolve `file_id` within `item_id` to a StreamResult."""
        ...
