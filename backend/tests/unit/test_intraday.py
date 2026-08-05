"""M7 tests: cooldowns, the intraday collector, live websocket, group D."""

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from app.alerts.cooldown import InMemoryCooldownStore, RedisCooldownStore
from app.analytics.inference import build_evidence
from app.api.main import app
from app.config import Settings
from app.db import ensure_schema, make_engine, symbol_stats
from app.enrichment.enrich import enrich_day, fetch_options_tilt
from app.ingestion.ingest import ingest_day
from app.intraday import IntradayCollector, LiveHub, live_hub

FIXTURE = Path(__file__).parents[1] / "fixtures" / "darkpool_recent_sample.json"
NOW = datetime(2026, 8, 5, 16, 30, tzinfo=UTC)
SETTINGS = Settings()


# ------------------------------------------------------------- cooldowns


def test_in_memory_cooldown_expires():
    clock = {"t": 0.0}
    store = InMemoryCooldownStore(clock=lambda: clock["t"])
    assert store.acquire("k", ttl_seconds=60) is True
    assert store.acquire("k", ttl_seconds=60) is False
    clock["t"] = 61.0
    assert store.acquire("k", ttl_seconds=60) is True


def test_redis_cooldown_uses_setnx_with_ttl():
    calls = []

    class FakeRedis:
        def __init__(self):
            self.keys = set()

        def set(self, name, value, nx=False, ex=None):
            calls.append((name, nx, ex))
            if name in self.keys:
                return None
            self.keys.add(name)
            return True

    store = RedisCooldownStore(FakeRedis())
    assert store.acquire("k", ttl_seconds=120) is True
    assert store.acquire("k", ttl_seconds=120) is False
    assert calls[0] == ("darkpool:cooldown:k", True, 120)


# ------------------------------------------------------------- collector


def fixture_rows() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def huge_print() -> dict:
    row = dict(fixture_rows()[0])  # TSM
    row.update(
        tracking_id=999_001,
        size=500_000,
        premium=str(Decimal("417.25") * 500_000),
        executed_at="2026-08-05T16:29:00Z",
        created_at="2026-08-05T16:29:01Z",
        trf_executed_at="2026-08-05T16:29:00Z",
    )
    return row


class FakeRecentClient:
    def __init__(self):
        self.batches = [fixture_rows() + [huge_print()]]
        self.calls = 0

    def recent_darkpool_trades(self, **kwargs):
        self.calls += 1
        return self.batches[min(self.calls - 1, len(self.batches) - 1)]


@pytest.fixture()
def collector_setup():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    ensure_schema(engine)
    with engine.begin() as conn:
        # Nightly stats for TSM: p999 = 100k shares -> the 500k print is extreme.
        conn.execute(symbol_stats.insert().values(
            ticker="TSM", as_of_date=date(2026, 8, 4), sample_size=1000,
            p50=2000.0, p90=10_000.0, p99=50_000.0, p999=100_000.0, mad=1500.0,
            updated_at=NOW,
        ))
    hub = LiveHub()
    queue = hub.subscribe()
    collector = IntradayCollector(
        engine, FakeRecentClient(), SETTINGS, hub, InMemoryCooldownStore(),
        now_fn=lambda: NOW,
    )
    return engine, collector, queue


def drain(queue) -> list[dict]:
    messages = []
    while not queue.empty():
        messages.append(queue.get_nowait())
    return messages


def test_collector_stores_publishes_and_alerts_once(collector_setup):
    engine, collector, queue = collector_setup

    stats = collector.poll_once()
    assert stats["fetched"] == 4
    assert stats["new"] == 4
    assert stats["clean"] == 4
    assert stats["published"] == 4
    assert stats["alerts"] == 1  # only the 500k-share TSM print is extreme

    messages = drain(queue)
    types = [message["type"] for message in messages]
    assert types.count("print") == 4
    assert types.count("alert") == 1
    alert = next(m for m in messages if m["type"] == "alert")
    assert alert["ticker"] == "TSM"
    assert alert["size_class"] == "extreme"
    assert alert["rule"] == "intraday_extreme_print"

    with engine.begin() as conn:
        stored_prints = conn.execute(sa.text("SELECT count(*) FROM prints")).scalar()
        stored_alerts = conn.execute(sa.text("SELECT count(*) FROM alerts")).scalar()
    assert stored_prints == 4
    assert stored_alerts == 1

    # Second poll: same tape -> nothing new, nothing republished, no dup alert.
    stats2 = collector.poll_once()
    assert stats2["new"] == 0
    assert stats2["published"] == 0
    assert stats2["alerts"] == 0
    assert drain(queue) == []


