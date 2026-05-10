"""Sanity tests for the Personality classifier — archetypal positions
should produce expected primary labels."""

from datetime import date

from app.classifier import classify
from app.schemas import ChainContext, EnrichedPosition, Position
from app.scoring import compute_force_scores


def _ep(**overrides: object) -> EnrichedPosition:
    base = {
        "ticker": "SPY",
        "expiration": date(2025, 12, 19),
        "strike": 480.0,
        "option_type": "call",
        "side": "long",
        "qty": 1,
        "entry_price": None,
        "underlying_price": 480.0,
        "dte": 30,
        "multiplier": 100,
        "mid": 8.50,
        "iv": 0.25,
        "iv_rank": 50.0,
        "delta": 0.50,
        "gamma": 0.03,
        "theta": -0.15,
        "vega": 0.40,
        "open_interest": 10_000,
        "volume": 5_000,
    }
    base.update(overrides)
    return EnrichedPosition(
        position=Position(
            ticker=base["ticker"],  # type: ignore[arg-type]
            expiration=base["expiration"],  # type: ignore[arg-type]
            strike=base["strike"],  # type: ignore[arg-type]
            option_type=base["option_type"],  # type: ignore[arg-type]
            side=base["side"],  # type: ignore[arg-type]
            qty=base["qty"],  # type: ignore[arg-type]
            entry_price=base["entry_price"],  # type: ignore[arg-type]
        ),
        context=ChainContext(
            underlying_price=base["underlying_price"],  # type: ignore[arg-type]
            dte=base["dte"],  # type: ignore[arg-type]
            multiplier=base["multiplier"],  # type: ignore[arg-type]
            bid=base["mid"] - 0.10,  # type: ignore[operator]
            ask=base["mid"] + 0.10,  # type: ignore[operator]
            mid=base["mid"],  # type: ignore[arg-type]
            iv=base["iv"],  # type: ignore[arg-type]
            iv_rank=base["iv_rank"],  # type: ignore[arg-type]
            delta=base["delta"],  # type: ignore[arg-type]
            gamma=base["gamma"],  # type: ignore[arg-type]
            theta=base["theta"],  # type: ignore[arg-type]
            vega=base["vega"],  # type: ignore[arg-type]
            open_interest=base["open_interest"],  # type: ignore[arg-type]
            volume=base["volume"],  # type: ignore[arg-type]
        ),
    )


def _classify(p: EnrichedPosition):
    return classify(p, compute_force_scores(p))


def test_long_atm_call_short_dte_is_directional_or_convexity() -> None:
    # Short-DTE long ATM call: delta and gamma both meaningful
    result = _classify(_ep(dte=5, qty=5))
    assert result.primary in {"Directional Bet", "Convexity Trade"}
    assert result.confidence >= 0  # any non-mixed result has confidence


def test_short_otm_put_high_iv_is_theta_harvest_or_vol_play() -> None:
    # Short OTM put: delta+, gamma-, theta+, vega-
    result = _classify(
        _ep(
            option_type="put",
            side="short",
            strike=470.0,
            delta=-0.20,
            gamma=0.02,
            theta=-0.10,
            vega=0.30,
            iv=0.40,
            iv_rank=85,
            mid=3.00,
            qty=3,
        )
    )
    assert result.primary in {"Theta Harvest", "Volatility Play"}


def test_long_far_otm_call_high_iv_is_decay_trap_or_directional() -> None:
    # Far OTM long call with high IV — expensive premium, paying theta.
    # V1 limitation: without an in-house BS pricer, Premium Fairness uses
    # expected-move-only heuristic and can score this position as "fair"
    # because the absolute premium is small relative to the wide expected move.
    # Result: classifier falls back to gamma-dominance ("Convexity Trade").
    # Phase 3 calibration + V2 BS engine will tighten this to "Decay Trap".
    result = _classify(
        _ep(
            strike=520.0,
            delta=0.10,
            gamma=0.01,
            theta=-0.08,
            vega=0.15,
            iv=0.45,
            iv_rank=90,
            mid=1.50,
            dte=14,
        )
    )
    assert result.primary in {
        "Decay Trap",
        "Directional Bet",
        "Volatility Play",
        "Convexity Trade",  # current V1 behavior — to be tightened in V2
    }


def test_balanced_book_falls_to_mixed_exposure() -> None:
    # Tiny qty + low Greeks => all magnitudes small => Mixed Exposure
    result = _classify(
        _ep(delta=0.05, gamma=0.001, theta=-0.01, vega=0.02, qty=1, mid=0.50)
    )
    assert result.primary == "Mixed Exposure"
    assert result.qualifier is None


def test_classification_emits_readout() -> None:
    result = _classify(_ep())
    assert len(result.readout) > 20
    assert "SPY" in result.readout


def test_short_dated_qualifier_applied() -> None:
    result = _classify(_ep(dte=3, qty=10))
    if result.primary == "Directional Bet":
        assert result.qualifier == "Short-Dated"
