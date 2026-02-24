"""
LibriVox addon — ContentSource + StreamResolver.

API: https://librivox.org/api/feed/audiobooks  (no auth required)

Quirks discovered from live API testing:
  - `title` param does partial slug matching (spaces → underscores improves hits)
  - `author` param matches on last name only; full names return 404
  - "No results" is HTTP 404 with {"error": "..."}, not an empty books array
  - `extended=1` populates `sections`; section duration is `playtime` (seconds, string)
  - Cover art: derive from `url_iarchive` field → archive.org/services/img/{id}

Search strategy:
  1. title={raw query}           — works when query is a slug-like title
  2. title={slug version}        — converts "Pride and Prejudice" → "pride_and_prejudice"
  3. author={last word of query} — "Mark Twain" → author=twain

file_id convention: the section's numeric `id` string (e.g. "134562").
ChapterFile.url is also populated with listen_url for direct playback.
resolve() returns proxy=False → backend issues a redirect (archive.org is public).
"""
import asyncio
import logging
import re
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

logger = logging.getLogger(__name__)

_API = "https://librivox.org/api/feed/audiobooks"
_TIMEOUT = httpx.Timeout(15.0)
_SEARCH_FIELDS = "id,title,description,url_iarchive,url_other,authors"
_DETAIL_FIELDS = "id,title,description,url_iarchive,url_other,authors,sections"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _strip_html(text: str | None) -> str | None:
    if not text:
        return None
    cleaned = re.sub(r"<[^>]+>", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or None


def _author_str(book: dict[str, Any]) -> str | None:
    authors = book.get("authors") or []
    parts = [
        f"{a.get('first_name', '')} {a.get('last_name', '')}".strip()
        for a in authors
        if a.get("first_name") or a.get("last_name")
    ]
    return ", ".join(parts) or None


def _cover_url(book: dict[str, Any]) -> str | None:
    """Extract archive.org identifier from url_iarchive or url_other and build image URL."""
    for field in ("url_iarchive", "url_other"):
        url = (book.get(field) or "").strip()
        if "archive.org/details/" in url:
            identifier = url.rstrip("/").split("/")[-1]
            return f"https://archive.org/services/img/{identifier}"
    return None


def _slugify(query: str) -> str:
    """'Pride and Prejudice' → 'pride_and_prejudice'"""
    return re.sub(r"[^a-z0-9]+", "_", query.lower()).strip("_")


def _parse_books(resp: httpx.Response) -> list[dict[str, Any]]:
    """
    Return the books list from a response, or [] on any failure.
    The LibriVox API returns HTTP 404 with {"error":"..."} when nothing is found
    — that is treated as an empty result, not an error.
    """
    if not resp.is_success:
        return []
    data = resp.json()
    books = data.get("books")
    if not books or isinstance(books, str):
        return []
    return books


def _int_or_none(v: Any) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _float_or_none(v: Any) -> float | None:
    try:
        result = float(v)
        return result if result > 0 else None
    except (TypeError, ValueError):
        return None


# ── ContentSource ─────────────────────────────────────────────────────────────

class ContentSourceImpl(ContentSource):

    async def search(self, query: str) -> list[AudiobookResult]:
        """
        Issue up to three parallel searches and merge results:
          1. title={raw query}  — direct match (e.g. "Moby Dick")
          2. title={slug}       — slug match  (e.g. "moby_dick")
          3. author={surname}   — last word of query as surname (e.g. "twain")

        De-duplicate by book ID. Preserves the order: title matches first,
        then author matches that weren't already in the title results.
        """
        slug = _slugify(query)
        words = query.strip().split()
        surname = words[-1] if words else query  # best guess at a surname

        # Build unique param sets (avoid duplicate requests)
        param_sets: list[dict[str, str]] = [
            {"title": query, "format": "json", "fields": _SEARCH_FIELDS, "limit": "10"},
        ]
        if slug != query:  # only add if slugifying actually changed something
            param_sets.append(
                {"title": slug, "format": "json", "fields": _SEARCH_FIELDS, "limit": "10"}
            )
        param_sets.append(
            {"author": surname, "format": "json", "fields": _SEARCH_FIELDS, "limit": "10"}
        )

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            raw_responses = await asyncio.gather(
                *[client.get(_API, params=p) for p in param_sets],
                return_exceptions=True,
            )

        seen_ids: set[str] = set()
        results: list[AudiobookResult] = []

        for i, resp in enumerate(raw_responses):
            if isinstance(resp, Exception):
                logger.debug("LibriVox search variant %d failed: %s", i, resp)
                continue
            for book in _parse_books(resp):
                book_id = str(book.get("id", ""))
                if not book_id or book_id in seen_ids:
                    continue
                seen_ids.add(book_id)
                results.append(
                    AudiobookResult(
                        id=book_id,
                        title=book.get("title") or "",
                        author=_author_str(book),
                        description=_strip_html(book.get("description")),
                        cover_url=_cover_url(book),
                        addon_id="librivox",
                    )
                )

        return results

    async def get_details(self, item_id: str) -> AudiobookDetail:
        params = {
            "id": item_id,
            "format": "json",
            "extended": "1",
            "fields": _DETAIL_FIELDS,
        }
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(_API, params=params)

        books = _parse_books(resp)
        if not books:
            raise ValueError(f"LibriVox book {item_id!r} not found")

        book = books[0]
        sections: list[dict[str, Any]] = book.get("sections") or []

        files = [
            ChapterFile(
                id=str(s["id"]),
                title=s.get("title") or f"Chapter {s.get('section_number', '?')}",
                track_number=_int_or_none(s.get("section_number")),
                duration=_float_or_none(s.get("playtime")),
                url=s.get("listen_url") or None,
            )
            for s in sorted(
                sections,
                key=lambda s: _int_or_none(s.get("section_number")) or 0,
            )
        ]

        return AudiobookDetail(
            id=item_id,
            title=book.get("title") or "",
            author=_author_str(book),
            description=_strip_html(book.get("description")),
            cover_url=_cover_url(book),
            files=files,
            addon_id="librivox",
        )


# ── StreamResolver ────────────────────────────────────────────────────────────

class StreamResolverImpl(StreamResolver):

    async def resolve(self, item_id: str, file_id: str) -> StreamResult:
        """
        Fetch the book's section list and return the listen_url for file_id.
        Returns proxy=False — archive.org MP3s are publicly accessible; redirect is enough.
        """
        params = {
            "id": item_id,
            "format": "json",
            "extended": "1",
            "fields": "sections",
        }
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(_API, params=params)

        books = _parse_books(resp)
        if not books:
            raise ValueError(f"LibriVox book {item_id!r} not found")

        sections: list[dict[str, Any]] = books[0].get("sections") or []
        for section in sections:
            if str(section.get("id", "")) == file_id:
                listen_url = section.get("listen_url")
                if listen_url:
                    return StreamResult(url=listen_url, proxy=False)
                break

        raise ValueError(f"Section {file_id!r} not found in LibriVox book {item_id!r}")
