"""Score-weighted Position Personality classifier (V1 Path A).

5 primary labels x 3 qualifiers = 15 two-tier labels + Mixed Exposure fallback.
Single-leg only in Path A — multi-leg qualifiers (Defined-Risk, Calendar) ship in V2.
"""

from __future__ import annotations

from app.schemas import (
    AxisName,
    Classification,
    EnrichedPosition,
    ForceScore,
    ForceScores,
    PrimaryLabel,
)

_CONFIDENCE_THRESHOLD = 0.3
_GREEK_AXES: tuple[AxisName, ...] = ("delta", "gamma", "theta", "vega")


def _rank_greek_axes(scores: ForceScores) -> list[tuple[AxisName, ForceScore]]:
    """Rank Greek axes by magnitude descending. Premium Fairness is treated as a
    modifier, not a dominant force on its own — it influences qualifiers."""
    by_axis = scores.by_axis()
    ranked: list[tuple[AxisName, ForceScore]] = [(a, by_axis[a]) for a in _GREEK_AXES]
    ranked.sort(key=lambda x: x[1].magnitude, reverse=True)
    return ranked


def _primary_label(
    dominant_axis: AxisName,
    dominant_sign: str | None,
    premium_fairness: ForceScore,
) -> PrimaryLabel:
    if dominant_axis == "delta":
        return "Directional Bet"
    if dominant_axis == "gamma":
        # Long gamma => convexity engine; short gamma => fold into theta-related label
        return "Convexity Trade" if dominant_sign == "+" else "Theta Harvest"
    if dominant_axis == "theta":
        if dominant_sign == "+":
            return "Theta Harvest"
        # Paying theta — Decay Trap only when premium is also unfair
        if premium_fairness.magnitude < 4.0:
            return "Decay Trap"
        return "Directional Bet"
    if dominant_axis == "vega":
        return "Volatility Play"
    return "Mixed Exposure"


def _qualifier(
    primary: PrimaryLabel,
    position: EnrichedPosition,
    scores: ForceScores,
) -> str | None:
    ctx = position.context
    pos = position.position
    iv_rank = ctx.iv_rank
    dte = ctx.dte
    fairness = scores.premium_fairness.magnitude

    if primary == "Directional Bet":
        if dte < 7:
            return "Short-Dated"
        if fairness <= 3.0:
            return "Expensive Premium"
        return "Cheap Convexity"

    if primary == "Theta Harvest":
        # Single-leg only in Path A — no multi-leg qualifiers
        return "Naked-Short"

    if primary == "Volatility Play":
        if scores.vega.sign == "+":
            return "Long Vol"
        if iv_rank > 80:
            return "Event-Driven"
        return "Short Vol"

    if primary == "Convexity Trade":
        # Cheap absolute premium = lottery ticket; ATM-ish + short DTE = gamma scalp
        if pos.entry_price is not None and pos.entry_price < 2.0:
            return "Lottery Ticket"
        if dte < 14 and abs(pos.strike - ctx.underlying_price) / ctx.underlying_price < 0.02:
            return "Long Gamma Scalp"
        return "Cheap Hedge"

    if primary == "Decay Trap":
        if iv_rank > 60:
            return "IV-Inflated"
        if abs(pos.strike - ctx.underlying_price) / ctx.underlying_price > 0.10:
            return "Far OTM"
        return "Overpriced Premium"

    return None


def _readout(
    primary: PrimaryLabel,
    qualifier: str | None,
    scores: ForceScores,
    position: EnrichedPosition,
) -> str:
    pos = position.position
    base = f"{pos.qty}x {pos.ticker} {pos.expiration.isoformat()} {pos.strike}{pos.option_type[0].upper()}, {pos.side}."
    if primary == "Mixed Exposure":
        return f"{base} No single force dominates — exposure is balanced across Greeks."
    label = f"{qualifier} {primary}" if qualifier else primary
    delta_word = "bullish" if scores.delta.sign == "+" else "bearish"
    vega_word = "long vol" if scores.vega.sign == "+" else "short vol"
    theta_word = "collecting" if scores.theta.sign == "+" else "paying"
    return (
        f"{base} {label}. You're {delta_word} on direction, {vega_word} on IV, "
        f"and {theta_word} theta day to day."
    )


def classify(position: EnrichedPosition, scores: ForceScores) -> Classification:
    ranked = _rank_greek_axes(scores)
    dominant_axis, dominant = ranked[0]
    secondary_axis, _ = ranked[1]
    third = ranked[2][1]

    confidence = (dominant.magnitude - third.magnitude) / 10.0
    confidence = max(0.0, min(1.0, confidence))

    if confidence < _CONFIDENCE_THRESHOLD or dominant.magnitude < 1.0:
        return Classification(
            primary="Mixed Exposure",
            qualifier=None,
            confidence=confidence,
            dominant_axis=None,
            secondary_axis=None,
            readout=_readout("Mixed Exposure", None, scores, position),
        )

    primary = _primary_label(dominant_axis, dominant.sign, scores.premium_fairness)
    qualifier = _qualifier(primary, position, scores)
    readout = _readout(primary, qualifier, scores, position)

    return Classification(
        primary=primary,
        qualifier=qualifier,
        confidence=confidence,
        dominant_axis=dominant_axis,
        secondary_axis=secondary_axis,
        readout=readout,
    )
