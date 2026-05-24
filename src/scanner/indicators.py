"""Pure technical / volatility indicators.

All functions are deterministic and side-effect free so they can be unit
tested without network access.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


def period_return(prices: pd.Series, periods: int) -> float:
    """Return the simple return over the trailing ``periods`` bars."""
    if prices is None or len(prices) <= periods:
        return float("nan")
    end = float(prices.iloc[-1])
    start = float(prices.iloc[-periods - 1])
    if start == 0 or np.isnan(start) or np.isnan(end):
        return float("nan")
    return end / start - 1.0


def sma(prices: pd.Series, window: int) -> pd.Series:
    return prices.rolling(window=window, min_periods=window).mean()


def above_ma(prices: pd.Series, window: int) -> bool:
    series = sma(prices, window)
    if series.dropna().empty:
        return False
    return float(prices.iloc[-1]) > float(series.iloc[-1])


def relative_strength(prices: pd.Series, benchmark: pd.Series, periods: int) -> float:
    """Ratio of asset return to benchmark return over ``periods`` bars.

    Returns 1.0 when both moved identically. ``> 1`` means the asset
    outperformed the benchmark; ``< 1`` means underperformance.
    """
    a = period_return(prices, periods)
    b = period_return(benchmark, periods)
    if np.isnan(a) or np.isnan(b):
        return float("nan")
    # Translate returns to growth factors so RS is well-defined when one side
    # is negative. RS = (1 + r_asset) / (1 + r_bench).
    denom = 1.0 + b
    if denom == 0:
        return float("nan")
    return (1.0 + a) / denom


def realized_volatility(prices: pd.Series, window: int = 30) -> float:
    """Annualized realized volatility over ``window`` trailing bars."""
    if prices is None or len(prices) < window + 1:
        return float("nan")
    log_returns = np.log(prices / prices.shift(1)).dropna()
    if len(log_returns) < window:
        return float("nan")
    sample = log_returns.iloc[-window:]
    return float(sample.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR))


def volume_expansion_ratio(volumes: pd.Series, recent: int = 5, baseline: int = 30) -> float:
    """Ratio of mean recent volume to mean baseline volume."""
    if volumes is None or len(volumes) < baseline:
        return float("nan")
    recent_avg = float(volumes.iloc[-recent:].mean())
    baseline_avg = float(volumes.iloc[-baseline:].mean())
    if baseline_avg == 0 or np.isnan(baseline_avg):
        return float("nan")
    return recent_avg / baseline_avg


def iv_rank(current_iv: float, iv_history: pd.Series) -> float:
    """IV Rank in [0, 100].

    ``IV Rank = 100 * (current - min) / (max - min)`` over the history window.
    Returns NaN if the history range is degenerate.
    """
    if current_iv is None or np.isnan(current_iv):
        return float("nan")
    series = pd.Series(iv_history).dropna()
    if series.empty:
        return float("nan")
    iv_min = float(series.min())
    iv_max = float(series.max())
    if iv_max <= iv_min:
        return float("nan")
    rank = 100.0 * (float(current_iv) - iv_min) / (iv_max - iv_min)
    return max(0.0, min(100.0, rank))


def normalize_min_max(values: pd.Series) -> pd.Series:
    """Min-max normalize to [0, 1]. Constant series returns 0.5 everywhere."""
    s = pd.Series(values, dtype="float64")
    if s.dropna().empty:
        return s
    lo = s.min(skipna=True)
    hi = s.max(skipna=True)
    if hi == lo:
        return pd.Series(0.5, index=s.index)
    return (s - lo) / (hi - lo)
