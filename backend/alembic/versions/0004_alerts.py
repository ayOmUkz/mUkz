"""M4: alerts table.

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-05
"""

from __future__ import annotations

from alembic import op
from app.db import metadata

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    metadata.create_all(op.get_bind())


def downgrade() -> None:
    op.drop_table("alerts")
