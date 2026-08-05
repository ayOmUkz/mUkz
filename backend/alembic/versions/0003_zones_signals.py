"""M3: zones, zone_events, signals.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-05

All three are plain tables (not hypertables). ``metadata.create_all`` is
idempotent, so this works both on fresh databases (where revision 0001
already created the full current schema) and on databases upgraded from M2.
"""

from __future__ import annotations

from alembic import op
from app.db import metadata

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    metadata.create_all(op.get_bind())


def downgrade() -> None:
    for table in ("signals", "zone_events", "zones"):
        op.drop_table(table)
