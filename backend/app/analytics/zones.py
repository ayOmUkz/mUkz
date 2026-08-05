"""Dark-pool price zones: clustering, metrics, strength, status (plan §9).

*Analogy: don't mark every spot an elephant stood — find the watering holes
they keep returning to.*

Only prints of class ``elevated`` or higher enter clustering, and odd lots
never do. Clustering is 1-D single-linkage on price: sort, then merge
neighbors while the gap stays within an ATR-scaled tolerance, so "one
level" means the same thing for a $12 stock and a $1,200 stock.
"""

from __future__ import annotations

import math
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from app.config import ZoneEpsilonConfig, ZonesConfig, ZoneStrengthWeights

ET = ZoneInfo("America/New_York")

ELIGIBLE_SIZE_CLASSES = ("elevated", "unusual", "extreme")
STRENGTH_CLASSES = ((80.0, "exceptional"), (60.0, "strong"), (40.0, "moderate"))
#: Full pct-of-ADV marks at 5% of 30-day ADV inside one zone (plan §9).
FULL_MARKS_PCT_ADV = 0.05
#: Sessions with distinct qualifying prints needed for full recurrence marks.
FULL_MARKS_RECURRENCE_DAYS = 5
#: Fallback "ATR" when no volatility context exists: 1% of the zone price.
FALLBACK_ATR_FRACTION = 0.01


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def tick_size(price: Decimal) -> Decimal:
    return Decimal("0.01") if price >= 1 else Decimal("0.0001")


def epsilon_for(price: Decimal, atr: float | None, config: ZoneEpsilonConfig) -> Decimal:
    """Cluster tolerance at a price level: max of the three configured knobs."""
    candidates = [
        Decimal(str(config.pct_of_price)) * price,
        config.min_ticks * tick_size(price),
    ]
    if atr is not None and atr > 0:
        candidates.append(Decimal(str(config.atr_mult * atr)))
    return max(candidates)


def eligible_prints(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if row.get("size_class") in ELIGIBLE_SIZE_CLASSES and row.get("character") != "odd_lot"
    ]


def cluster_prints(
    rows: list[dict[str, Any]], *, atr: float | None, config: ZoneEpsilonConfig
) -> list[list[dict[str, Any]]]:
    """Single-linkage 1-D clustering on execution price."""
    ordered = sorted(rows, key=lambda row: row["price"])
    clusters: list[list[dict[str, Any]]] = []
    for row in ordered:
        if clusters and row["price"] - clusters[-1][-1]["price"] <= epsilon_for(
            clusters[-1][-1]["price"], atr, config
        ):
            clusters[-1].append(row)
        else:
            clusters.append([row])
    return clusters


def sessions_between(start: date, end: date) -> int:
    """Weekdays strictly after ``start`` up to and including ``end``."""
    if end <= start:
        return 0
    count = 0
    current = start + timedelta(days=1)
    while current <= end:
        if current.weekday() < 5:
            count += 1
        current += timedelta(days=1)
    return count


def zone_metrics(
    cluster: list[dict[str, Any]],
    *,
    as_of: date,
    atr: float | None,
    window_total_shares: int,
) -> dict[str, Any]:
    """Everything the plan (§9) asks to know about one zone."""
    total_shares = sum(row["size"] for row in cluster)
    weighted = sum(row["price"] * row["size"] for row in cluster)
    wavg = (weighted / total_shares).quantize(Decimal("0.000001"))
    prices = [row["price"] for row in cluster]
    executed = [_as_utc(row["executed_at"]) for row in cluster]
    unique_days = len({ts.astimezone(ET).date() for ts in executed})
    avg30_values = [row["avg30_volume"] for row in cluster if row.get("avg30_volume")]
    avg30 = max(avg30_values) if avg30_values else None
    width = prices[-1] - prices[0] if len(prices) > 1 else Decimal(0)
    return {
        "price_low": min(prices),
        "price_high": max(prices),
        "wavg_price": wavg,
        "total_shares": total_shares,
        "total_notional": sum(row["premium"] for row in cluster),
        "print_count": len(cluster),
        "unique_days": unique_days,
        "first_print_at": min(executed),
        "last_print_at": max(executed),
        "pct_adv30": float(total_shares / avg30) if avg30 else None,
        "pct_dark_volume": (
            total_shares / window_total_shares if window_total_shares else None
        ),
        "tightness_atr": float(width) / atr if atr else None,
        "sessions_since_last": sessions_between(
            max(executed).astimezone(ET).date(), as_of
        ),
    }


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def strength_score(
    metrics: dict[str, Any],
    status: dict[str, Any],
    *,
    weights: ZoneStrengthWeights,
    config: ZonesConfig,
) -> tuple[float, dict[str, float]]:
    """0–100 zone strength; returns (score, per-component breakdown).

    Every component is a 0–1 fraction times its configured weight, so the
    dashboard can always "show its work" (plan §9).
    """
    pct_adv = metrics.get("pct_adv30")
    adv_fraction = (
        _clamp01(math.log1p(9 * (pct_adv / FULL_MARKS_PCT_ADV)) / math.log1p(9))
        if pct_adv
        else 0.0
    )
    recurrence_fraction = _clamp01(metrics["unique_days"] / FULL_MARKS_RECURRENCE_DAYS)
    recency_fraction = math.exp(
        -math.log(2) * metrics["sessions_since_last"] / config.recency_half_life_sessions
    )
    tightness = metrics.get("tightness_atr")
    # Full marks when the zone spans ≤ 0.5 ATR, zero by 2 ATR; neutral without ATR.
    tightness_fraction = (
        _clamp01((2.0 - tightness) / 1.5) if tightness is not None else 0.5
    )
    concentration_fraction = _clamp01(metrics.get("pct_dark_volume") or 0.0)
    reaction_fraction = _clamp01(
        0.5
        + 0.25 * status.get("respected_touches", 0)
        + (0.25 if status.get("status") == "reclaimed" else 0.0)
        - (0.5 if status.get("status") == "broken" else 0.0)
    )
    components = {
        "pct_adv30": round(adv_fraction * weights.pct_adv30, 2),
        "recurrence": round(recurrence_fraction * weights.recurrence, 2),
        "recency": round(recency_fraction * weights.recency, 2),
        "tightness": round(tightness_fraction * weights.tightness, 2),
        "concentration": round(concentration_fraction * weights.concentration, 2),
        "reactions": round(reaction_fraction * weights.reactions, 2),
    }
    return round(sum(components.values()), 2), components


