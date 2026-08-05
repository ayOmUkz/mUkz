"""End-to-end pipeline test: fake client -> validate -> SQLite -> stats."""

import json
from datetime import date
from pathlib import Path

import pytest
import sqlalchemy as sa

from app.client.uw_client import UWAPIError
from app.config import Settings
from app.db import ensure_schema, make_engine
from app.ingestion.ingest import build_universe, ingest_day, session_cutoff

FIXTURE = Path(__file__).parents[1] / "fixtures" / "darkpool_recent_sample.json"
TRADING_DATE = date(2026, 8, 5)


def fixture_rows() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class FakeClient:
    """Serves the recorded fixture rows the way the pipeline consumes them."""

    def __init__(self):
        rows = fixture_rows()
        canceled = {**rows[0], "tracking_id": 999, "canceled": True}
        unparseable = {**rows[1], "tracking_id": 998, "price": None}
        self.by_ticker = {
            "TSM": [rows[0], canceled, unparseable],
            "IWM": [rows[1]],
            "SGOV": [rows[2]],
        }
        self.deep_fetches: list[str] = []

    def recent_darkpool_trades(self, **kwargs):
        return [row for rows in self.by_ticker.values() for row in rows]

    def iter_ticker_darkpool_trades(self, ticker, **kwargs):
        self.deep_fetches.append(ticker)
        if ticker == "FAIL":
            raise UWAPIError("boom", status_code=500)
        yield from self.by_ticker.get(ticker, [])


@pytest.fixture()
def engine():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    ensure_schema(engine)
    return engine


def settings_with(watchlist: list[str]) -> Settings:
    return Settings.model_validate({"universe": {"watchlist": watchlist}})


def test_session_cutoff_is_reproducible():
    cutoff = session_cutoff(TRADING_DATE)
    assert cutoff.isoformat() == "2026-08-07T00:00:00+00:00"


def test_build_universe_watchlist_first_and_capped():
    universe = build_universe(["SPY", "QQQ"], ["NVDA", "SPY", "TSM"], cap=3)
    assert universe == ["SPY", "QQQ", "NVDA"]


def test_ingest_day_full_flow(engine):
    client = FakeClient()
    stats = ingest_day(engine, client, settings_with(["TSM", "IWM", "SGOV"]), TRADING_DATE)

    assert stats["totals"] == {
        "fetched": 5,
        "raw_inserted": 5,     # canceled + unparseable rows ARE stored raw
        "prints_inserted": 3,  # ...but only clean ones reach `prints`
        "clean": 3,
        "flagged": 0,
        "rejected": 2,
        "unstorable": 0,
    }
    with engine.begin() as conn:
        raw = conn.execute(sa.text("SELECT count(*) FROM raw_prints")).scalar()
        clean = conn.execute(sa.text("SELECT count(*) FROM prints")).scalar()
        quarantined = conn.execute(sa.text("SELECT count(*) FROM data_quality_log")).scalar()
        run = conn.execute(sa.text("SELECT run_date, finished_at, stats FROM ingest_runs")).one()
    assert (raw, clean, quarantined) == (5, 3, 2)
    assert run.finished_at is not None
    assert json.loads(run.stats)["date"] == "2026-08-05"


def test_ingest_day_is_idempotent(engine):
    client = FakeClient()
    settings = settings_with(["TSM", "IWM", "SGOV"])
    ingest_day(engine, client, settings, TRADING_DATE)
    second = ingest_day(engine, client, settings, TRADING_DATE)

    assert second["totals"]["raw_inserted"] == 0
    assert second["totals"]["prints_inserted"] == 0
    with engine.begin() as conn:
        clean = conn.execute(sa.text("SELECT count(*) FROM prints")).scalar()
    assert clean == 3  # no double counting on re-runs


def test_one_failing_ticker_does_not_sink_the_day(engine):
    client = FakeClient()
    stats = ingest_day(engine, client, settings_with(["TSM", "FAIL", "IWM"]), TRADING_DATE)
    assert "FAIL" in stats["errors"]
    assert stats["per_ticker"]["TSM"]["clean"] == 1
    assert stats["per_ticker"]["IWM"]["clean"] == 1


def test_discovery_failure_still_ingests_watchlist(engine):
    client = FakeClient()

    def broken_discovery(**kwargs):
        raise UWAPIError("discovery down", status_code=503)

    client.recent_darkpool_trades = broken_discovery
    stats = ingest_day(engine, client, settings_with(["TSM"]), TRADING_DATE)
    assert stats["discovery_error"] is not None
    assert stats["per_ticker"]["TSM"]["clean"] == 1
