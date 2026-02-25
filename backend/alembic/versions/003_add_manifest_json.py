"""Add manifest_json to user_installed_addons

Revision ID: 003
Revises: 002
Create Date: 2025-01-01 00:00:02.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user_installed_addons", sa.Column("manifest_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("user_installed_addons", "manifest_json")
