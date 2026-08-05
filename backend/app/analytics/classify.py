"""Per-print classification (plan §7): size, location, timing, character.

Every function here is pure — inputs in, labels out — so each rule is
directly testable. Two principles carried from the plan:

* **Location is a feature, never a verdict.** No function in this module
  emits "bullish" or "bearish".
* All liquidity-character labels are hedged ("probable_", "possible_")
  because TRF prints never identify the aggressor.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from app.config import SizeClassConfig

ET = ZoneInfo("America/New_York")

#: Condition codes with near-zero directional information (plan §7).
DERIVATIVE_LINKED_TRADE_CODES = {"derivative_priced", "qualified_contingent_trade"}


def location_bucket(
    price: Decimal | None,
    bid: Decimal | None,
    ask: Decimal | None,
    *,
    spread_tolerance: float = 0.10,
) -> str | None:
    """Where in (or beyond) the quoted spread the execution sat.

    Position 0.0 = at the bid, 1.0 = at the ask. "At" means within
    ``spread_tolerance`` of the spread from that edge (or the midpoint).
    Returns None when there is no usable quote.
    """
    if price is None or bid is None or ask is None or bid <= 0 or ask <= bid:
        return None
    position = float((price - bid) / (ask - bid))
    tolerance = spread_tolerance
    if position < -tolerance:
        return "below_bid"
    if position <= tolerance:
        return "at_bid"
    if position >= 1 + tolerance:
        return "above_ask"
    if position >= 1 - tolerance:
        return "at_ask"
    if abs(position - 0.5) <= tolerance:
        return "at_mid"
    if position <= 0.25:
        return "near_bid"
    if position < 0.5:
        return "below_mid"
    if position >= 0.75:
        return "near_ask"
    return "above_mid"


def vwap_position(
    price: Decimal | None, vwap: Decimal | None, *, band_pct: float = 0.001
) -> str | None:
    if price is None or vwap is None or vwap <= 0:
        return None
    ratio = float(price / vwap) - 1.0
    if abs(ratio) <= band_pct:
        return "near"
    return "above" if ratio > 0 else "below"


def timing_bucket(
    executed_at: datetime, *, report_delay_s: float, late_report_seconds: int
) -> str:
    """Session bucket in Eastern Time; heavily delayed reports get their own
    bucket because they are often negotiated blocks (plan §7).

    Regular/half-day close times are not distinguished (documented
    approximation until an exchange calendar is added).
    """
    if report_delay_s > late_report_seconds:
        return "late_report"
    if executed_at.tzinfo is None:
        executed_at = executed_at.replace(tzinfo=UTC)
    eastern = executed_at.astimezone(ET)
    if eastern.weekday() >= 5:
        return "after_hours"
    minutes = eastern.hour * 60 + eastern.minute
    if minutes < 9 * 60 + 30:
        return "premarket"
    if minutes < 10 * 60:
        return "open"
    if minutes < 11 * 60 + 30:
        return "morning"
    if minutes < 13 * 60 + 30:
        return "lunch"
    if minutes < 15 * 60 + 30:
        return "afternoon"
    if minutes < 16 * 60:
        return "close"
    return "after_hours"


def size_classification(
    *,
    size: int,
    premium: Decimal,
    pct_adv30: float | None,
    stats: dict[str, Any] | None,
    config: SizeClassConfig,
) -> tuple[str, float | None, str]:
    """(size_class, estimated percentile, confidence).

    Primary path: compare against the symbol's own rolling distribution.
    Cold start (thin history): $-notional buckets, marked "provisional".
    A print above ``extreme_pct_adv30`` of 30-day ADV is always extreme —
    no distribution needed to know 1%+ of ADV in one print is exceptional.
    """
    from app.enrichment.stats import approx_percentile_of

    adv_extreme = pct_adv30 is not None and pct_adv30 >= config.extreme_pct_adv30

    if stats and stats.get("sample_size", 0) >= config.min_history_prints:
        estimated = approx_percentile_of(float(size), stats)
        if adv_extreme or (stats["p999"] is not None and size >= stats["p999"]):
            return "extreme", estimated, "historical"
        if size >= stats["p99"]:
            return "unusual", estimated, "historical"
        if size >= stats["p90"]:
            return "elevated", estimated, "historical"
        return "normal", estimated, "historical"

    buckets = config.cold_start_notional
    if adv_extreme or premium >= buckets.extreme:
        return "extreme", None, "provisional"
    if premium >= buckets.unusual:
        return "unusual", None, "provisional"
    if premium >= buckets.elevated:
        return "elevated", None, "provisional"
    return "normal", None, "provisional"


def liquidity_character(
    *,
    sale_cond_codes: str | None,
    trade_code: str | None,
    size: int,
    size_class: str,
    nbbo_bid_quantity: int | None,
    nbbo_ask_quantity: int | None,
    report_delay_s: float,
    location: str | None,
    late_report_seconds: int,
) -> str:
    """Best-effort liquidity character, condition codes first (plan §7)."""
    if sale_cond_codes == "odd_lot_execution":
        return "odd_lot"
    if sale_cond_codes == "average_price_trade":
        return "probable_vwap_execution"
    if trade_code in DERIVATIVE_LINKED_TRADE_CODES or sale_cond_codes == "contingent_trade":
        return "derivative_linked"
    at_or_outside_edges = location in (None, "below_bid", "above_ask", "at_bid", "at_ask")
    if sale_cond_codes == "prior_reference_price" or (
        size_class in ("unusual", "extreme")
        and report_delay_s > late_report_seconds
        and at_or_outside_edges
    ):
        return "possible_negotiated_block"
    displayed = (nbbo_bid_quantity or 0) + (nbbo_ask_quantity or 0)
    if displayed > 0 and size >= 50 * displayed and size_class != "normal":
        return "probable_dark_crossing"
    return "routine_off_exchange"
