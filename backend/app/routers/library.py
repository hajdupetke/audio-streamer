import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.library import LibraryItemResponse, SaveBookRequest
from app.services import library as library_service

router = APIRouter(prefix="/api/library", tags=["library"])


@router.get("", response_model=list[LibraryItemResponse])
async def get_library(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[LibraryItemResponse]:
    """Return the current user's saved audiobook library."""
    items = await library_service.get_library(db, current_user.id)
    return [LibraryItemResponse.from_orm_item(item) for item in items]


@router.post("", response_model=LibraryItemResponse, status_code=201)
async def save_book(
    body: SaveBookRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LibraryItemResponse:
    """Add (or update) an audiobook in the user's library."""
    item = await library_service.save_book(
        db,
        user_id=current_user.id,
        addon_id=body.addon_id,
        external_id=body.external_id,
        title=body.title,
        author=body.author,
        cover_url=body.cover_url,
        metadata=body.metadata,
    )
    return LibraryItemResponse.from_orm_item(item)


@router.delete("/{item_id}", status_code=204)
async def delete_book(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove an audiobook from the user's library."""
    deleted = await library_service.delete_book(db, current_user.id, item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Library item not found")
