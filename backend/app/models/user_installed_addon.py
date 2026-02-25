import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserInstalledAddon(Base):
    __tablename__ = "user_installed_addons"
    __table_args__ = (UniqueConstraint("user_id", "addon_id", name="uq_user_installed_addon"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    addon_id: Mapped[str] = mapped_column(String, nullable=False)
    # NULL = bundled (local Python class); set = remote addon manifest URL
    manifest_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # Cached JSON from the manifest URL (populated on install, used to serve manifest without re-fetching)
    manifest_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    installed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
