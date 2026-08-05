"""End-to-end M2 test: ingest fixture day -> enrich -> classified tape."""

import json
from datetime import date, timedelta
from pathlib import Path

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from app.api.main import app, get_engine
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
    """Daily bars in date-only shape; minute bars in short-alias shape."""

    def ohlc(self, ticker, candle_size, **kwargs):
        base = BASE_PRICES[ticker]
        if candle_size == "1d":
            start = TRADING_DATE - timedelta(days=19)
            return [
                {
                    "date": (start + timedelta(days=i)).isoformat(),
                    "open": base,
                    "high": base + 2,
                    "low": base - 2,
                    "close": base + 1,
                    "volume": 1_000_000,
                }
                for i in range(20)
            ]
        return [
            {
                "start": f"2026-08-05T18:{30 + i}:00Z",
                "o": base,
                "h": base + 1,
                "l": base - 1,
                "c": base,
                "vol": 1000,
                "market": "r",
            }
            for i in range(3)
        ]


@pytest.fixture()
def engine():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    ensure_schema(engine)
    return engine


@pytest.fixture()
def enriched(engine):
    settings = Settings.model_validate({"universe": {"watchlist": ["TSM", "IWM", "SGOV"]}})
    ingest_day(engine, FakeIngestClient(), settings, TRADING_DATE)
    stats = enrich_day(engine, FakeCandleClient(), settings, TRADING_DATE)
    return engine, settings, stats


def classified_rows(engine) -> dict[str, dict]:
    with engine.begin() as conn:
        rows = conn.execute(sa.text("SELECT * FROM prints")).mappings().all()
    return {row["ticker"]: dict(row) for row in rows}


def test_enrich_day_classifies_every_print(enriched):
    engine, _, stats = enriched
    assert stats["tickers"] == 3
    assert stats["classified"] == 3
    assert stats["errors"] == {}

    rows = classified_rows(engine)
    tsm, iwm, sgov = rows["TSM"], rows["IWM"], rows["SGOV"]

    # Cold start (sample of 1): notional buckets, marked provisional.
    for row in rows.values():
        assert row["size_class"] == "elevated"  # all three prints are $1M-$5M
        assert row["size_confidence"] == "provisional"
        assert row["timing_bucket"] == "lunch"  # 16:28 UTC = 12:28 ET

    # Location comes straight from the recorded NBBO of each real print.
    assert tsm["location_bucket"] == "below_bid"   # 417.25 vs 417.34/417.46
    assert iwm["location_bucket"] == "above_ask"   # 301.01 vs 300.99/301.00
    assert sgov["location_bucket"] == "at_mid"     # 100.445 vs 100.44/100.45

    # VWAP of the fake minute bars == base price per ticker.
    assert tsm["vwap_position"] == "above"
    assert iwm["vwap_position"] == "above"
    assert sgov["vwap_position"] == "near"

    # TSM's 5487 shares dwarf the 101 displayed shares -> probable crossing.
    assert tsm["character"] == "probable_dark_crossing"
    assert iwm["character"] == "routine_off_exchange"


def test_enrich_day_writes_context_and_stats(enriched):
    engine, _, _ = enriched
    with engine.begin() as conn:
        day = conn.execute(
            sa.text("SELECT * FROM symbol_days WHERE ticker = 'TSM'")
        ).mappings().one()
        stat = conn.execute(
            sa.text("SELECT * FROM symbol_stats WHERE ticker = 'TSM'")
        ).mappings().one()
        candle_count = conn.execute(sa.text("SELECT count(*) FROM candles")).scalar()
    assert float(day["session_vwap"]) == 415.0
    assert day["atr14"] == 4.0  # constant true range of the fake dailies
    assert float(day["prior_high"]) == 417.0  # Aug 4 bar: base + 2
    assert day["minute_bars"] == 3
    assert stat["sample_size"] == 1
    assert candle_count == 3 * (20 + 3)  # per ticker: 20 daily + 3 minute bars


def test_enrich_day_is_idempotent(enriched):
    engine, settings, _ = enriched
    again = enrich_day(engine, FakeCandleClient(), settings, TRADING_DATE)
    assert again["classified"] == 3
    with engine.begin() as conn:
        candle_count = conn.execute(sa.text("SELECT count(*) FROM candles")).scalar()
        day_rows = conn.execute(sa.text("SELECT count(*) FROM symbol_days")).scalar()
    assert candle_count == 3 * (20 + 3)  # no duplicates
    assert day_rows == 3


def test_tape_endpoint_serves_classified_prints(enriched):
    engine, _, _ = enriched
    app.dependency_overrides[get_engine] = lambda: engine
    try:
        client = TestClient(app)
        response = client.get(
            "/tape", params={"ticker": "tsm", "date": TRADING_DATE.isoformat()}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ticker"] == "TSM"
        assert body["count"] == 1
        print_ = body["prints"][0]
        assert print_["size_class"] == "elevated"
        assert print_["location_bucket"] == "below_bid"
        assert print_["timing_bucket"] == "lunch"
        assert print_["character"] == "probable_dark_crossing"
        assert print_["price"] == 417.25
        assert print_["quality_flags"] == []
    finally:
        app.dependency_overrides.clear()
