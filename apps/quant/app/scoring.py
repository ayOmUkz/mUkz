"""Score 5-axis forces (Delta, Gamma, Theta, Vega, Premium Fairness) for V1 Path A.

Every axis emits a (magnitude 0-10, sign +/-) pair except Premium Fairness which is
unsigned (0 = severely overpriced, 5 = fair, 10 = bargain). Magnitudes are clamped
so the radar can plot them directly. Scaling constants here are first-pass
heuristics — Phase 3 manual calibration on hand-labeled positions will tune them.
"""

from __future__ import annotations

import math

from app.schemas import EnrichedPosition, ForceScore, ForceScores, Sign

# Scaling constants chosen so a "typical retail" position scores around 5
# Calibrate against real chains in Phase 3.
_DELTA_SHARES_FOR_FULL_SCORE = 50.0
_GAMMA_PRICE_NORM = 0.05  # gamma × spot, multiplied to 0-10
_THETA_PREMIUM_FRACTION_FOR_FULL_SCORE = 0.05  # $/day at 5% of position premium = score 10
_VEGA_IV_NORM = 0.5  # vega normalized against IV regime


def _clamp(x: float, lo: float = 0.0, hi: float = 10.0) -> float:
    return max(lo, min(hi, x))


def _sign(x: float) -> Sign:
    return "+" if x >= 0 else "-"


def score_delta(position: EnrichedPosition) -> ForceScore:
    side_mult = 1 if position.position.side == "long" else -1
    qty = position.position.qty
    delta = position.context.delta
    # Shares-equivalent exposure
    shares_equiv = delta * qty * position.context.multiplier * side_mult
    magnitude = _clamp(abs(shares_equiv) / _DELTA_SHARES_FOR_FULL_SCORE)
    return ForceScore(magnitude=magnitude, sign=_sign(shares_equiv))


def score_gamma(position: EnrichedPosition) -> ForceScore:
    # Gamma is intrinsically positive for long positions, negative for short
    side_mult = 1 if position.position.side == "long" else -1
    qty = position.position.qty
    gamma = position.context.gamma
    spot = position.context.underlying_price
    # Normalize gamma * spot (gives "delta change per 1% move in dollars")
    raw = abs(gamma * qty * position.context.multiplier * spot) * _GAMMA_PRICE_NORM
    magnitude = _clamp(raw)
    return ForceScore(magnitude=magnitude, sign=_sign(side_mult))


def score_theta(position: EnrichedPosition) -> ForceScore:
    side_mult = 1 if position.position.side == "long" else -1
    qty = position.position.qty
    # Vendor theta is per-day, typically negative for the long side of a contract.
    # Position theta is signed: positive = collecting rent, negative = paying.
    position_theta = position.context.theta * qty * position.context.multiplier * side_mult
    # Normalize against position gross premium
    gross_premium = position.context.mid * qty * position.context.multiplier
    if gross_premium <= 0:
        magnitude = 0.0
    else:
        magnitude = _clamp(
            abs(position_theta) / (gross_premium * _THETA_PREMIUM_FRACTION_FOR_FULL_SCORE)
        )
    return ForceScore(magnitude=magnitude, sign=_sign(position_theta))


def score_vega(position: EnrichedPosition) -> ForceScore:
    side_mult = 1 if position.position.side == "long" else -1
    qty = position.position.qty
    vega = position.context.vega
    iv = position.context.iv
    position_vega = vega * qty * position.context.multiplier * side_mult
    # Normalize against IV regime — a 10-vega in a 15% IV name is "louder" than in 60%
    iv_pct = max(iv * 100.0, 1.0)  # avoid divide-by-zero
    magnitude = _clamp(abs(position_vega) / (iv_pct * _VEGA_IV_NORM))
    return ForceScore(magnitude=magnitude, sign=_sign(position_vega))


def score_premium_fairness(position: EnrichedPosition) -> ForceScore:
    """Score how fairly priced the option is relative to its expected move and IV regime.

    Score interpretation:
      0  — severely overpriced (premium far above expected move, IV rank high)
      5  — fair value
      10 — bargain (premium well below expected move, IV rank low)

    V1 heuristic; calibrate in Phase 3.
    """
    ctx = position.context
    if ctx.mid <= 0 or ctx.underlying_price <= 0:
        return ForceScore(magnitude=5.0, sign=None)

    # 1σ expected move from IV and time
    expected_move = ctx.underlying_price * ctx.iv * math.sqrt(max(ctx.dte, 1) / 365.0)
    if expected_move <= 0:
        return ForceScore(magnitude=5.0, sign=None)

    # Premium as fraction of expected move (ATM call ~ 0.4 fair)
    premium_em_ratio = ctx.mid / expected_move

    # IV rank penalty: high IV rank means options are pricey vs their own history
    iv_rank_penalty = max(0.0, (ctx.iv_rank - 50.0) / 50.0)  # 0 below 50, → 1 at 100

    # Base score: lower premium_em_ratio = cheaper = higher score
    # Use 0.4 as the reference ATM ratio
    base = 5.0 + (0.4 - premium_em_ratio) * 12.0

    # Apply IV rank penalty (subtract up to 3 points if IV rank is 100)
    score = base - iv_rank_penalty * 3.0

    return ForceScore(magnitude=_clamp(score), sign=None)


def compute_force_scores(position: EnrichedPosition) -> ForceScores:
    return ForceScores(
        delta=score_delta(position),
        gamma=score_gamma(position),
        theta=score_theta(position),
        vega=score_vega(position),
        premium_fairness=score_premium_fairness(position),
    )
