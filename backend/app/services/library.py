import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.library_item import LibraryItem


async def get_library(db: AsyncSession, user_id: uuid.UUID) -> Sequence[LibraryItem]:
    result = await db.execute(
        select(LibraryItem)
        .where(LibraryItem.user_id == user_id)
        .order_by(LibraryItem.added_at.desc())
    )
    return result.scalars().all()


async def save_book(
    db: AsyncSession,
    user_id: uuid.UUID,
    addon_id: str,
    external_id: str,
    title: str,
    author: str | None = None,
    cover_url: str | None = None,
    metadata: dict | None = None,
) -> LibraryItem:
    stmt = (
        pg_insert(LibraryItem)
        .values(
            user_id=user_id,
            addon_id=addon_id,
            external_id=external_id,
            title=title,
            author=author,
            cover_url=cover_url,
            metadata=metadata,
        )
        .on_conflict_do_update(
            index_elements=["user_id", "addon_id", "external_id"],
            set_=dict(
                title=title,
                author=author,
                cover_url=cover_url,
                metadata=metadata,
            ),
        )
        .returning(LibraryItem)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.scalar_one()


async def delete_book(
    db: AsyncSession,
    user_id: uuid.UUID,
    item_id: uuid.UUID,
) -> bool:
    result = await db.execute(
        select(LibraryItem).where(
            LibraryItem.id == item_id,
            LibraryItem.user_id == user_id,
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        return False
    await db.delete(item)
    await db.commit()
    return True
