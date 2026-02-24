"""Add user_installed_addons table

Revision ID: 002
Revises: 001
Create Date: 2025-01-01 00:00:01.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_installed_addons",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("addon_id", sa.String(), nullable=False),
        sa.Column("manifest_url", sa.String(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("installed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "addon_id", name="uq_user_installed_addon"),
    )
    op.create_index("ix_user_installed_addons_user_id", "user_installed_addons", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_installed_addons_user_id", table_name="user_installed_addons")
    op.drop_table("user_installed_addons")
