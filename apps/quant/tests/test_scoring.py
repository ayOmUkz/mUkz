"""Smoke tests for the 5-axis force scoring. Calibration happens in Phase 3."""

from datetime import date

import pytest

from app.schemas import ChainContext, EnrichedPosition, Position
from app.scoring import compute_force_scores


def _make_position(
    *,
    side: str = "long",
    option_type: str = "call",
    qty: int = 1,
    strike: float = 480.0,
    underlying: float = 480.0,
    dte: int = 30,
    delta: float = 0.50,
    gamma: float = 0.03,
    theta: float = -0.15,
    vega: float = 0.40,
    iv: float = 0.25,
    iv_rank: float = 50.0,
    mid: float = 8.50,
    entry_price: float | None = None,
) -> EnrichedPosition:
    return EnrichedPosition(
        position=Position(
            ticker="SPY",
            expiration=date(2025, 12, 19),
            strike=strike,
            option_type=option_type,  # type: ignore[arg-type]
            side=side,  # type: ignore[arg-type]
            qty=qty,
            entry_price=entry_price,
        ),
        context=ChainContext(
            underlying_price=underlying,
            dte=dte,
            multiplier=100,
            bid=mid - 0.10,
            ask=mid + 0.10,
            mid=mid,
            iv=iv,
            iv_rank=iv_rank,
            delta=delta,
            gamma=gamma,
            theta=theta,
            vega=vega,
            open_interest=10_000,
            volume=5_000,
        ),
    )


def test_long_atm_call_is_bullish_long_vol_paying_theta() -> None:
    scores = compute_force_scores(_make_position())
    assert scores.delta.sign == "+", "long call should be bullish"
    assert scores.gamma.sign == "+", "long call should have positive gamma"
    assert scores.theta.sign == "-", "long call pays theta"
    assert scores.vega.sign == "+", "long call is long vega"
    assert 0 <= scores.premium_fairness.magnitude <= 10


def test_short_put_is_bullish_short_vol_collecting_theta() -> None:
    scores = compute_force_scores(
        _make_position(option_type="put", side="short", delta=-0.45, theta=-0.12)
    )
    # Short put: delta positive (delta of put is negative; shorting flips it)
    assert scores.delta.sign == "+"
    # Short anything: negative gamma
    assert scores.gamma.sign == "-"
    # Short put collects theta — vendor theta is negative, side flips it positive
    assert scores.theta.sign == "+"
    # Short put is short vega
    assert scores.vega.sign == "-"


def test_magnitudes_are_clamped_to_0_10() -> None:
    # Enormous position should still clamp at 10
    scores = compute_force_scores(_make_position(qty=100, gamma=1.0, vega=10.0))
    for axis in (scores.delta, scores.gamma, scores.theta, scores.vega, scores.premium_fairness):
        assert 0 <= axis.magnitude <= 10


def test_premium_fairness_unsigned() -> None:
    scores = compute_force_scores(_make_position())
    assert scores.premium_fairness.sign is None


@pytest.mark.parametrize("dte", [1, 7, 30, 90, 365])
def test_premium_fairness_finite_across_dte(dte: int) -> None:
    scores = compute_force_scores(_make_position(dte=dte))
    assert 0 <= scores.premium_fairness.magnitude <= 10
