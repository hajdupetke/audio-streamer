"""
Stream endpoint — resolves audio files and serves them with Range support.

Auth: httpOnly cookie (normal) or ?token= query param (HTML <audio src> fallback).

Dispatch order (based on StreamResult):
  1. local_path set → serve file from disk with Range support
  2. proxy=True     → proxy bytes from upstream with Range passthrough
  3. proxy=False    → 307 redirect to URL (cheapest; works for public CDNs)
"""
import os
import re

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user_for_stream
from app.models.user import User
from app.services import addon as addon_service

router = APIRouter(prefix="/api/stream", tags=["stream"])

_CHUNK = 65536  # 64 KB read chunks


# ── Local file serving with Range support ─────────────────────────────────────

def _local_range_response(
    file_path: str,
    content_type: str,
    range_header: str | None,
) -> StreamingResponse:
    file_size = os.path.getsize(file_path)

    if range_header:
        match = re.fullmatch(r"bytes=(\d+)-(\d*)", range_header.strip())
        if match:
            start = int(match.group(1))
            end = int(match.group(2)) if match.group(2) else file_size - 1
            end = min(end, file_size - 1)
            if start > end or start >= file_size:
                raise HTTPException(
                    status_code=416,
                    detail="Range Not Satisfiable",
                    headers={"Content-Range": f"bytes */{file_size}"},
                )
            length = end - start + 1

            async def file_range_iter():
                with open(file_path, "rb") as fh:
                    fh.seek(start)
                    remaining = length
                    while remaining > 0:
                        chunk = fh.read(min(_CHUNK, remaining))
                        if not chunk:
                            break
                        yield chunk
                        remaining -= len(chunk)

            headers = {
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(length),
            }
            return StreamingResponse(
                file_range_iter(), status_code=206, headers=headers, media_type=content_type
            )

    # No Range header — serve whole file
    async def full_file_iter():
        with open(file_path, "rb") as fh:
            while chunk := fh.read(_CHUNK):
                yield chunk

    return StreamingResponse(
        full_file_iter(),
        status_code=200,
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
        },
        media_type=content_type,
    )


# ── HTTP proxy with Range passthrough ─────────────────────────────────────────

async def _proxy_response(
    url: str,
    extra_headers: dict,
    range_header: str | None,
    content_type: str,
) -> StreamingResponse:
    req_headers = dict(extra_headers)
    if range_header:
        req_headers["Range"] = range_header

    client = httpx.AsyncClient(follow_redirects=True)
    response = await client.send(
        client.build_request("GET", url, headers=req_headers),
        stream=True,
    )

    forward: dict[str, str] = {"Accept-Ranges": "bytes"}
    for h in ("content-range", "content-length"):
        if h in response.headers:
            forward[h] = response.headers[h]

    async def proxy_iter():
        try:
            async for chunk in response.aiter_bytes(_CHUNK):
                yield chunk
        finally:
            await response.aclose()
            await client.aclose()

    return StreamingResponse(
        proxy_iter(),
        status_code=response.status_code,
        headers=forward,
        media_type=content_type,
    )


# ── Route ─────────────────────────────────────────────────────────────────────

@router.get("/{addon_id}/{item_id}/{file_id}")
async def stream(
    addon_id: str,
    item_id: str,
    file_id: str,
    request: Request,
    current_user: User = Depends(get_current_user_for_stream),
    db: AsyncSession = Depends(get_db),
):
    """
    Resolve and stream a single audio file.
    Supports Range requests for seeking.
    """
    resolver = await addon_service.get_stream_resolver(db, current_user.id, addon_id)
    if resolver is None:
        raise HTTPException(status_code=404, detail=f"Addon '{addon_id}' not found or not enabled")

    try:
        result = await resolver.resolve(item_id, file_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Addon error: {exc}") from exc

    range_header = request.headers.get("Range")

    # Dispatch mode 1: serve local file
    if result.local_path:
        if not os.path.isfile(result.local_path):
            raise HTTPException(status_code=404, detail="Audio file not found on server")
        return _local_range_response(result.local_path, result.content_type, range_header)

    # Dispatch mode 2: proxy
    if result.proxy:
        return await _proxy_response(result.url, result.headers, range_header, result.content_type)

    # Dispatch mode 3: redirect
    return RedirectResponse(url=result.url, status_code=307)
