from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.addon import (
    AddonEnabledRequest,
    AddonResponse,
    AddonSettingsRequest,
    AddonSettingsResponse,
)
from app.services import addon as addon_service

router = APIRouter(prefix="/api/addons", tags=["addons"])


@router.get("", response_model=list[AddonResponse])
async def list_addons(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AddonResponse]:
    """List all installed addons for the current user with their enabled state."""
    rows = await addon_service.get_user_addons_response(db, current_user.id)
    return [AddonResponse(**r) for r in rows]


@router.patch("/{addon_id}")
async def update_addon(
    addon_id: str,
    data: AddonEnabledRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Enable or disable an addon for the current user."""
    try:
        await addon_service.set_addon_enabled(db, current_user.id, addon_id, data.enabled)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"ok": True}


@router.get("/{addon_id}/settings", response_model=AddonSettingsResponse)
async def get_settings(
    addon_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AddonSettingsResponse:
    """Return the current user's settings for an addon (passwords masked)."""
    try:
        data = await addon_service.get_addon_settings_response(db, current_user.id, addon_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return AddonSettingsResponse(**data)


@router.put("/{addon_id}/settings")
async def save_settings(
    addon_id: str,
    body: AddonSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Save per-user configuration for an addon (encrypted at rest)."""
    try:
        await addon_service.save_addon_settings(db, current_user.id, addon_id, body.settings)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}
