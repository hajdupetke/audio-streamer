import uuid
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.playback_progress import PlaybackProgress


async def get_progress(
    db: AsyncSession,
    user_id: uuid.UUID,
    library_item_id: uuid.UUID,
) -> Sequence[PlaybackProgress]:
    result = await db.execute(
        select(PlaybackProgress).where(
            PlaybackProgress.user_id == user_id,
            PlaybackProgress.library_item_id == library_item_id,
        )
    )
    return result.scalars().all()


async def upsert_progress(
    db: AsyncSession,
    user_id: uuid.UUID,
    library_item_id: uuid.UUID,
    file_id: str,
    position: float,
    duration: float | None = None,
) -> PlaybackProgress:
    stmt = (
        pg_insert(PlaybackProgress)
        .values(
            user_id=user_id,
            library_item_id=library_item_id,
            file_id=file_id,
            position=position,
            duration=duration,
        )
        .on_conflict_do_update(
            index_elements=["user_id", "library_item_id", "file_id"],
            set_=dict(
                position=position,
                duration=duration,
                last_played=func.now(),
            ),
        )
        .returning(PlaybackProgress)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.scalar_one()
