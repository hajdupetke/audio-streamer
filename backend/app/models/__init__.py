# Import Base and all models so Alembic can detect the full schema
from app.models.base import Base
from app.models.library_item import LibraryItem
from app.models.playback_progress import PlaybackProgress
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.models.user_addon_settings import UserAddonSettings
from app.models.user_installed_addon import UserInstalledAddon

__all__ = [
    "Base",
    "LibraryItem",
    "PlaybackProgress",
    "RefreshToken",
    "User",
    "UserAddonSettings",
    "UserInstalledAddon",
]
