"""Ranking engine.

Combines the per-leg sub-scores into a single composite score in [0, 100]:

    composite = w_m * momentum
              + w_iv * iv_cheapness
              + w_l * options_liquidity
              + w_s * sector_strength

Each sub-score is itself a 0–100 number so the composite always lives in
the same range. Sub-scores are documented in the module-level helpers
below — they are intentionally simple and readable so a quant can audit
or override them without touching engine logic.
"""

from __future__ import annotations

import math

import pandas as pd

from .config import RankingConfig
from .models import Candidate


class RankingEngine:
    def __init__(self, config: RankingConfig) -> None:
        self._config = config

    def score(self, candidates: list[Candidate]) -> list[Candidate]:
        for c in candidates:
            c.momentum_score = momentum_score(c)
            c.iv_cheapness_score = iv_cheapness_score(c)
            c.liquidity_score = liquidity_score(c)
            c.sector_strength_score = sector_strength_score(c)
            c.composite_score = self._composite(c)
            c.notes = build_notes(c)
        candidates.sort(key=lambda x: x.composite_score, reverse=True)
        return candidates[: self._config.top_n_results]

    def _composite(self, c: Candidate) -> float:
        w = self._config.weights
        total_weight = w.momentum + w.iv_cheapness + w.liquidity + w.sector_strength
        if total_weight <= 0:
            return 0.0
        score = (
            w.momentum * c.momentum_score
            + w.iv_cheapness * c.iv_cheapness_score
            + w.liquidity * c.liquidity_score
            + w.sector_strength * c.sector_strength_score
        ) / total_weight
        return round(max(0.0, min(100.0, score)), 2)


# ----------------------------------------------------------------- sub-scores
def momentum_score(c: Candidate) -> float:
    """Higher is better. Caps generous single-stock 1M moves at +30%.

    Components:
        * 1M return scaled into [0, 60] (cap at +30% return)
        * Relative strength scaled into [0, 25] (cap at RS = 1.30)
        * MA confirmation: +7.5 each for above 20D / 50D
    """
    ret = _nan_to(c.stock.return_1m, 0.0)
    rs = _nan_to(c.stock.relative_strength, 1.0)

    ret_score = max(0.0, min(60.0, (ret / 0.30) * 60.0))
    rs_excess = max(0.0, rs - 1.0)
    rs_score = max(0.0, min(25.0, (rs_excess / 0.30) * 25.0))
    ma_score = (7.5 if c.stock.above_20d_ma else 0.0) + (7.5 if c.stock.above_50d_ma else 0.0)
    return round(min(100.0, ret_score + rs_score + ma_score), 2)


def iv_cheapness_score(c: Candidate) -> float:
    """Lower IV Rank = higher score. IV Rank 0 -> 100, IV Rank 30 -> 0.

    Adds a small bonus when current IV is below trailing realized vol
    (i.e. options are pricing in less movement than the stock has
    actually delivered).
    """
    rank = _nan_to(c.options.iv_rank, 50.0)
    base = max(0.0, min(100.0, 100.0 - (rank / 30.0) * 100.0))
    iv_vs_rv = c.options.iv_vs_realized
    if not math.isnan(iv_vs_rv) and iv_vs_rv < 0:
        base = min(100.0, base + 5.0)
    return round(base, 2)


def liquidity_score(c: Candidate) -> float:
    """Combines options volume, OI, and bid-ask quality."""
    vol = _nan_to(c.options.total_volume, 0.0)
    oi = _nan_to(c.options.avg_open_interest, 0.0)
    spread = _nan_to(c.options.avg_bid_ask_spread_pct, 0.20)

    vol_score = max(0.0, min(40.0, math.log10(max(1.0, vol)) / math.log10(20_000) * 40.0))
    oi_score = max(0.0, min(35.0, math.log10(max(1.0, oi)) / math.log10(10_000) * 35.0))
    spread_score = max(0.0, min(25.0, (1.0 - min(spread, 0.20) / 0.20) * 25.0))
    return round(vol_score + oi_score + spread_score, 2)


def sector_strength_score(c: Candidate) -> float:
    """Pass-through of the sector composite (already 0–100)."""
    return round(max(0.0, min(100.0, _nan_to(c.sector_strength, 0.0))), 2)


def build_notes(c: Candidate) -> list[str]:
    notes: list[str] = []
    if c.options.iv_vs_realized < 0:
        notes.append("IV < realized vol (options cheap vs delivered move)")
    if c.options.call_put_skew > 0.02:
        notes.append("call IV > put IV (bullish skew)")
    if c.options.call_put_skew < -0.02:
        notes.append("put IV > call IV (defensive skew)")
    if c.stock.above_20d_ma and c.stock.above_50d_ma:
        notes.append("trend confirmed (above 20D & 50D MA)")
    return notes


def _nan_to(value: float, fallback: float) -> float:
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return fallback
    if pd.isna(value):
        return fallback
    return float(value)
