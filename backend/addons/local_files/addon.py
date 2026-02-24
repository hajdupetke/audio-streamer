"""
Local Files addon — ContentSource + StreamResolver for server-side audio files.

Directory layout (both levels supported):
  Two-level (preferred):   {LIBRARY_PATH}/Author Name/Book Title/*.mp3
  One-level (flat books):  {LIBRARY_PATH}/Book Title/*.mp3

IDs use URL-safe base64 so they survive URL path segments:
  item_id → base64url of the relative path from LIBRARY_PATH to the book dir
            e.g. "Mark Twain/Huck Finn" → "TWFyayBUd2Fpbi9IdWNrIEZpbm4"
  file_id → base64url of the filename only
            e.g. "01 - Chapter 1.mp3" → "MDEgLSBDaGFwdGVyIDEubXAz"

StreamResult.local_path is set → stream endpoint serves the file directly with
Range request support (no HTTP redirect, no external proxying).

Security: all decoded paths are validated to stay within LIBRARY_PATH.
"""
import asyncio
import base64
import logging
import re
from pathlib import Path
from typing import Any

from mutagen import File as MutagenFile

from app.addons.base import (
    AudiobookDetail,
    AudiobookResult,
    ChapterFile,
    ContentSource,
    StreamResolver,
    StreamResult,
)
from app.config import get_settings

logger = logging.getLogger(__name__)

_AUDIO_EXTENSIONS = frozenset(
    [".mp3", ".m4a", ".m4b", ".flac", ".ogg", ".opus", ".wav", ".aac"]
)
_CONTENT_TYPES: dict[str, str] = {
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".m4b": "audio/mp4",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
    ".opus": "audio/ogg; codecs=opus",
    ".wav": "audio/wav",
    ".aac": "audio/aac",
}


# ── ID encoding ───────────────────────────────────────────────────────────────

