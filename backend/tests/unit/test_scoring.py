"""Golden tests for the scoring stack — any weight change must update these
deliberately (plan §17, "golden-file tests")."""

import pytest

from app.analytics.scoring import (
    data_quality_score,
    dpss,
    print_significance,
    trade_relevance,
)
from app.config import DpssWeights, PrintSignificanceWeights

WEIGHTS = PrintSignificanceWeights()


def test_print_significance_golden_negotiated_block():
    row = {
        "size_percentile": 99.0,
        "pct_adv30": 0.01,
        "character": "possible_negotiated_block",
        "timing_bucket": "late_report",
    }
    # 0.4*99 + 0.25*100 + 0.2*100 + 0.15*85 = 97.35
    assert print_significance(row, WEIGHTS) == 97.35


def test_print_significance_cold_start_falls_back_to_class():
    row = {
        "size_percentile": None,
        "size_class": "elevated",
        "pct_adv30": None,
        "character": "routine_off_exchange",
        "timing_bucket": "lunch",
    }
    # 0.4*90 + 0.25*0 + 0.2*60 + 0.15*50 = 55.5
    assert print_significance(row, WEIGHTS) == 55.5


def test_data_quality_perfect_and_degraded():
    clean = {"quality_flags": [], "location_confidence": "ok"}
    perfect, _ = data_quality_score([clean, clean], has_vwap=True, has_atr=True)
    assert perfect == 100.0

    degraded_row = {"quality_flags": ["crossed_quote"], "location_confidence": "none"}
    score, components = data_quality_score(
        [clean, degraded_row], has_vwap=True, has_atr=False
    )
    # clean_share 0.5 -> 20; location (1+0)/2 -> 15; vwap 15; atr 0.
    assert score == 50.0
    assert components["atr"] == 0.0


def test_data_quality_zero_without_prints():
    assert data_quality_score([], has_vwap=True, has_atr=True)[0] == 0.0


def test_trade_relevance_close_and_fresh_is_full_marks():
    score, components = trade_relevance(
        current_close=100.0, zone_wavg=100.0, atr=2.0,
        sessions_since_last=0, half_life_sessions=5,
    )
    assert score == 100.0
    assert components == {"proximity": 60.0, "freshness": 40.0}


def test_trade_relevance_decays_with_distance_and_age():
    score, components = trade_relevance(
        current_close=106.0, zone_wavg=100.0, atr=2.0,  # 3 ATRs away
        sessions_since_last=5, half_life_sessions=5,    # one half-life old
    )
    # proximity (5-3)/4 = 50 -> 30; freshness 50 -> 20.
    assert components == {"proximity": 30.0, "freshness": 20.0}
    assert score == 50.0


def test_trade_relevance_zero_proximity_without_price():
    _, components = trade_relevance(
        current_close=None, zone_wavg=100.0, atr=2.0,
        sessions_since_last=0, half_life_sessions=5,
    )
    assert components["proximity"] == 0.0


def test_dpss_golden_and_quality_gate():
    total = dpss(
        print_score=80.0, zone_score=60.0, direction_score=65.0,
        relevance_score=70.0, quality_score=90.0, weights=DpssWeights(),
    )
    # (0.25*80 + 0.30*60 + 0.25*65 + 0.20*70) * 0.9 = 68.25 * 0.9
    assert total == pytest.approx(61.43, abs=0.01)
    # Zero quality gates everything to zero, no matter how good the rest is.
    assert dpss(
        print_score=100.0, zone_score=100.0, direction_score=85.0,
        relevance_score=100.0, quality_score=0.0, weights=DpssWeights(),
    ) == 0.0
