"""Tests for schema creation and idempotent storage on SQLite."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import sqlalchemy as sa

from app.db import ensure_schema, insert_ignore, make_engine, prints, raw_prints, symbols
from app.ingestion import store
from app.validation import validate_rows

FIXTURE = Path(__file__).parents[1] / "fixtures" / "darkpool_recent_sample.json"
AS_OF = datetime(2026, 8, 7, 0, 0, tzinfo=UTC)


@pytest.fixture()
def engine():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    ensure_schema(engine)
    return engine


def fixture_rows() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_store_raw_is_idempotent(engine):
    rows = fixture_rows()
    with engine.begin() as conn:
        inserted, unstorable = store.store_raw(conn, rows, ingested_at=AS_OF)
        assert (inserted, unstorable) == (3, [])
        # Same rows again (pagination overlap / re-run): nothing new.
        inserted_again, _ = store.store_raw(conn, rows, ingested_at=AS_OF)
        assert inserted_again == 0
        total = conn.execute(sa.select(sa.func.count()).select_from(raw_prints)).scalar()
    assert total == 3


def test_store_raw_reports_unstorable_rows(engine):
    junk = {"price": "1.00"}  # no ticker, no executed_at
    with engine.begin() as conn:
        inserted, unstorable = store.store_raw(conn, [junk], ingested_at=AS_OF)
    assert inserted == 0
    assert unstorable == [junk]


def test_store_prints_dedupes_on_identity(engine):
    result = validate_rows(fixture_rows(), as_of=AS_OF)
    with engine.begin() as conn:
        first = store.store_prints(
            conn, result.clean, late_report_seconds=900, ingested_at=AS_OF
        )
        second = store.store_prints(
            conn, result.clean, late_report_seconds=900, ingested_at=AS_OF
        )
        stored = conn.execute(sa.select(prints.c.ticker)).scalars().all()
    assert first == 3
    assert second == 0
    assert sorted(stored) == ["IWM", "SGOV", "TSM"]


def test_rejections_are_logged(engine):
    bad = {**fixture_rows()[0], "canceled": True}
    result = validate_rows([bad], as_of=AS_OF)
    with engine.begin() as conn:
        logged = store.log_rejections(conn, result.rejected, logged_at=AS_OF)
        row = conn.execute(sa.text("SELECT stage, reasons FROM data_quality_log")).one()
    assert logged == 1
    assert row.stage == "quality"
    assert "canceled" in row.reasons


def test_upsert_symbols_inserts_then_updates(engine):
    rows = fixture_rows()
    with engine.begin() as conn:
        store.upsert_symbols(conn, rows, seen_at=AS_OF)
        first = conn.execute(sa.select(symbols.c.ticker, symbols.c.sector)).all()

        later = datetime(2026, 8, 8, 0, 0, tzinfo=UTC)
        updated_rows = [{**rows[0], "sector": "Semiconductors"}]
        store.upsert_symbols(conn, updated_rows, seen_at=later)
        tsm = conn.execute(
            sa.select(symbols.c.sector, symbols.c.first_seen_at, symbols.c.last_seen_at).where(
                symbols.c.ticker == "TSM"
            )
        ).one()
    assert {ticker for ticker, _ in first} == {"TSM", "IWM", "SGOV"}
    assert tsm.sector == "Semiconductors"
    assert tsm.first_seen_at < tsm.last_seen_at  # first_seen preserved on update


def test_insert_ignore_returns_inserted_count(engine):
    record = {
        "ticker": "XYZ",
        "tracking_id": 1,
        "executed_at": AS_OF,
        "payload": {},
        "ingested_at": AS_OF,
    }
    with engine.begin() as conn:
        assert insert_ignore(conn, raw_prints, [record]) == 1
        assert insert_ignore(conn, raw_prints, [record]) == 0