def strength_class(score: float) -> str:
    for threshold, label in STRENGTH_CLASSES:
        if score >= threshold:
            return label
    return "weak"


def track_zone_status(
    metrics: dict[str, Any],
    daily: list[dict[str, Any]],
    *,
    atr: float | None,
    config: ZonesConfig,
) -> dict[str, Any]:
    """Walk the daily bars after the zone formed and classify its life so far.

    States: untested → tested → respected, with broken → reclaimed on top.
    "Respected" needs a touch that closes ``respected_atr_mult`` ATRs back on
    the side price came from; "broken" needs a close ``broken_atr_mult`` ATRs
    beyond the far edge; "reclaimed" needs a close back across the zone
    within ``reclaim_window_sessions`` sessions of the break.
    """
    zone_low = float(metrics["price_low"])
    zone_high = float(metrics["price_high"])
    atr_value = atr if atr and atr > 0 else float(metrics["wavg_price"]) * FALLBACK_ATR_FRACTION
    respect_threshold = config.respected_atr_mult * atr_value
    break_threshold = config.broken_atr_mult * atr_value
    formed_date = _as_utc(metrics["first_print_at"]).astimezone(ET).date()

    state = "untested"
    respected = 0
    events: list[dict[str, Any]] = []
    previous_side: str | None = None
    break_to: str | None = None
    break_index: int | None = None

    bars = sorted(
        (bar for bar in daily if bar["ts"].date() > formed_date), key=lambda b: b["ts"]
    )
    for index, bar in enumerate(bars):
        low, high, close = float(bar["low"]), float(bar["high"]), float(bar["close"])
        session = bar["ts"].date()

        if state == "broken" and break_index is not None:
            within_window = index - break_index <= config.reclaim_window_sessions
            recrossed = (break_to == "below" and close >= zone_high) or (
                break_to == "above" and close <= zone_low
            )
            if within_window and recrossed:
                state = "reclaimed"
                events.append({"session_date": session, "event": "reclaim", "close": close})

        touched = low <= zone_high and high >= zone_low
        if touched:
            events.append({"session_date": session, "event": "touch", "close": close})
            if state == "untested":
                state = "tested"
            bounced = previous_side == "above" and close >= zone_high + respect_threshold
            bounced |= previous_side == "below" and close <= zone_low - respect_threshold
            if bounced:
                respected += 1
                events.append({"session_date": session, "event": "reject", "close": close})
                if state in ("tested", "respected"):
                    state = "respected"

        broke_down = previous_side == "above" and close <= zone_low - break_threshold
        broke_up = previous_side == "below" and close >= zone_high + break_threshold
        if state != "broken" and (broke_down or broke_up):
            state = "broken"
            break_to = "below" if broke_down else "above"
            break_index = index
            events.append({"session_date": session, "event": "break", "close": close})

        if close > zone_high:
            previous_side = "above"
        elif close < zone_low:
            previous_side = "below"

    return {
        "status": state,
        "respected_touches": respected,
        "break_to": break_to,
        "events": events,
    }
