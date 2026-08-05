"""End-to-end M3 test: ingest -> enrich -> analyze on the fixture day."""

import json
from datetime import date, timedelta
from pathlib import Path

import pytest
import sqlalchemy as sa

from app.analytics.analyze import analyze_day, crosscheck_price_levels
from app.config import Settings
from app.db import ensure_schema, make_engine
from app.enrichment.enrich import enrich_day
from app.ingestion.ingest import ingest_day

FIXTURE = Path(__file__).parents[1] / "fixtures" / "darkpool_recent_sample.json"
TRADING_DATE = date(2026, 8, 5)
BASE_PRICES = {"TSM": 415.0, "IWM": 300.0, "SGOV": 100.44}


def fixture_rows() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class FakeIngestClient:
    def recent_darkpool_trades(self, **kwargs):
        return fixture_rows()

    def iter_ticker_darkpool_trades(self, ticker, **kwargs):
        yield from (row for row in fixture_rows() if row["ticker"] == ticker)


class FakeCandleClient:
    def ohlc(self, ticker, candle_size, **kwargs):
        base = BASE_PRICES[ticker]
        if candle_size == "1d":
            start = TRADING_DATE - timedelta(days=19)
            return [
                {
                    "date": (start + timedelta(days=i)).isoformat(),
                    "open": base, "high": base + 2, "low": base - 2,
                    "close": base + 1, "volume": 1_000_000,
                }
                for i in range(20)
            ]
        return [
            {
                "start": f"2026-08-05T18:{30 + i}:00Z",
                "o": base, "h": base + 1, "l": base - 1, "c": base,
                "vol": 1000, "market": "r",
            }
            for i in range(3)
        ]


@pytest.fixture()
def analyzed():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    ensure_schema(engine)
    settings = Settings.model_validate({"universe": {"watchlist": ["TSM", "IWM", "SGOV"]}})
    ingest_day(engine, FakeIngestClient(), settings, TRADING_DATE)
    enrich_day(engine, FakeCandleClient(), settings, TRADING_DATE)
    stats = analyze_day(engine, settings, TRADING_DATE)
    return engine, settings, stats


def test_analyze_day_builds_zones_and_signals(analyzed):
    engine, _, stats = analyzed
    assert stats["tickers"] == 3
    assert stats["signals"] == 3

    with engine.begin() as conn:
        zones = conn.execute(sa.text("SELECT * FROM zones")).mappings().all()
        signals = conn.execute(sa.text("SELECT * FROM signals")).mappings().all()
    assert len(zones) == 3  # one single-print zone per ticker
    for zone in zones:
        assert zone["print_count"] == 1
        assert zone["status"] == "untested"  # no bars exist after the print day
        assert 0 <= zone["strength_score"] <= 100
        assert zone["strength_class"] in ("weak", "moderate", "strong", "exceptional")

    for signal in signals:
        # One print, flat context: honest answer is "insufficient evidence".
        assert signal["classification"] == "insufficient_evidence"
        assert signal["confidence"] == 0.0
        sub_scores = json.loads(signal["sub_scores"])
        assert set(sub_scores) >= {"print", "zone", "direction", "relevance", "quality"}
        assert sub_scores["quality"] == 100.0
        assert signal["dpss"] > 0


def test_analyze_signal_snapshot_is_self_contained(analyzed):
    engine, _, _ = analyzed
    with engine.begin() as conn:
        signal = conn.execute(
            sa.text("SELECT top_zone, invalidation FROM signals WHERE ticker = 'TSM'")
        ).mappings().one()
    top_zone = json.loads(signal["top_zone"])
    assert top_zone["wavg_price"] == 417.25
    assert top_zone["strength_components"].keys() >= {"pct_adv30", "recurrence", "recency"}
    assert json.loads(signal["invalidation"]) == []  # no direction, nothing to invalidate


def test_analyze_day_is_idempotent_and_signals_immutable(analyzed):
    engine, settings, _ = analyzed
    with engine.begin() as conn:
        first_available = conn.execute(
            sa.text("SELECT available_at FROM signals WHERE ticker = 'TSM'")
        ).scalar()

    again = analyze_day(engine, settings, TRADING_DATE)
    assert again["signals"] == 0  # insert-ignore: signals are immutable

    with engine.begin() as conn:
        zone_count = conn.execute(sa.text("SELECT count(*) FROM zones")).scalar()
        signal_count = conn.execute(sa.text("SELECT count(*) FROM signals")).scalar()
        available = conn.execute(
            sa.text("SELECT available_at FROM signals WHERE ticker = 'TSM'")
        ).scalar()
    assert zone_count == 3  # rebuilt, not duplicated
    assert signal_count == 3
    assert available == first_available


def test_crosscheck_price_levels_math():
    provider = {
        "stock_price_vol": [
            {"price": "100", "dark_pool_volume": 600, "regular_volume": 50},
            {"price": "101", "dark_pool_volume": 400, "regular_volume": 10},
        ]
    }
    good = crosscheck_price_levels(950, provider)
    assert good["within_tolerance"] is True
    assert good["ratio"] == 0.95

    bad = crosscheck_price_levels(400, provider)
    assert bad["within_tolerance"] is False

    empty = crosscheck_price_levels(1000, {"stock_price_vol": []})
    assert empty["comparable"] is False
