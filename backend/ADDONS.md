# Addon Development Guide

Addons are the extension points of the audio streamer. Each addon can provide content search, audio stream resolution, or both. The core app never hardcodes any content source — everything goes through this interface.

## Architecture overview

The system has two layers:

| Layer | Location | Purpose |
|---|---|---|
| **Framework** | `app/addons/` | ABCs, manifest, registry, loader, seeder |
| **Plugins** | `backend/addons/` | Actual addon implementations |

On startup, `app/addons/loader.py` scans `backend/addons/*/` and registers any valid addon packages with the global `registry` singleton. Per-user installation records are seeded into `user_installed_addons`. Per-user settings are stored encrypted (Fernet AES-128) in `user_addon_settings`.

## Creating a bundled addon

### 1. Directory structure

```
backend/addons/
└── your_addon_name/       ← use underscores, no hyphens
    ├── __init__.py        ← empty
    ├── manifest.py        ← exports `manifest: AddonManifest`
    └── addon.py           ← exports ContentSourceImpl and/or StreamResolverImpl
```

The loader discovers addons by looking for `manifest.py` inside each subdirectory. Directories starting with `_` are skipped.

---

### 2. manifest.py

```python
from app.addons.manifest import AddonManifest, SettingsField

manifest = AddonManifest(
    id="my-addon",           # stable, URL-safe slug — never change this after release
    name="My Addon",         # display name shown in the settings UI
    description="One sentence about what this addon does.",
    version="1.0.0",
    capabilities=["content_source", "stream_resolver"],  # declare what you implement
    author="Your Name",      # optional
    settings_schema=[        # drives the dynamic config form in the frontend
        SettingsField(
            key="api_key",
            type="password",
            label="API Key",
            required=True,
            description="Your API key from example.com/settings",
        ),
        SettingsField(
            key="max_results",
            type="number",
            label="Max results per search",
            required=False,
            default=20,
        ),
    ],
)
```

**`capabilities`** must list every capability you implement. Only listed capabilities are offered to users.

**`settings_schema`** drives the auto-generated config form in the frontend settings page. The frontend renders one input per field based on `type`:

| type | UI element | Notes |
|---|---|---|
| `"string"` | Text input | General text |
| `"password"` | Password input | Masked; stored encrypted; masked in API responses |
| `"number"` | Number input | Value is still passed as a string — parse it yourself |
| `"boolean"` | Toggle | Value is `"true"` or `"false"` string |
| `"path"` | Text input | Hint to the UI that this is a file/directory path |

Settings with `required=True` mark the addon as "not configured" until the user saves a value for them.

---

### 3. addon.py — ContentSource

Implement `ContentSourceImpl(ContentSource)` if your addon can search for audiobooks.

```python
from typing import Any
from app.addons.base import AudiobookResult, AudiobookDetail, ChapterFile, ContentSource

class ContentSourceImpl(ContentSource):
    # self.settings: dict[str, Any] — the user's decrypted settings for this addon
    # A new instance is created per request with the calling user's settings.

    async def search(self, query: str) -> list[AudiobookResult]:
        """Return matching audiobooks. Empty list if nothing found — never raise on 'no results'."""
        ...

    async def get_details(self, item_id: str) -> AudiobookDetail:
        """Return full details + chapter list. Raise ValueError if not found."""
        ...
```

**Return types:**

```python
@dataclass
class AudiobookResult:
    id: str           # Your internal ID for this audiobook — must be stable and URL-safe
    title: str
    addon_id: str     # Always set to your manifest id (e.g. "my-addon")
    author: str | None = None
    description: str | None = None
    cover_url: str | None = None
    extra: dict = {}  # Optional extra data passed through to the frontend

@dataclass
class AudiobookDetail:
    id: str           # Same id as in AudiobookResult
    title: str
    addon_id: str
    author: str | None = None
    description: str | None = None
    cover_url: str | None = None
    files: list[ChapterFile] = []  # Ordered chapter/file list

@dataclass
class ChapterFile:
    id: str               # Stable file ID used in progress tracking + stream resolution
    title: str
    track_number: int | None = None
    duration: float | None = None  # seconds; None if unknown
    url: str | None = None         # direct playable URL if known (optional shortcut for player)
```

