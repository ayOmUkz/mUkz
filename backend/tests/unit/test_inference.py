"""Tests for the evidence ledger and the six-state verdicts."""

from datetime import UTC, datetime
from decimal import Decimal

from app.analytics.inference import (
    Evidence,
    build_evidence,
    infer,
    invalidation_conditions,
)
from app.config import InferenceConfig

CFG = InferenceConfig()

ZONE = {
    "wavg_price": Decimal("100"),
    "price_low": Decimal("99"),
    "price_high": Decimal("101"),
    "unique_days": 3,
    "tightness_atr": 0.5,
}


def bar(day: int, low: float, high: float, close: float, volume: int) -> dict:
    return {
        "ts": datetime(2026, 8, day, 0, 0, tzinfo=UTC),
        "low": Decimal(str(low)),
        "high": Decimal(str(high)),
        "close": Decimal(str(close)),
        "volume": volume,
    }


def rising_market() -> list[dict]:
    """Higher lows; up days on heavy volume, the one down day on light volume."""
    closes = [100, 101, 100.5, 102, 103]
    volumes = [1_000, 10_000, 1_000, 10_000, 10_000]
    return [
        bar(3 + i, 99 + i, 102 + i, closes[i], volumes[i]) for i in range(5)
    ]


def falling_market() -> list[dict]:
    """Lower highs; down days on heavy volume, the one up day on light volume."""
    closes = [106, 105, 105.5, 103, 102]
    volumes = [1_000, 10_000, 1_000, 10_000, 10_000]
    return [
        bar(3 + i, 104 - i, 107 - i, closes[i], volumes[i]) for i in range(5)
    ]


def test_accumulation_case_builds_aligned_evidence():
    status = {"status": "respected", "respected_touches": 2, "break_to": None}
    items = build_evidence(ZONE, status, rising_market(), current_close=104.0)
    ids = {item.id for item in items}
    assert {"A_repeat_holding", "B_respected", "B_higher_lows", "C_up_volume"} <= ids
    verdict = infer(items, CFG)
    assert verdict["classification"] == "probable_accumulation"
    assert 0 < verdict["confidence"] <= CFG.confidence_cap
    assert verdict["net_weight"] >= CFG.probable_net_weight
    assert set(verdict["groups"]) >= {"A", "B", "C"}


def test_distribution_case_mirrors():
    status = {"status": "broken", "respected_touches": 0, "break_to": "below"}
    items = build_evidence(ZONE, status, falling_market(), current_close=96.0)
    verdict = infer(items, CFG)
    assert verdict["classification"] == "probable_distribution"
    assert verdict["net_weight"] <= -CFG.probable_net_weight
    assert verdict["supporting"] == []  # nothing leans accumulation here


def test_conflicting_evidence_is_neutral():
    items = [
        Evidence("a", "A", +1, 2, "prints holding"),
        Evidence("b", "B", -1, 2, "zone broken"),
        Evidence("c", "C", +1, 1, "up volume"),
    ]
    verdict = infer(items, CFG)  # net +1: below the 'possible' bar
    assert verdict["classification"] == "neutral_institutional_activity"
    assert verdict["confidence"] == 0.0
    assert len(verdict["contradicting"]) == 1


def test_possible_needs_less_than_probable():
    items = [
        Evidence("a", "A", +1, 2, "prints holding"),
        Evidence("c", "C", +1, 1, "up volume"),
    ]
    verdict = infer(items, CFG)  # net +3, 2 items, 2 groups
    assert verdict["classification"] == "possible_accumulation"


def test_single_group_or_thin_evidence_is_insufficient():
    same_group = [
        Evidence("a", "B", +1, 2, "respected"),
        Evidence("b", "B", +1, 2, "reclaimed"),
    ]
    assert infer(same_group, CFG)["classification"] == "insufficient_evidence"
    assert infer([], CFG)["classification"] == "insufficient_evidence"
    assert infer([], CFG)["confidence"] == 0.0


def test_confidence_is_hard_capped():
    stacked = [Evidence(f"e{i}", "ABC"[i % 3], +1, 3, "x") for i in range(10)]
    verdict = infer(stacked, CFG)
    assert verdict["classification"] == "probable_accumulation"
    assert verdict["confidence"] <= CFG.confidence_cap


def test_invalidation_levels_follow_direction():
    bullish = invalidation_conditions(ZONE, "probable_accumulation", atr=2.0)
    assert bullish[0]["type"] == "daily_close_below"
    assert bullish[0]["level"] == 98.0  # zone low 99 - 0.5 * ATR 2
    bearish = invalidation_conditions(ZONE, "possible_distribution", atr=2.0)
    assert bearish[0]["type"] == "daily_close_above"
    assert bearish[0]["level"] == 102.0
    assert invalidation_conditions(ZONE, "neutral_institutional_activity", atr=2.0) == []
    assert invalidation_conditions(ZONE, "insufficient_evidence", atr=2.0) == []
