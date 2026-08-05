"""M1 ingest tables: symbols, raw_prints, prints, quality log, probes, runs.

Revision ID: 0001
Revises:
Create Date: 2026-08-05

Creates every table from ``app.db.metadata`` (single source of truth — the
same metadata tests use) and converts the time-series tables to TimescaleDB
hypertables when the extension is available. On plain PostgreSQL the tables
work identically, just without Timescale partitioning.
"""

from __future__ import annotations

from alembic import op
from app.db import maybe_create_hypertables, metadata

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    metadata.create_all(bind)
    maybe_create_hypertables(bind)


def downgrade() -> None:
    bind = op.get_bind()
    metadata.drop_all(bind)
