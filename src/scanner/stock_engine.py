"""Bottom-up stock screener.

Applies the momentum / market-cap / liquidity filters to a candidate
universe and returns :class:`StockMetrics` for stocks that pass.
"""

from __future__ import annotations

import logging

import pandas as pd

from .config import StockEngineConfig, UniverseConfig
from .data_sources import DataSource, TickerSnapshot
from .indicators import (
    above_ma,
    period_return,
    realized_volatility,
    relative_strength,
)
from .models import StockMetrics

logger = logging.getLogger(__name__)


class StockEngine:
    def __init__(
        self,
        data_source: DataSource,
        universe: UniverseConfig,
        config: StockEngineConfig,
        history_days: int,
        lookback_days: int = 21,
    ) -> None:
        self._data = data_source
        self._universe = universe
        self._config = config
        self._history_days = history_days
        self._lookback_days = lookback_days

    def screen(
        self,
        tickers: list[str],
        allowed_sectors: set[str] | None = None,
    ) -> tuple[list[StockMetrics], dict[str, str]]:
        """Run all filters.

        Returns a tuple ``(passing, rejection_reasons)`` so callers can
        explain *why* a name fell out — useful for debugging the funnel.
        """
        benchmark_history = self._data.get_history(
            self._universe.benchmark, self._history_days
        )
        bench_close = _close_series(benchmark_history)

        passing: list[StockMetrics] = []
        rejected: dict[str, str] = {}

        for ticker in tickers:
            try:
                snapshot = self._data.get_snapshot(ticker, self._history_days)
            except Exception as exc:  # pragma: no cover - network
                rejected[ticker] = f"snapshot error: {exc}"
                continue

            metrics = self._compute_metrics(snapshot, bench_close)
            if metrics is None:
                rejected[ticker] = "insufficient history"
                continue

            reason = self._reject_reason(metrics, snapshot, allowed_sectors)
            if reason:
                rejected[ticker] = reason
                continue
            passing.append(metrics)

        return passing, rejected

    # ------------------------------------------------------------------ helpers
    def _compute_metrics(
        self, snapshot: TickerSnapshot, bench_close: pd.Series
    ) -> StockMetrics | None:
        close = _close_series(snapshot.history)
        volume = _volume_series(snapshot.history)
        if close.dropna().empty or len(close) < 60:
            return None

        ret_1m = period_return(close, self._lookback_days)
        rs = relative_strength(close, bench_close, self._lookback_days) if not bench_close.empty else float("nan")
        avg_vol = float(volume.tail(30).mean()) if not volume.empty else 0.0
        last_price = float(close.iloc[-1])
        rv = realized_volatility(close, window=30)
        market_cap = snapshot.market_cap or _approx_market_cap(snapshot, last_price)

        return StockMetrics(
            ticker=snapshot.ticker,
            sector=snapshot.sector,
            last_price=last_price,
            return_1m=float(ret_1m) if pd.notna(ret_1m) else float("nan"),
            above_20d_ma=above_ma(close, 20),
            above_50d_ma=above_ma(close, 50),
            relative_strength=float(rs) if pd.notna(rs) else float("nan"),
            avg_daily_volume=avg_vol,
            market_cap=float(market_cap) if market_cap is not None else float("nan"),
            realized_vol_30d=float(rv) if pd.notna(rv) else float("nan"),
        )

    def _reject_reason(
        self,
        m: StockMetrics,
        snapshot: TickerSnapshot,
        allowed_sectors: set[str] | None,
    ) -> str | None:
        cfg = self._config
        if allowed_sectors and snapshot.sector and snapshot.sector not in allowed_sectors:
            return f"sector {snapshot.sector!r} not in top sectors"

        # Momentum
        if pd.isna(m.return_1m) or m.return_1m < cfg.momentum.min_1m_return:
            return f"1M return {m.return_1m:.2%} < {cfg.momentum.min_1m_return:.2%}"
        if cfg.momentum.require_above_20d_ma and not m.above_20d_ma:
            return "price below 20D MA"
        if cfg.momentum.require_above_50d_ma and not m.above_50d_ma:
            return "price below 50D MA"
        if pd.notna(m.relative_strength) and m.relative_strength < cfg.momentum.min_relative_strength:
            return f"RS {m.relative_strength:.2f} < {cfg.momentum.min_relative_strength:.2f}"

        # Market cap
        mc_min = cfg.market_cap.min_usd
        mc_max = cfg.market_cap.max_usd
        if pd.isna(m.market_cap):
            return "market cap unavailable"
        if not (mc_min <= m.market_cap <= mc_max):
            return f"market cap ${m.market_cap/1e6:,.0f}M out of [{mc_min/1e6:,.0f}M, {mc_max/1e6:,.0f}M]"

        # Liquidity
        if m.avg_daily_volume < cfg.liquidity.min_avg_daily_volume:
            return (
                f"avg volume {m.avg_daily_volume:,.0f} < "
                f"{cfg.liquidity.min_avg_daily_volume:,.0f}"
            )
        return None


def _close_series(df: pd.DataFrame) -> pd.Series:
    if df is None or df.empty:
        return pd.Series(dtype="float64")
    if "Close" in df.columns:
        return df["Close"].astype(float)
    if "Adj Close" in df.columns:
        return df["Adj Close"].astype(float)
    return df.iloc[:, 0].astype(float)


def _volume_series(df: pd.DataFrame) -> pd.Series:
    if df is None or df.empty or "Volume" not in df.columns:
        return pd.Series(dtype="float64")
    return df["Volume"].astype(float)


def _approx_market_cap(snapshot: TickerSnapshot, last_price: float) -> float | None:
    """Fall back to ``shares_outstanding * price`` when marketCap is missing."""
    info = snapshot.info or {}
    shares = info.get("sharesOutstanding") or info.get("impliedSharesOutstanding")
    if shares is None:
        return None
    try:
        return float(shares) * float(last_price)
    except (TypeError, ValueError):
        return None
