"""The scoring stack (plan §11): five sub-scores and the DPSS.

``DPSS = (w·print + w·zone + w·direction + w·relevance) × quality/100`` —
data quality *multiplies* rather than adds, so bad data can only hurt a
score, never prop one up. Every function returns its component breakdown so
the dashboard can show the arithmetic.
"""

from __future__ import annotations

import math
from typing import Any

from app.config import DpssWeights, PrintSignificanceWeights

#: Percentile stand-ins when a print has no estimated percentile (cold start).
SIZE_CLASS_PERCENTILE_FALLBACK = {
    "normal": 50.0,
    "elevated": 90.0,
    "unusual": 99.0,
    "extreme": 99.9,
}
#: How informative each liquidity character is (plan §7/§11).
CHARACTER_SCORES = {
    "possible_negotiated_block": 100.0,
    "probable_dark_crossing": 80.0,
    "routine_off_exchange": 60.0,
    "probable_vwap_execution": 30.0,
    "derivative_linked": 10.0,
    "odd_lot": 0.0,
}
#: Session context: off-hours and late-reported blocks carry more signal.
TIMING_SCORES = {
    "late_report": 85.0,
    "premarket": 75.0,
    "after_hours": 75.0,
    "open": 70.0,
    "close": 70.0,
    "morning": 55.0,
    "afternoon": 55.0,
    "lunch": 50.0,
}
#: %ADV that earns full marks in print significance (1% of 30-day ADV).
FULL_MARKS_PRINT_PCT_ADV = 0.01
#: Trade relevance: full marks within 1 ATR of the zone, zero beyond 5.
RELEVANCE_NEAR_ATR, RELEVANCE_FAR_ATR = 1.0, 5.0
RELEVANCE_PROXIMITY_WEIGHT, RELEVANCE_FRESHNESS_WEIGHT = 0.6, 0.4


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def print_significance(row: dict[str, Any], weights: PrintSignificanceWeights) -> float:
    """0–100 significance of a single print."""
    size_pct = row.get("size_percentile")
    if size_pct is None:
        size_pct = SIZE_CLASS_PERCENTILE_FALLBACK.get(row.get("size_class") or "normal", 50.0)
    adv_score = _clamp01((row.get("pct_adv30") or 0.0) / FULL_MARKS_PRINT_PCT_ADV) * 100
    character_score = CHARACTER_SCORES.get(row.get("character") or "", 50.0)
    timing_score = TIMING_SCORES.get(row.get("timing_bucket") or "", 50.0)
    return round(
        weights.size_percentile * size_pct
        + weights.pct_adv30 * adv_score
        + weights.character * character_score
        + weights.timing * timing_score,
        2,
    )


def data_quality_score(
    prints_rows: list[dict[str, Any]], *, has_vwap: bool, has_atr: bool
) -> tuple[float, dict[str, float]]:
    """0–100 gate: how much the day's inputs can be trusted (plan §8/§11)."""
    if not prints_rows:
        return 0.0, {"clean_share": 0.0, "location_share": 0.0, "vwap": 0.0, "atr": 0.0}
    clean_share = sum(1 for row in prints_rows if not row["quality_flags"]) / len(prints_rows)
    location_values = {"ok": 1.0, "low": 0.5, "none": 0.0}
    location_share = sum(
        location_values.get(row["location_confidence"], 0.0) for row in prints_rows
    ) / len(prints_rows)
    components = {
        "clean_share": round(40 * clean_share, 2),
        "location_share": round(30 * location_share, 2),
        "vwap": 15.0 if has_vwap else 0.0,
        "atr": 15.0 if has_atr else 0.0,
    }
    return round(sum(components.values()), 2), components


def trade_relevance(
    *,
    current_close: float | None,
    zone_wavg: float,
    atr: float | None,
    sessions_since_last: int,
    half_life_sessions: int,
) -> tuple[float, dict[str, float]]:
    """0–100: is this zone actionable *now* (near price, still fresh)?"""
    if current_close is None:
        proximity = 0.0
    else:
        atr_value = atr if atr and atr > 0 else zone_wavg * 0.01
        distance_atr = abs(current_close - zone_wavg) / atr_value
        proximity = 100 * _clamp01(
            (RELEVANCE_FAR_ATR - distance_atr) / (RELEVANCE_FAR_ATR - RELEVANCE_NEAR_ATR)
        )
    freshness = 100 * math.exp(-math.log(2) * sessions_since_last / half_life_sessions)
    components = {
        "proximity": round(RELEVANCE_PROXIMITY_WEIGHT * proximity, 2),
        "freshness": round(RELEVANCE_FRESHNESS_WEIGHT * freshness, 2),
    }
    return round(sum(components.values()), 2), components


def dpss(
    *,
    print_score: float,
    zone_score: float,
    direction_score: float,
    relevance_score: float,
    quality_score: float,
    weights: DpssWeights,
) -> float:
    """The Dark Pool Significance Score, 0–100 (plan §11)."""
    weighted = (
        weights.print * print_score
        + weights.zone * zone_score
        + weights.direction * direction_score
        + weights.relevance * relevance_score
    )
    return round(weighted * quality_score / 100.0, 2)