def _encode(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


def _decode(s: str) -> str:
    # Restore stripped padding
    s += "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode(s).decode()


# ── Path helpers ──────────────────────────────────────────────────────────────

def _get_library_path() -> Path:
    val = get_settings().local_files_library_path
    if not val:
        raise ValueError(
            "LOCAL_FILES_LIBRARY_PATH is not set. "
            "Add it to your .env file to use the Local Files addon."
        )
    return Path(val)


def _safe_resolve(library_path: Path, rel: str) -> Path:
    """
    Resolve `rel` relative to `library_path` and assert it stays inside.
    Raises ValueError on path traversal attempts.
    """
    resolved = (library_path / rel).resolve()
    if not str(resolved).startswith(str(library_path.resolve()) + "/") and resolved != library_path.resolve():
        raise ValueError(f"Path traversal detected in: {rel!r}")
    return resolved


def _is_audio(p: Path) -> bool:
    return p.suffix.lower() in _AUDIO_EXTENSIONS


def _natural_key(name: str) -> list[Any]:
    """'Chapter 10' sorts after 'Chapter 9' (not alphabetically before it)."""
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", name)]


# ── Metadata reading (sync, run in thread) ────────────────────────────────────

def _read_metadata(path: Path) -> tuple[str | None, float | None, int | None]:
    """
    Returns (title, duration_seconds, track_number) from the file's audio tags.
    Falls back to (None, None, None) on any failure — the caller uses the filename instead.
    """
    try:
        audio = MutagenFile(path, easy=True)
        if audio is None:
            return None, None, None

        duration: float | None = getattr(getattr(audio, "info", None), "length", None)
        if duration is not None and duration <= 0:
            duration = None

        tags: Any = getattr(audio, "tags", None) or {}

        # EasyID3 / EasyMP4 / EasyVorbis all expose list values
        def _tag(key: str) -> str | None:
            val = tags.get(key)
            if not val:
                return None
            return str(val[0]) if isinstance(val, list) else str(val)

        title = _tag("title")

        track_number: int | None = None
        raw_track = _tag("tracknumber")
        if raw_track:
            try:
                track_number = int(raw_track.split("/")[0].strip())
            except (ValueError, AttributeError):
                pass

        return title, duration, track_number

    except Exception as exc:
        logger.debug("Could not read metadata for %s: %s", path.name, exc)
        return None, None, None


# ── Directory scanning (sync, run in thread) ──────────────────────────────────

def _scan_library_sync(
    library_path: Path,
    query_lower: str | None,
) -> list[dict[str, Any]]:
    """
    Walk LIBRARY_PATH and return a list of book info dicts.

    For each top-level entry:
      - If it directly contains audio files → treat as a one-level Book dir
      - Otherwise → treat as an Author dir and scan its subdirectories

    Applies the search filter on title and author name.
    """
    if not library_path.exists():
        logger.warning("Library path does not exist: %s", library_path)
        return []

    books: list[dict[str, Any]] = []

    for entry in sorted(library_path.iterdir(), key=lambda p: _natural_key(p.name)):
        if not entry.is_dir() or entry.name.startswith("."):
            continue

        # Peek: does this directory directly contain any audio files?
        try:
            direct_audio = any(
                f.is_file() and _is_audio(f) for f in entry.iterdir()
            )
        except PermissionError:
            continue

        if direct_audio:
            # One-level: entry IS the book directory
            if query_lower and query_lower not in entry.name.lower():
                continue
            books.append({"rel_path": entry.name, "title": entry.name, "author": None})
        else:
            # Two-level: entry is an Author directory
            try:
                sub_entries = sorted(entry.iterdir(), key=lambda p: _natural_key(p.name))
            except PermissionError:
                continue

            for book_dir in sub_entries:
                if not book_dir.is_dir() or book_dir.name.startswith("."):
                    continue
                if query_lower and not (
                    query_lower in book_dir.name.lower()
                    or query_lower in entry.name.lower()
                ):
                    continue
                books.append(
                    {
                        "rel_path": f"{entry.name}/{book_dir.name}",
                        "title": book_dir.name,
                        "author": entry.name,
                    }
                )

    return books


def _scan_book_files_sync(book_path: Path) -> list[dict[str, Any]]:
    """
    Scan a book directory for audio files and read their tags.
    Returns file dicts sorted by natural filename order (track tags applied later).
    """
    if not book_path.is_dir():
        return []

    results: list[dict[str, Any]] = []
    for f in sorted(book_path.iterdir(), key=lambda p: _natural_key(p.name)):
        if not f.is_file() or not _is_audio(f):
            continue
        title_tag, duration, track_number = _read_metadata(f)
        results.append(
            {
                "filename": f.name,
                "title": title_tag or f.stem,  # fall back to filename stem
                "duration": duration,
                "track_number": track_number,
                "content_type": _CONTENT_TYPES.get(f.suffix.lower(), "audio/mpeg"),
            }
        )

    # Re-sort: prefer track_number from tags, keep natural order as tiebreak
    results.sort(
        key=lambda x: (
            x["track_number"] if x["track_number"] is not None else 9999,
            _natural_key(x["filename"]),
        )
    )
    return results


# ── ContentSource ─────────────────────────────────────────────────────────────

class ContentSourceImpl(ContentSource):

    async def search(self, query: str) -> list[AudiobookResult]:
        library_path = _get_library_path()
        query_lower = query.strip().lower() or None  # None → return all books

        books = await asyncio.to_thread(_scan_library_sync, library_path, query_lower)

        return [
            AudiobookResult(
                id=_encode(b["rel_path"]),
                title=b["title"],
                author=b["author"],
                addon_id="local-files",
            )
            for b in books
        ]

    async def get_details(self, item_id: str) -> AudiobookDetail:
        library_path = _get_library_path()

        try:
            rel_path = _decode(item_id)
        except Exception:
            raise ValueError(f"Malformed item_id: {item_id!r}")

        book_path = _safe_resolve(library_path, rel_path)

        # Derive title / author from the path structure
        parts = rel_path.split("/", 1)
        title = parts[-1]
        author = parts[0] if len(parts) > 1 else None

        raw_files = await asyncio.to_thread(_scan_book_files_sync, book_path)

        files = [
            ChapterFile(
                id=_encode(f["filename"]),
                title=f["title"],
                track_number=f["track_number"],
                duration=f["duration"],
                url=None,  # no direct URL — must route through /api/stream
            )
            for f in raw_files
        ]

        return AudiobookDetail(
            id=item_id,
            title=title,
            author=author,
            files=files,
            addon_id="local-files",
        )


# ── StreamResolver ────────────────────────────────────────────────────────────

class StreamResolverImpl(StreamResolver):

    async def resolve(self, item_id: str, file_id: str) -> StreamResult:
        library_path = _get_library_path()

        try:
            rel_book = _decode(item_id)
            filename = _decode(file_id)
        except Exception:
            raise ValueError("Malformed item_id or file_id")

        # Reconstruct and validate the full path
        rel_file = f"{rel_book}/{filename}"
        file_path = _safe_resolve(library_path, rel_file)

        if not file_path.is_file():
            raise ValueError(f"File not found: {filename!r} in {rel_book!r}")

        content_type = _CONTENT_TYPES.get(file_path.suffix.lower(), "audio/mpeg")

        return StreamResult(
            # url is unused for local files; local_path triggers direct FileResponse serving
            local_path=str(file_path),
            content_type=content_type,
        )