def test_collector_cold_start_uses_notional_fallback(collector_setup):
    engine, collector, queue = collector_setup
    collector.poll_once()
    messages = drain(queue)
    # IWM has no stored stats: $1.79M premium -> elevated via notional buckets.
    iwm = next(m for m in messages if m["ticker"] == "IWM")
    assert iwm["size_class"] == "elevated"


def test_slow_subscriber_drops_oldest_not_the_hub():
    hub = LiveHub(queue_size=2)
    queue = hub.subscribe()
    for index in range(5):
        hub.publish({"n": index})
    assert queue.qsize() == 2
    assert queue.get_nowait()["n"] == 3  # oldest dropped, newest kept
    assert queue.get_nowait()["n"] == 4


# ------------------------------------------------------------- websocket


def test_ws_live_pushes_hub_messages():
    client = TestClient(app)
    with client.websocket_connect("/ws/live") as websocket:
        live_hub.publish({"type": "print", "ticker": "TSM"})
        message = websocket.receive_json()
    assert message == {"type": "print", "ticker": "TSM"}
    assert live_hub.subscriber_count == 0  # cleaned up after disconnect


# ---------------------------------------------------- options tilt (D)


ZONE = {"wavg_price": Decimal("100"), "price_low": Decimal("99"),
        "price_high": Decimal("101"), "unique_days": 1, "tightness_atr": 0.5}
NO_STATUS = {"status": "untested", "respected_touches": 0, "break_to": None}


def test_options_tilt_generates_group_d_evidence():
    bullish = build_evidence(
        ZONE, NO_STATUS, [], current_close=100.0,
        options_tilt={"call_premium": Decimal("3000000"), "put_premium": Decimal("1000000")},
    )
    assert any(item.id == "D_call_tilt" and item.group == "D" for item in bullish)

    bearish = build_evidence(
        ZONE, NO_STATUS, [], current_close=100.0,
        options_tilt={"call_premium": Decimal("1000000"), "put_premium": Decimal("2000000")},
    )
    assert any(item.id == "D_put_tilt" for item in bearish)

    balanced = build_evidence(
        ZONE, NO_STATUS, [], current_close=100.0,
        options_tilt={"call_premium": Decimal("1000000"), "put_premium": Decimal("1000000")},
    )
    assert not any(item.group == "D" for item in balanced)

    assert not any(item.group == "D"
                   for item in build_evidence(ZONE, NO_STATUS, [], current_close=100.0))


def test_fetch_options_tilt_tolerant_and_guarded():
    class WithVolume:
        def options_volume(self, ticker, limit=1):
            return [{"date": "2026-08-05", "call_premium": "3000000.5",
                     "put_premium": 1000000}]

    tilt = fetch_options_tilt(WithVolume(), "TSM")
    assert tilt == {"call_premium": Decimal("3000000.5"),
                    "put_premium": Decimal("1000000")}

    class Without:
        pass

    assert fetch_options_tilt(Without(), "TSM") is None

    class Junk:
        def options_volume(self, ticker, limit=1):
            return [{"date": "2026-08-05"}]  # no premium fields

    assert fetch_options_tilt(Junk(), "TSM") is None


def test_enrich_persists_options_tilt():
    from datetime import timedelta

    trading_date = date(2026, 8, 5)
    base = {"TSM": 415.0, "IWM": 300.0, "SGOV": 100.44}

    class FakeFullClient:
        def recent_darkpool_trades(self, **kwargs):
            return fixture_rows()

        def iter_ticker_darkpool_trades(self, ticker, **kwargs):
            yield from (r for r in fixture_rows() if r["ticker"] == ticker)

        def ohlc(self, ticker, candle_size, **kwargs):
            price = base[ticker]
            if candle_size == "1d":
                start = trading_date - timedelta(days=19)
                return [{"date": (start + timedelta(days=i)).isoformat(),
                         "open": price, "high": price + 2, "low": price - 2,
                         "close": price + 1, "volume": 1_000_000} for i in range(20)]
            return [{"start": f"2026-08-05T18:{30 + i}:00Z", "o": price,
                     "h": price + 1, "l": price - 1, "c": price, "vol": 1000,
                     "market": "r"} for i in range(3)]

        def options_volume(self, ticker, limit=1):
            return [{"call_premium": 2_000_000, "put_premium": 500_000}]

    engine = make_engine("sqlite+pysqlite:///:memory:")
    ensure_schema(engine)
    settings = Settings.model_validate({"universe": {"watchlist": ["TSM", "IWM", "SGOV"]}})
    ingest_day(engine, FakeFullClient(), settings, trading_date)
    enrich_day(engine, FakeFullClient(), settings, trading_date)
    with engine.begin() as conn:
        row = conn.execute(sa.text(
            "SELECT call_premium, put_premium FROM symbol_days WHERE ticker = 'TSM'"
        )).one()
    assert float(row.call_premium) == 2_000_000
    assert float(row.put_premium) == 500_000
