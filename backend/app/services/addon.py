"""Addon service — DB-backed operations for user addon installations and settings."""
import json
import uuid
from dataclasses import asdict
from typing import Any

import httpx
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.addons.base import ContentSource, StreamResolver
from app.addons.manifest import AddonManifest, SettingsField
from app.addons.registry import registry
from app.addons.remote import RemoteContentSource, RemoteStreamResolver
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


# ── Manifest JSON helpers ─────────────────────────────────────────────────────

def _parse_manifest_json(manifest_json: str) -> tuple[AddonManifest, str]:
    """Parse cached manifest JSON into (AddonManifest, api_url). Raises ValueError on error."""
    data = json.loads(manifest_json)
    api_url = data.get("api_url")
    if not api_url:
        raise ValueError("Remote manifest missing api_url")
    schema = [
        SettingsField(
            key=f["key"],
            type=f["type"],
            label=f["label"],
            required=f.get("required", True),
            default=f.get("default"),
            description=f.get("description"),
            max_length=f.get("max_length"),
        )
        for f in data.get("settings_schema", [])
    ]
    manifest = AddonManifest(
        id=data["id"],
        name=data["name"],
        description=data.get("description", ""),
        version=data.get("version", "0.0.0"),
        capabilities=data.get("capabilities", []),
        settings_schema=schema,
        author=data.get("author"),
        icon_url=data.get("icon_url"),
    )
    return manifest, api_url


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


# ── Remote addon install/uninstall ────────────────────────────────────────────

async def install_remote_addon(
    db: AsyncSession, user_id: uuid.UUID, manifest_url: str
) -> UserInstalledAddon:
    """Fetch a remote manifest, validate it, and install it for the user."""
    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
        resp = await client.get(manifest_url)
        resp.raise_for_status()
    data = resp.json()

    # Validate required fields
    for field_name in ("id", "name", "description", "version", "capabilities", "api_url"):
        if not data.get(field_name):
            raise ValueError(f"Remote manifest missing required field: {field_name!r}")

    addon_id = data["id"]

    # Guard: can't shadow a bundled addon
    if registry.get_manifest(addon_id) is not None:
        raise ValueError(f"Addon {addon_id!r} is already provided as a bundled addon")

    # Guard: already installed
    existing = await get_installed_addon(db, user_id, addon_id)
    if existing is not None:
        raise ValueError(f"Addon {addon_id!r} is already installed")

    installation = UserInstalledAddon(
        user_id=user_id,
        addon_id=addon_id,
        manifest_url=manifest_url,
        manifest_json=json.dumps(data),
        enabled=True,
    )
    db.add(installation)
    await db.commit()
    await db.refresh(installation)
    return installation


async def uninstall_remote_addon(
    db: AsyncSession, user_id: uuid.UUID, addon_id: str
) -> None:
    """Uninstall a remote addon and delete its settings."""
    installation = await get_installed_addon(db, user_id, addon_id)
    if installation is None:
        raise ValueError(f"Addon {addon_id!r} is not installed")
    if installation.manifest_url is None:
        raise ValueError(f"Addon {addon_id!r} is a bundled addon and cannot be uninstalled")

    await db.execute(
        delete(UserAddonSettings).where(
            UserAddonSettings.user_id == user_id,
            UserAddonSettings.addon_id == addon_id,
        )
    )
    await db.delete(installation)
    await db.commit()


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
        # Fall back to remote manifest from user's installation
        installation = await get_installed_addon(db, user_id, addon_id)
        if installation is None or not installation.manifest_json:
            raise ValueError(f"Unknown addon: {addon_id!r}")
        try:
            manifest, _ = _parse_manifest_json(installation.manifest_json)
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            raise ValueError(f"Unknown addon: {addon_id!r}") from exc

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

    # Bundled addons from the registry
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
                "is_remote": False,
                "author": manifest.author,
                "icon_url": manifest.icon_url,
            }
        )

    # Remote addons from the user's installation rows
    for addon_id, installation in installations.items():
        if installation.manifest_url is None:
            continue  # bundled — already handled above
        if not installation.manifest_json:
            continue
        try:
            manifest, _ = _parse_manifest_json(installation.manifest_json)
        except (ValueError, KeyError, json.JSONDecodeError):
            continue
        user_settings = await _get_raw_settings(db, user_id, addon_id)
        result.append(
            {
                "id": manifest.id,
                "name": manifest.name,
                "description": manifest.description,
                "version": manifest.version,
                "capabilities": manifest.capabilities,
                "settings_schema": [asdict(f) for f in manifest.settings_schema],
                "enabled": installation.enabled,
                "configured": _is_configured(manifest, user_settings),
                "is_remote": True,
                "author": manifest.author,
                "icon_url": manifest.icon_url,
            }
        )

    return result


async def get_addon_settings_response(
    db: AsyncSession, user_id: uuid.UUID, addon_id: str
) -> dict[str, Any]:
    """Return masked settings for the API response (passwords → placeholder)."""
    manifest = registry.get_manifest(addon_id)
    if manifest is None:
        # Fall back to remote manifest
        installation = await get_installed_addon(db, user_id, addon_id)
        if installation is None or not installation.manifest_json:
            raise ValueError(f"Unknown addon: {addon_id!r}")
        try:
            manifest, _ = _parse_manifest_json(installation.manifest_json)
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            raise ValueError(f"Unknown addon: {addon_id!r}") from exc

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

    if installation.manifest_url is not None:
        if not installation.manifest_json:
            return None
        try:
            manifest, api_url = _parse_manifest_json(installation.manifest_json)
        except (ValueError, KeyError, json.JSONDecodeError):
            return None
        if "content_source" not in manifest.capabilities:
            return None
        user_settings = await get_addon_settings(db, user_id, addon_id)
        return RemoteContentSource(user_settings, api_url)

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

    if installation.manifest_url is not None:
        if not installation.manifest_json:
            return None
        try:
            manifest, api_url = _parse_manifest_json(installation.manifest_json)
        except (ValueError, KeyError, json.JSONDecodeError):
            return None
        if "stream_resolver" not in manifest.capabilities:
            return None
        user_settings = await get_addon_settings(db, user_id, addon_id)
        return RemoteStreamResolver(user_settings, api_url)

    user_settings = await get_addon_settings(db, user_id, addon_id)
    return registry.make_stream_resolver(addon_id, user_settings)
