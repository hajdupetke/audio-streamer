import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.addons.registry import registry
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.search import AudiobookDetailSchema, AudiobookResultSchema, ChapterFileSchema, SearchResponse
from app.services import addon as addon_service

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    addon_id: str | None = Query(default=None, description="Limit search to a specific addon"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """
    Search across all enabled content-source addons (or a specific one).
    Results from multiple addons are merged and returned together.
    """
    if addon_id:
        source = await addon_service.get_content_source(db, current_user.id, addon_id)
        if source is None:
            raise HTTPException(status_code=404, detail=f"Addon '{addon_id}' not found or not enabled")
        addon_ids = [addon_id]
        sources = [source]
    else:
        # Gather all enabled addons that have content_source capability
        addon_ids = []
        sources = []
        for aid, manifest in registry.all_manifests.items():
            if "content_source" not in manifest.capabilities:
                continue
            source = await addon_service.get_content_source(db, current_user.id, aid)
            if source is not None:
                addon_ids.append(aid)
                sources.append(source)

    if not sources:
        return SearchResponse(query=q, results=[])

    # Run all searches in parallel; swallow per-addon errors so one bad addon
    # doesn't break the whole response.
    raw_results = await asyncio.gather(
        *[src.search(q) for src in sources],
        return_exceptions=True,
    )

    results: list[AudiobookResultSchema] = []
    for aid, outcome in zip(addon_ids, raw_results):
        if isinstance(outcome, Exception):
            continue
        for book in outcome:
            results.append(
                AudiobookResultSchema(
                    id=book.id,
                    title=book.title,
                    addon_id=book.addon_id,
                    author=book.author,
                    description=book.description,
                    cover_url=book.cover_url,
                    extra=book.extra,
                )
            )

    return SearchResponse(query=q, results=results)


@router.get("/addons/{addon_id}/items/{item_id}", response_model=AudiobookDetailSchema)
async def get_item_details(
    addon_id: str,
    item_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AudiobookDetailSchema:
    """Fetch full audiobook details (chapters, metadata) from an addon."""
    source = await addon_service.get_content_source(db, current_user.id, addon_id)
    if source is None:
        raise HTTPException(status_code=404, detail=f"Addon '{addon_id}' not found or not enabled")

    try:
        detail = await source.get_details(item_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Addon error: {exc}") from exc

    return AudiobookDetailSchema(
        id=detail.id,
        title=detail.title,
        addon_id=detail.addon_id,
        author=detail.author,
        description=detail.description,
        cover_url=detail.cover_url,
        files=[
            ChapterFileSchema(
                id=f.id,
                title=f.title,
                track_number=f.track_number,
                duration=f.duration,
                url=f.url,
            )
            for f in detail.files
        ],
        extra=detail.extra,
    )
