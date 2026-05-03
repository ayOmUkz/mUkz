"""Domain data models for scanner pipeline outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class SectorScore:
    """Scored output from the sector (top-down) engine."""

    sector: str
    etf: str
    relative_performance: float   # sector return - benchmark return (decimal)
    volume_expansion: float       # recent / 30D avg, ratio (1.0 = flat)
    relative_strength: float      # sector / benchmark price ratio, normalized
    composite: float              # 0–100

    def __post_init__(self) -> None:
        self.composite = max(0.0, min(100.0, float(self.composite)))


@dataclass
class StockMetrics:
    """Per-stock metrics emitted by the bottom-up engine."""

    ticker: str
    sector: str | None
    last_price: float
    return_1m: float
    above_20d_ma: bool
    above_50d_ma: bool
    relative_strength: float
    avg_daily_volume: float
    market_cap: float
    realized_vol_30d: float


@dataclass
class OptionsMetrics:
    """Aggregated options stats for a single ticker (front month preferred)."""

    ticker: str
    total_volume: int
    avg_open_interest: float
    iv: float                     # mean front-month IV (decimal, e.g. 0.32 = 32%)
    iv_rank: float                # 0–100
    iv_vs_realized: float         # iv - realized_30d
    avg_bid_ask_spread_pct: float
    call_put_skew: float          # mean call IV - mean put IV
    expiry: date | None
    dte: int | None


@dataclass
class Candidate:
    """A stock that passed all filters and is ready for ranking."""

    ticker: str
    sector: str | None
    stock: StockMetrics
    options: OptionsMetrics
    sector_strength: float        # composite from SectorScore (0–100)
    momentum_score: float = 0.0
    iv_cheapness_score: float = 0.0
    liquidity_score: float = 0.0
    sector_strength_score: float = 0.0
    composite_score: float = 0.0
    notes: list[str] = field(default_factory=list)


@dataclass
class ScanResult:
    """Full result of a scan run."""

    sectors: list[SectorScore]
    candidates: list[Candidate]
    universe_size: int
    filtered_size: int