**Important:** `ChapterFile.id` must be stable (same value across calls for the same file) because it's stored in the `playback_progress` table. If IDs change, users lose their progress. If `ChapterFile.url` is set, the player can use it directly without going through the stream endpoint — useful for public URLs (like LibriVox). For protected/local content, leave `url=None`.

---

### 4. addon.py — StreamResolver

Implement `StreamResolverImpl(StreamResolver)` if your addon can resolve a file reference into a playable audio stream.

```python
from app.addons.base import StreamResolver, StreamResult

class StreamResolverImpl(StreamResolver):

    async def resolve(self, item_id: str, file_id: str) -> StreamResult:
        """
        Turn (item_id, file_id) into a StreamResult.
        Raise ValueError if the item or file cannot be found.
        """
        ...
```

**StreamResult — three dispatch modes:**

The stream endpoint checks these in order:

```python
@dataclass
class StreamResult:
    url: str = ""
    proxy: bool = False
    local_path: str | None = None   # takes priority over proxy/url
    headers: dict[str, str] = {}
    content_type: str = "audio/mpeg"
```

| Mode | When | How |
|---|---|---|
| **Local file** | `local_path` is set | Backend serves the file directly with `FileResponse` + Range support |
| **HTTP proxy** | `proxy=True`, `local_path=None` | Backend fetches from `url`, passes Range header through, streams back |
| **Redirect** | `proxy=False`, `local_path=None` | Backend issues `307 Temporary Redirect` to `url` |

Use redirect for public URLs (LibriVox, direct CDN links). Use proxy for sources that require auth headers. Use `local_path` for server-side files.

---

### 5. Accessing user settings

Your addon receives the calling user's decrypted settings as `self.settings: dict[str, Any]` in the constructor. The keys match the `key` fields in your `settings_schema`.

```python
class ContentSourceImpl(ContentSource):
    async def search(self, query: str) -> list[AudiobookResult]:
        api_key = self.settings.get("api_key", "")
        max_results = int(self.settings.get("max_results") or 20)
        ...
```

If the user hasn't saved settings yet, `self.settings` will be `{}` — always use `.get()` with a sensible default.

---

### 6. Registration

No registration code needed — the loader handles it automatically. Just restart the backend and your addon will appear.

The loader imports `{your_package}.manifest` and `{your_package}.addon` and looks for:
- `manifest_mod.manifest` — your `AddonManifest` instance
- `addon_mod.ContentSourceImpl` — optional
- `addon_mod.StreamResolverImpl` — optional

If neither `ContentSourceImpl` nor `StreamResolverImpl` is found, the addon is skipped with a warning.

---

## Complete example — Podcast Feed addon

A minimal addon that treats a user's podcast RSS feed as an audiobook collection:

**`addons/podcast_feed/manifest.py`**
```python
from app.addons.manifest import AddonManifest, SettingsField

manifest = AddonManifest(
    id="podcast-feed",
    name="Podcast Feed",
    description="Listen to podcast episodes as audiobooks via an RSS feed URL.",
    version="1.0.0",
    capabilities=["content_source", "stream_resolver"],
    settings_schema=[
        SettingsField(
            key="feed_url",
            type="string",
            label="RSS Feed URL",
            required=True,
            description="The full URL to the podcast's RSS feed.",
        ),
    ],
)
```

