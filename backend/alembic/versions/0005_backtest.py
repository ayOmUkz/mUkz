"""M6: backtest_runs, backtest_events, backtest_results.

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-05
"""

from __future__ import annotations

from alembic import op
from app.db import metadata

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    metadata.create_all(op.get_bind())


def downgrade() -> None:
    for table in ("backtest_results", "backtest_events", "backtest_runs"):
        op.drop_table(table)
