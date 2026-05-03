from datetime import date

from scanner.config import RankingConfig, RankingWeights
from scanner.models import Candidate, OptionsMetrics, StockMetrics
from scanner.ranking_engine import (
    RankingEngine,
    iv_cheapness_score,
    liquidity_score,
    momentum_score,
    sector_strength_score,
)


def _make_candidate(
    *,
    ret_1m: float = 0.10,
    rs: float = 1.10,
    above_20: bool = True,
    above_50: bool = True,
    iv_rank: float = 15.0,
    iv_vs_rv: float = -0.02,
    opt_volume: int = 5_000,
    opt_oi: float = 1_500,
    spread: float = 0.05,
    sector_strength: float = 80.0,
) -> Candidate:
    stock = StockMetrics(
        ticker="ABC",
        sector="Technology",
        last_price=100.0,
        return_1m=ret_1m,
        above_20d_ma=above_20,
        above_50d_ma=above_50,
        relative_strength=rs,
        avg_daily_volume=2_000_000,
        market_cap=1.5e9,
        realized_vol_30d=0.30,
    )
    opts = OptionsMetrics(
        ticker="ABC",
        total_volume=opt_volume,
        avg_open_interest=opt_oi,
        iv=0.25,
        iv_rank=iv_rank,
        iv_vs_realized=iv_vs_rv,
        avg_bid_ask_spread_pct=spread,
        call_put_skew=0.01,
        expiry=date.today(),
        dte=30,
    )
    return Candidate(
        ticker="ABC",
        sector="Technology",
        stock=stock,
        options=opts,
        sector_strength=sector_strength,
    )


def test_momentum_score_rewards_strong_returns():
    weak = _make_candidate(ret_1m=0.06, rs=1.02)
    strong = _make_candidate(ret_1m=0.25, rs=1.20)
    assert momentum_score(strong) > momentum_score(weak)


def test_momentum_score_penalizes_below_ma():
    above = _make_candidate(above_20=True, above_50=True)
    below = _make_candidate(above_20=False, above_50=False)
    assert momentum_score(above) > momentum_score(below)


def test_iv_cheapness_inversely_related_to_iv_rank():
    cheap = _make_candidate(iv_rank=5.0)
    rich = _make_candidate(iv_rank=29.0)
    assert iv_cheapness_score(cheap) > iv_cheapness_score(rich)


def test_iv_cheapness_bonus_when_iv_below_realized():
    base = _make_candidate(iv_rank=10.0, iv_vs_rv=0.05)
    discounted = _make_candidate(iv_rank=10.0, iv_vs_rv=-0.05)
    assert iv_cheapness_score(discounted) > iv_cheapness_score(base)


def test_liquidity_score_increases_with_volume_and_oi():
    thin = _make_candidate(opt_volume=1_500, opt_oi=600, spread=0.10)
    deep = _make_candidate(opt_volume=15_000, opt_oi=8_000, spread=0.02)
    assert liquidity_score(deep) > liquidity_score(thin)


def test_sector_strength_passthrough():
    c = _make_candidate(sector_strength=42.0)
    assert sector_strength_score(c) == 42.0


def test_composite_in_range_and_sorted():
    candidates = [
        _make_candidate(ret_1m=0.05, rs=1.0, iv_rank=29.0, opt_volume=1_500, opt_oi=600, sector_strength=10.0),
        _make_candidate(ret_1m=0.20, rs=1.20, iv_rank=5.0, opt_volume=10_000, opt_oi=5_000, sector_strength=90.0),
    ]
    engine = RankingEngine(RankingConfig(weights=RankingWeights()))
    ranked = engine.score(candidates)
    assert ranked[0].composite_score >= ranked[1].composite_score
    for c in ranked:
        assert 0.0 <= c.composite_score <= 100.0


def test_top_n_results_truncates():
    many = [_make_candidate(ret_1m=0.10 + i * 0.01) for i in range(10)]
    cfg = RankingConfig(weights=RankingWeights(), top_n_results=3)
    engine = RankingEngine(cfg)
    ranked = engine.score(many)
    assert len(ranked) == 3
