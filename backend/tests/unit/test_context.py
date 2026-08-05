"""Tests for trend detection and context labels."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.analytics.context import context_label, signal_direction, trend_from_daily


def bars(closes: list[float]) -> list[dict]:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    return [
        {"ts": start + timedelta(days=i), "close": Decimal(str(close))}
        for i, close in enumerate(closes)
    ]


def test_trend_up_down_sideways_and_thin():
    rising = [100 + i for i in range(30)]
    falling = [130 - i for i in range(30)]
    flat = [100 + (i % 2) * 0.1 for i in range(30)]
    assert trend_from_daily(bars(rising)) == "up"
    assert trend_from_daily(bars(falling)) == "down"
    assert trend_from_daily(bars(flat)) == "sideways"
    assert trend_from_daily(bars([100.0] * 10)) is None  # thin history: no call


def test_signal_direction():
    assert signal_direction("probable_accumulation") == 1
    assert signal_direction("possible_distribution") == -1
    assert signal_direction("neutral_institutional_activity") == 0
    assert signal_direction("insufficient_evidence") == 0


def test_context_label_confirmations_and_conflicts():
    confirmed = context_label(
        direction=1, spy_trend="up", sector_trend_value="up", zone_status="respected"
    )
    assert confirmed["summary"] == "market_confirmed+sector_confirmed+technically_confirmed"

    conflicting = context_label(
        direction=1, spy_trend="down", sector_trend_value="up", zone_status=None
    )
    assert conflicting["summary"] == "conflicting"
    assert conflicting["conflicts"] == ["market"]

    isolated = context_label(
        direction=1, spy_trend="sideways", sector_trend_value=None, zone_status="untested"
    )
    assert isolated["summary"] == "isolated"

    bearish = context_label(
        direction=-1, spy_trend="down", sector_trend_value=None, zone_status="broken"
    )
    assert bearish["summary"] == "market_confirmed+technically_confirmed"


def test_context_label_neutral_direction_is_isolated():
    assert context_label(
        direction=0, spy_trend="up", sector_trend_value="up", zone_status="respected"
    )["summary"] == "isolated"
