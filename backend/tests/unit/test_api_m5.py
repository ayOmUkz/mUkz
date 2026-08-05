"""Tests for the M5 dashboard endpoints (/status, /symbol/{ticker})."""

import json
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.analytics.analyze import analyze_day
from app.api.main import app, get_engine, get_settings
from app.config import Settings
from app.db import ensure_schema, make_engine
from app.enrichment.enrich import enrich_day
from app.ingestion.ingest import ingest_day

FIXTURE = Path(__file__).parents[1] / "fixtures" / "darkpool_recent_sample.json"
TRADING_DATE = date(2026, 8, 5)
BASE_PRICES = {"TSM": 415.0, "IWM": 300.0, "SGOV": 100.44}
SETTINGS = Settings.model_validate({"universe": {"watchlist": ["TSM", "IWM", "SGOV"]}})


def fixture_rows() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class FakeFullClient:
    def recent_darkpool_trades(self, **kwargs):
        return fixture_rows()

    def iter_ticker_darkpool_trades(self, ticker, **kwargs):
        yield from (row for row in fixture_rows() if row["ticker"] == ticker)

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
def client():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    ensure_schema(engine)
    ingest_day(engine, FakeFullClient(), SETTINGS, TRADING_DATE)
    enrich_day(engine, FakeFullClient(), SETTINGS, TRADING_DATE)
    analyze_day(engine, SETTINGS, TRADING_DATE)
    app.dependency_overrides[get_engine] = lambda: engine
    app.dependency_overrides[get_settings] = lambda: SETTINGS
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_status_endpoint(client):
    body = client.get("/status").json()
    assert body["latest_signal_date"] == "2026-08-05"
    assert body["counts"]["prints"] == 3
    assert body["counts"]["signals"] == 3
    assert body["counts"]["quarantined"] == 0
    assert body["last_run"]["date"] == "2026-08-05"
    assert body["last_run"]["stats"]["totals"]["clean"] == 3


def test_symbol_endpoint_serves_chart_data(client):
    body = client.get("/symbol/tsm").json()
    assert body["ticker"] == "TSM"
    assert body["date"] == "2026-08-05"
    assert len(body["candles"]) == 20
    assert body["candles"][-1]["time"] == "2026-08-05"
    assert body["vwap"] == 415.0
    assert body["atr"] == 4.0
    assert len(body["zones"]) == 1
    assert body["zones"][0]["wavg"] == 417.25
    assert len(body["prints"]) == 1
    assert body["prints"][0]["session"] == "2026-08-05"
    assert body["signal"]["classification"] == "insufficient_evidence"
    assert body["invalidation"] == []


def test_symbol_endpoint_404_for_unknown(client):
    assert client.get("/symbol/NOPE").status_code == 404


def test_cors_header_for_dashboard_origin(client):
    response = client.get("/status", headers={"Origin": "http://localhost:3000"})
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
