"""M7: options premium tilt columns on symbol_days.

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-05
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op
from app.db import SYMBOL_DAY_OPTIONS_COLUMNS, symbol_days

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing = {column["name"] for column in inspector.get_columns("symbol_days")}
    for name in SYMBOL_DAY_OPTIONS_COLUMNS:
        if name not in existing:
            op.add_column("symbol_days", sa.Column(name, symbol_days.c[name].type,
                                                   nullable=True))


def downgrade() -> None:
    for name in reversed(SYMBOL_DAY_OPTIONS_COLUMNS):
        op.drop_column("symbol_days", name)
