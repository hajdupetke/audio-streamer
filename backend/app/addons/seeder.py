"""
Ensure every user has a UserInstalledAddon row for every bundled addon.

Called at startup (for all existing users) and after registration (for the new user).
Uses INSERT ... ON CONFLICT DO NOTHING so it's safe to call repeatedly.
"""
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.addons.registry import registry
from app.models.user import User
from app.models.user_installed_addon import UserInstalledAddon

logger = logging.getLogger(__name__)


async def seed_addons_for_user(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Install all currently registered bundled addons for a single user (idempotent)."""
    addon_ids = registry.bundled_addon_ids
    if not addon_ids:
        return

    for addon_id in addon_ids:
        stmt = (
            pg_insert(UserInstalledAddon)
            .values(user_id=user_id, addon_id=addon_id, manifest_url=None, enabled=True)
            .on_conflict_do_nothing(index_elements=["user_id", "addon_id"])
        )
        await db.execute(stmt)

    await db.commit()


async def seed_addons_for_all_users(db: AsyncSession) -> None:
    """Seed all bundled addons for every user in the database. Run once at startup."""
    addon_ids = registry.bundled_addon_ids
    if not addon_ids:
        return

    result = await db.execute(select(User.id))
    user_ids: list[uuid.UUID] = list(result.scalars().all())

    if not user_ids:
        return

    for user_id in user_ids:
        for addon_id in addon_ids:
            stmt = (
                pg_insert(UserInstalledAddon)
                .values(user_id=user_id, addon_id=addon_id, manifest_url=None, enabled=True)
                .on_conflict_do_nothing(index_elements=["user_id", "addon_id"])
            )
            await db.execute(stmt)

    await db.commit()
    logger.info("Seeded %d addon(s) for %d user(s)", len(addon_ids), len(user_ids))
