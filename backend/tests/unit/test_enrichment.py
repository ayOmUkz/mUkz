"""Tests for candle normalization and the math built on candles."""

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from app.enrichment.candles import (
    compute_atr,
    normalize_candles,
    prior_day_levels,
    session_vwap,
)
from app.enrichment.stats import approx_percentile_of, size_distribution

CANDLES_FIXTURE = Path(__file__).parents[1] / "fixtures" / "candles_sample.json"


def bar(ts: str, o: float, h: float, low: float, c: float, vol: int = 1000) -> dict:
    return {
        "ticker": "T",
        "candle_size": "1d",
        "ts": datetime.fromisoformat(ts).replace(tzinfo=UTC),
        "open": Decimal(str(o)),
        "high": Decimal(str(h)),
        "low": Decimal(str(low)),
        "close": Decimal(str(c)),
        "volume": vol,
        "session": None,
    }


def test_normalize_real_short_alias_shape():
    rows = json.loads(CANDLES_FIXTURE.read_text(encoding="utf-8"))
    records, unparseable = normalize_candles(rows, ticker="TSM", candle_size="1h")
    assert unparseable == []
    assert len(records) == 3
    first = records[0]
    assert first["ts"] == datetime(2026, 8, 5, 16, 0, tzinfo=UTC)
    assert first["open"] == Decimal("414.48")   # float input
    assert first["high"] == Decimal("417.82")   # string input
    assert first["volume"] == 1404091
    assert first["session"] == "r"


def test_normalize_long_alias_and_daily_date_shapes():
    long_shape = {
        "start_time": "2026-08-05T14:30:00Z",
        "open": "100.0",
        "high": "101.0",
        "low": "99.0",
        "close": "100.5",
        "volume": 5000,
        "market_time": "r",
    }
    daily_shape = {"date": "2026-08-04", "open": 99, "high": 102, "low": 98, "close": 101}
    junk = {"open": "1.0"}  # no timestamp at all
    records, unparseable = normalize_candles(
        [long_shape, daily_shape, junk], ticker="X", candle_size="1d"
    )
    assert len(records) == 2
    assert records[0]["ts"] == datetime(2026, 8, 5, 14, 30, tzinfo=UTC)
    assert records[1]["ts"] == datetime(2026, 8, 4, 0, 0, tzinfo=UTC)
    assert records[1]["volume"] is None
    assert unparseable == [junk]


def test_session_vwap_typical_price_weighting():
    bars = [
        bar("2026-08-05T14:30:00", 100, 102, 98, 100, vol=100),   # typical 100
        bar("2026-08-05T14:31:00", 100, 111, 105, 108, vol=300),  # typical 108
    ]
    vwap = session_vwap(bars)
    assert vwap == Decimal("106.000000")  # (100*100 + 108*300) / 400


def test_session_vwap_prefers_regular_session_bars():
    regular = bar("2026-08-05T14:30:00", 100, 102, 98, 100, vol=100)
    regular["session"] = "r"
    premarket = bar("2026-08-05T12:00:00", 100, 202, 198, 200, vol=1000)
    premarket["session"] = "pre"
    assert session_vwap([premarket, regular]) == Decimal("100.000000")


def test_session_vwap_none_when_no_volume():
    assert session_vwap([bar("2026-08-05T14:30:00", 1, 1, 1, 1, vol=0)]) is None


def test_compute_atr_known_values():
    # 15 bars: close climbs 100..114; each day H=close+1, L=close-1, so with
    # prev_close = close-1 the true range is max(2, 2, 0) = 2 every day.
    bars = [
        bar(f"2026-07-{day:02d}T00:00:00", 100 + i, 101 + i, 99 + i, 100 + i)
        for i, day in enumerate(range(1, 16))
    ]
    assert compute_atr(bars, period=14) == 2.0


def test_compute_atr_needs_period_plus_one():
    bars = [bar(f"2026-07-{day:02d}T00:00:00", 1, 2, 1, 2) for day in range(1, 15)]
    assert compute_atr(bars, period=14) is None


def test_prior_day_levels_picks_last_earlier_bar():
    bars = [
        bar("2026-08-01T00:00:00", 1, 10, 1, 5),
        bar("2026-08-04T00:00:00", 5, 20, 4, 18),
        bar("2026-08-05T00:00:00", 18, 25, 17, 24),  # same day: excluded
    ]
    high, low, close = prior_day_levels(bars, date(2026, 8, 5))
    assert (high, low, close) == (Decimal("20"), Decimal("4"), Decimal("18"))
    assert prior_day_levels([], date(2026, 8, 5)) == (None, None, None)


def test_size_distribution_percentiles():
    stats = size_distribution(list(range(1, 1001)))  # 1..1000
    assert stats["sample_size"] == 1000
    assert stats["p50"] == 500.5
    assert abs(stats["p90"] - 900.1) < 0.2
    assert abs(stats["p99"] - 990.01) < 0.2
    assert stats["p999"] > 998
    assert stats["mad"] == 250.0
    assert size_distribution([])["sample_size"] == 0


def test_approx_percentile_interpolates():
    stats = {"p50": 100.0, "p90": 200.0, "p99": 300.0, "p999": 400.0}
    assert approx_percentile_of(50.0, stats) == 25.0    # below median: scaled
    assert approx_percentile_of(150.0, stats) == 70.0   # halfway p50->p90
    assert approx_percentile_of(250.0, stats) == 94.5   # halfway p90->p99
    assert approx_percentile_of(1000.0, stats) == 99.9  # beyond p999: capped