**`addons/podcast_feed/addon.py`**
```python
import httpx
from xml.etree import ElementTree as ET
from app.addons.base import (
    AudiobookResult, AudiobookDetail, ChapterFile,
    ContentSource, StreamResolver, StreamResult,
)

class ContentSourceImpl(ContentSource):

    async def search(self, query: str) -> list[AudiobookResult]:
        feed_url = self.settings.get("feed_url", "")
        if not feed_url:
            return []

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(feed_url)
            resp.raise_for_status()

        root = ET.fromstring(resp.text)
        channel = root.find("channel")
        if channel is None:
            return []

        show_title = channel.findtext("title") or "Podcast"
        show_image = channel.find(".//image/url")
        cover = show_image.text if show_image is not None else None

        # Return the whole podcast as a single "audiobook"
        if query.lower() in show_title.lower() or not query:
            return [AudiobookResult(
                id="feed",
                title=show_title,
                addon_id="podcast-feed",
                cover_url=cover,
            )]
        return []

    async def get_details(self, item_id: str) -> AudiobookDetail:
        feed_url = self.settings.get("feed_url", "")
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(feed_url)
            resp.raise_for_status()

        root = ET.fromstring(resp.text)
        channel = root.find("channel")
        show_title = channel.findtext("title") or "Podcast"

        files = []
        for i, item in enumerate(channel.findall("item"), 1):
            enclosure = item.find("enclosure")
            if enclosure is None:
                continue
            mp3_url = enclosure.get("url", "")
            duration_str = item.findtext("{http://www.itunes.com/dtds/podcast-1.0.dtd}duration")
            files.append(ChapterFile(
                id=str(i),         # episode index as stable-enough ID for MVP
                title=item.findtext("title") or f"Episode {i}",
                track_number=i,
                duration=_parse_itunes_duration(duration_str),
                url=mp3_url,       # direct URL — player can use it without stream endpoint
            ))

        return AudiobookDetail(
            id=item_id,
            title=show_title,
            addon_id="podcast-feed",
            files=files,
        )


class StreamResolverImpl(StreamResolver):

    async def resolve(self, item_id: str, file_id: str) -> StreamResult:
        # Re-fetch the feed and find the episode by index
        feed_url = self.settings.get("feed_url", "")
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(feed_url)
            resp.raise_for_status()

        root = ET.fromstring(resp.text)
        items = root.findall(".//item")
        idx = int(file_id) - 1
        if not (0 <= idx < len(items)):
            raise ValueError(f"Episode {file_id} not found")

        enclosure = items[idx].find("enclosure")
        if enclosure is None:
            raise ValueError(f"Episode {file_id} has no audio")

        return StreamResult(url=enclosure.get("url", ""), proxy=False)


def _parse_itunes_duration(s: str | None) -> float | None:
    if not s:
        return None
    parts = s.strip().split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        return float(parts[0])
    except (ValueError, IndexError):
        return None
```

---

## Future: user-linked addons (remote manifests)

> **Not yet implemented.** This describes the planned architecture already wired into the DB schema.

Currently only server-side (bundled) addons exist. The `user_installed_addons.manifest_url` column in the database is reserved for the future remote addon feature:

1. **An addon author** deploys an HTTP service that implements the addon protocol and exposes a `/manifest.json` endpoint describing its capabilities and settings schema.

2. **A user** pastes the manifest URL into the app → the backend fetches the manifest, validates it, creates a `user_installed_addons` row with the URL set, and presents the settings form (driven by the manifest's `settings_schema`).

3. **At request time**, the backend checks `manifest_url`:
   - `NULL` → call the local Python class from the registry (current behavior)
   - Set → make HTTP calls to the remote addon service, passing the user's settings as headers or a signed token

The remote addon protocol will mirror the Python ABC interface as a REST API:
```
POST /search          body: {query, settings}    → list[AudiobookResult]
POST /details         body: {item_id, settings}  → AudiobookDetail
POST /resolve         body: {item_id, file_id, settings} → StreamResult
```

The dispatch stub is already in `app/services/addon.py` (`get_content_source` and `get_stream_resolver`) — look for the `# TODO: remote addons` comment. That's the only place that needs to change when this feature is built.
