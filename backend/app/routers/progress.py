import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.library_item import LibraryItem
from app.models.user import User
from app.schemas.progress import ProgressRequest, ProgressResponse
from app.services import progress as progress_service

router = APIRouter(prefix="/api/progress", tags=["progress"])


@router.get("/{library_item_id}", response_model=list[ProgressResponse])
async def get_progress(
    library_item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProgressResponse]:
    """Return all per-file playback progress for a library item."""
    # Verify the item belongs to this user
    result = await db.execute(
        select(LibraryItem).where(
            LibraryItem.id == library_item_id,
            LibraryItem.user_id == current_user.id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Library item not found")

    rows = await progress_service.get_progress(db, current_user.id, library_item_id)
    return list(rows)


@router.post("", response_model=ProgressResponse)
async def upsert_progress(
    body: ProgressRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProgressResponse:
    """Save or update playback position for a file."""
    # Verify the library item belongs to this user
    result = await db.execute(
        select(LibraryItem).where(
            LibraryItem.id == body.library_item_id,
            LibraryItem.user_id == current_user.id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Library item not found")

    row = await progress_service.upsert_progress(
        db,
        user_id=current_user.id,
        library_item_id=body.library_item_id,
        file_id=body.file_id,
        position=body.position,
        duration=body.duration,
    )
    return row
