"""Addon service — DB-backed operations for user addon installations and settings."""
import json
import uuid
from dataclasses import asdict
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.addons.base import ContentSource, StreamResolver
from app.addons.manifest import AddonManifest
from app.addons.registry import registry
from app.config import get_settings
from app.models.user_addon_settings import UserAddonSettings
from app.models.user_installed_addon import UserInstalledAddon

settings = get_settings()


# ── Encryption helpers ────────────────────────────────────────────────────────

def _fernet() -> Fernet:
    key = settings.fernet_key
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_settings(data: dict[str, Any]) -> str:
    return _fernet().encrypt(json.dumps(data).encode()).decode()


def decrypt_settings(encrypted: str) -> dict[str, Any]:
    try:
        return json.loads(_fernet().decrypt(encrypted.encode()).decode())
    except (InvalidToken, json.JSONDecodeError) as exc:
        raise ValueError("Failed to decrypt addon settings") from exc


# ── Installed addon queries ───────────────────────────────────────────────────

async def get_installed_addon(
    db: AsyncSession, user_id: uuid.UUID, addon_id: str
) -> UserInstalledAddon | None:
    result = await db.execute(
        select(UserInstalledAddon).where(
            UserInstalledAddon.user_id == user_id,
            UserInstalledAddon.addon_id == addon_id,
        )
    )
    return result.scalar_one_or_none()


async def get_all_installed_addons(
    db: AsyncSession, user_id: uuid.UUID
) -> list[UserInstalledAddon]:
    result = await db.execute(
        select(UserInstalledAddon).where(UserInstalledAddon.user_id == user_id)
    )
    return list(result.scalars().all())


# ── Settings queries ──────────────────────────────────────────────────────────

async def _get_raw_settings(
    db: AsyncSession, user_id: uuid.UUID, addon_id: str
) -> dict[str, Any] | None:
    result = await db.execute(
        select(UserAddonSettings).where(
            UserAddonSettings.user_id == user_id,
            UserAddonSettings.addon_id == addon_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return decrypt_settings(row.encrypted_settings)


async def get_addon_settings(
    db: AsyncSession, user_id: uuid.UUID, addon_id: str
) -> dict[str, Any]:
    """Return decrypted settings dict (empty dict if none saved yet)."""
    return await _get_raw_settings(db, user_id, addon_id) or {}


async def save_addon_settings(
    db: AsyncSession, user_id: uuid.UUID, addon_id: str, new_settings: dict[str, Any]
) -> None:
    """Encrypt and upsert addon settings for the user."""
    manifest = registry.get_manifest(addon_id)
    if manifest is None:
        raise ValueError(f"Unknown addon: {addon_id!r}")

    encrypted = encrypt_settings(new_settings)

    result = await db.execute(
        select(UserAddonSettings).where(
            UserAddonSettings.user_id == user_id,
            UserAddonSettings.addon_id == addon_id,
        )
    )
    row = result.scalar_one_or_none()

    if row is None:
        row = UserAddonSettings(user_id=user_id, addon_id=addon_id, encrypted_settings=encrypted)
        db.add(row)
    else:
        row.encrypted_settings = encrypted

    await db.commit()


# ── Enabled state ─────────────────────────────────────────────────────────────

async def set_addon_enabled(
    db: AsyncSession, user_id: uuid.UUID, addon_id: str, enabled: bool
) -> None:
    installation = await get_installed_addon(db, user_id, addon_id)
    if installation is None:
        raise ValueError(f"Addon {addon_id!r} is not installed for this user")
    installation.enabled = enabled
    await db.commit()


# ── Composite response builder ────────────────────────────────────────────────

def _is_configured(manifest: AddonManifest, user_settings: dict[str, Any] | None) -> bool:
    """True if all required fields in the manifest have a non-empty value in user_settings."""
    required = [f for f in manifest.settings_schema if f.required]
    if not required:
        return True
    if not user_settings:
        return False
    return all(user_settings.get(f.key) not in (None, "") for f in required)


async def get_user_addons_response(
    db: AsyncSession, user_id: uuid.UUID
) -> list[dict[str, Any]]:
    """
    Build the full addon list response for a user.
    Merges: registry manifests + user installation state + configured status.
    """
    installations = {i.addon_id: i for i in await get_all_installed_addons(db, user_id)}

    result = []
    for addon_id, manifest in registry.all_manifests.items():
        installation = installations.get(addon_id)
        user_settings = await _get_raw_settings(db, user_id, addon_id)

        result.append(
            {
                "id": manifest.id,
                "name": manifest.name,
                "description": manifest.description,
                "version": manifest.version,
                "capabilities": manifest.capabilities,
                "settings_schema": [asdict(f) for f in manifest.settings_schema],
                "enabled": installation.enabled if installation else False,
                "configured": _is_configured(manifest, user_settings),
            }
        )

    return result


async def get_addon_settings_response(
    db: AsyncSession, user_id: uuid.UUID, addon_id: str
) -> dict[str, Any]:
    """Return masked settings for the API response (passwords → placeholder)."""
    manifest = registry.get_manifest(addon_id)
    if manifest is None:
        raise ValueError(f"Unknown addon: {addon_id!r}")

    raw = await _get_raw_settings(db, user_id, addon_id) or {}
    return {
        "addon_id": addon_id,
        "settings": manifest.mask_secret_fields(raw),
    }


# ── Addon instance factory (used by search + stream endpoints) ────────────────

async def get_content_source(
    db: AsyncSession, user_id: uuid.UUID, addon_id: str
) -> ContentSource | None:
    """
    Return an instantiated ContentSource for the user's addon config, or None
    if the addon isn't installed, isn't enabled, or doesn't have content_source capability.
    """
    installation = await get_installed_addon(db, user_id, addon_id)
    if installation is None or not installation.enabled:
        return None

    # TODO: remote addons — check installation.manifest_url and dispatch via HTTP
    user_settings = await get_addon_settings(db, user_id, addon_id)
    return registry.make_content_source(addon_id, user_settings)


async def get_stream_resolver(
    db: AsyncSession, user_id: uuid.UUID, addon_id: str
) -> StreamResolver | None:
    """
    Return an instantiated StreamResolver for the user's addon config, or None
    if not applicable.
    """
    installation = await get_installed_addon(db, user_id, addon_id)
    if installation is None or not installation.enabled:
        return None

    # TODO: remote addons — check installation.manifest_url and dispatch via HTTP
    user_settings = await get_addon_settings(db, user_id, addon_id)
    return registry.make_stream_resolver(addon_id, user_settings)
