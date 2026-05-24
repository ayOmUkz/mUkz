"""Options mispricing engine.

For each candidate ticker we pick a target front-month expiration in the
configured DTE band and aggregate ATM-bracket strikes to compute:

    * total options volume / day
    * average open interest per strike
    * mean implied volatility (ATM bracket)
    * IV Rank vs trailing realized-volatility window (proxy for IV history)
    * IV vs realized-vol spread (mispricing read)
    * average bid-ask spread % of mid (liquidity quality)
    * call/put skew (mean call IV - mean put IV)

NOTE on IV history: yfinance does not expose historical IV. We use the
trailing realized-volatility *distribution* as a transparent proxy when
no IV history feed is configured. Wire a paid feed into the
:class:`DataSource` if you need true IV Rank.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Iterable

import numpy as np
import pandas as pd

from .config import OptionsEngineConfig
from .data_sources import DataSource, TickerSnapshot
from .indicators import iv_rank, realized_volatility
from .models import OptionsMetrics

logger = logging.getLogger(__name__)


class OptionsEngine:
    def __init__(
        self,
        data_source: DataSource,
        config: OptionsEngineConfig,
    ) -> None:
        self._data = data_source
        self._config = config

    def evaluate(self, snapshot: TickerSnapshot) -> OptionsMetrics | None:
        expiration = self._select_expiration(snapshot.options_expirations)
        if expiration is None:
            logger.info("%s: no expiration in [%d,%d] DTE",
                        snapshot.ticker,
                        self._config.expirations.min_dte,
                        self._config.expirations.max_dte)
            return None

        calls, puts = self._data.get_options_chain(snapshot.ticker, expiration)
        if calls.empty and puts.empty:
            return None

        underlying = self._underlying_price(snapshot)
        if underlying is None:
            return None

        atm_calls = _atm_bracket(calls, underlying)
        atm_puts = _atm_bracket(puts, underlying)
        combined = pd.concat([atm_calls, atm_puts], ignore_index=True)
        if combined.empty:
            return None

        total_volume = int(_safe_sum(combined.get("volume")))
        avg_oi = float(_safe_mean(combined.get("openInterest")))
        atm_iv = float(_safe_mean(combined.get("impliedVolatility")))
        spread_pct = _avg_bid_ask_spread_pct(combined)
        skew = float(_safe_mean(atm_calls.get("impliedVolatility"))) - float(
            _safe_mean(atm_puts.get("impliedVolatility"))
        )

        # IV Rank — use realized-vol distribution as a transparent proxy if we
        # don't have a true IV history feed.
        close = _close_series(snapshot.history)
        rv_series = _trailing_realized_vol_series(
            close, window=30, lookback=self._config.iv_rank.lookback_days
        )
        rank = iv_rank(atm_iv, rv_series) if not np.isnan(atm_iv) else float("nan")
        rv_now = realized_volatility(close, window=30)
        iv_vs_rv = (atm_iv - rv_now) if pd.notna(atm_iv) and pd.notna(rv_now) else float("nan")

        expiry_date = _parse_date(expiration)
        dte = (expiry_date - date.today()).days if expiry_date else None

        return OptionsMetrics(
            ticker=snapshot.ticker,
            total_volume=total_volume,
            avg_open_interest=avg_oi,
            iv=atm_iv if pd.notna(atm_iv) else float("nan"),
            iv_rank=float(rank) if pd.notna(rank) else float("nan"),
            iv_vs_realized=float(iv_vs_rv) if pd.notna(iv_vs_rv) else float("nan"),
            avg_bid_ask_spread_pct=spread_pct,
            call_put_skew=float(skew) if pd.notna(skew) else float("nan"),
            expiry=expiry_date,
            dte=dte,
        )

    # ------------------------------------------------------------------ filters
    def passes_filters(self, m: OptionsMetrics) -> tuple[bool, str | None]:
        cfg = self._config
        if pd.isna(m.iv_rank):
            return False, "IV rank unavailable"
        if m.iv_rank > cfg.iv_rank.max:
            return False, f"IV Rank {m.iv_rank:.1f} > {cfg.iv_rank.max:.1f}"
        if m.total_volume < cfg.liquidity.min_total_volume:
            return False, (
                f"options volume {m.total_volume:,} < "
                f"{cfg.liquidity.min_total_volume:,}"
            )
        if m.avg_open_interest < cfg.liquidity.min_open_interest_per_strike:
            return False, (
                f"avg OI {m.avg_open_interest:.0f} < "
                f"{cfg.liquidity.min_open_interest_per_strike}"
            )
        if (
            pd.notna(m.avg_bid_ask_spread_pct)
            and m.avg_bid_ask_spread_pct > cfg.liquidity.max_bid_ask_spread_pct
        ):
            return False, (
                f"bid-ask spread {m.avg_bid_ask_spread_pct:.2%} > "
                f"{cfg.liquidity.max_bid_ask_spread_pct:.2%}"
            )
        return True, None

    # ------------------------------------------------------------------ helpers
    def _select_expiration(self, expirations: Iterable[str]) -> str | None:
        today = date.today()
        best: tuple[int, str] | None = None
        for raw in expirations:
            d = _parse_date(raw)
            if d is None:
                continue
            dte = (d - today).days
            if self._config.expirations.min_dte <= dte <= self._config.expirations.max_dte:
                # prefer the earliest expiry inside the band (front month bias)
                if best is None or dte < best[0]:
                    best = (dte, raw)
        return best[1] if best else None

    def _underlying_price(self, snapshot: TickerSnapshot) -> float | None:
        close = _close_series(snapshot.history)
        if close.empty:
            return None
        return float(close.iloc[-1])


# ---------------------------------------------------------------------- helpers
def _close_series(df: pd.DataFrame) -> pd.Series:
    if df is None or df.empty:
        return pd.Series(dtype="float64")
    if "Close" in df.columns:
        return df["Close"].astype(float)
    if "Adj Close" in df.columns:
        return df["Adj Close"].astype(float)
    return df.iloc[:, 0].astype(float)


def _atm_bracket(chain: pd.DataFrame, underlying: float, n: int = 5) -> pd.DataFrame:
    """Return the ``n`` strikes nearest to underlying."""
    if chain is None or chain.empty or "strike" not in chain.columns:
        return pd.DataFrame()
    df = chain.copy()
    df["__dist__"] = (df["strike"].astype(float) - float(underlying)).abs()
    df.sort_values("__dist__", inplace=True)
    return df.head(n).drop(columns="__dist__")


def _avg_bid_ask_spread_pct(chain: pd.DataFrame) -> float:
    if chain is None or chain.empty:
        return float("nan")
    bid = chain.get("bid")
    ask = chain.get("ask")
    if bid is None or ask is None:
        return float("nan")
    bid = pd.to_numeric(bid, errors="coerce")
    ask = pd.to_numeric(ask, errors="coerce")
    mid = (bid + ask) / 2.0
    spread = (ask - bid)
    pct = (spread / mid).replace([np.inf, -np.inf], np.nan)
    pct = pct[(pct > 0) & pct.notna()]
    return float(pct.mean()) if not pct.empty else float("nan")


def _safe_sum(series: pd.Series | None) -> float:
    if series is None:
        return 0.0
    return float(pd.to_numeric(series, errors="coerce").fillna(0).sum())


def _safe_mean(series: pd.Series | None) -> float:
    if series is None:
        return float("nan")
    cleaned = pd.to_numeric(series, errors="coerce").dropna()
    return float(cleaned.mean()) if not cleaned.empty else float("nan")


def _parse_date(raw: str) -> date | None:
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _trailing_realized_vol_series(
    close: pd.Series, window: int, lookback: int
) -> pd.Series:
    """Rolling annualized realized vol used as an IV-history proxy."""
    if close is None or close.empty:
        return pd.Series(dtype="float64")
    log_returns = np.log(close / close.shift(1)).dropna()
    if log_returns.empty:
        return pd.Series(dtype="float64")
    rolling = log_returns.rolling(window=window, min_periods=window).std(ddof=1) * np.sqrt(252)
    return rolling.tail(lookback).dropna()
