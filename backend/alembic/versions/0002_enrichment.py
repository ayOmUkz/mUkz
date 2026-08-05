"""M2 enrichment: candles, symbol_days, symbol_stats, print classification.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-05

Adds the enrichment tables and the classification columns on ``prints``.
Both steps are guarded with inspector checks because a *fresh* database gets
the full current schema from revision 0001 (metadata.create_all), while a
database that ran M1 before this code existed needs the ALTERs.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op
from app.db import PRINT_CLASSIFICATION_COLUMNS, maybe_create_hypertables, metadata, prints

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    metadata.create_all(bind)  # creates candles / symbol_days / symbol_stats if missing
    maybe_create_hypertables(bind)

    inspector = sa.inspect(bind)
    existing = {column["name"] for column in inspector.get_columns("prints")}
    for name in PRINT_CLASSIFICATION_COLUMNS:
        if name not in existing:
            column = prints.c[name]
            op.add_column("prints", sa.Column(name, column.type, nullable=True))


def downgrade() -> None:
    for name in reversed(PRINT_CLASSIFICATION_COLUMNS):
        op.drop_column("prints", name)
    for table in ("symbol_stats", "symbol_days", "candles"):
        op.drop_table(table)
