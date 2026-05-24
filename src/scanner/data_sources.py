"""Data source abstraction.

The default backend wraps `yfinance`, but the Protocol below lets callers
inject a fake/in-memory data source for tests or for swapping in a paid
data vendor (Polygon, Tradier, IBKR, etc.) without touching engine code.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Protocol

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class TickerSnapshot:
    """Bundle of everything an engine needs about a single ticker."""

    ticker: str
    history: pd.DataFrame                  # OHLCV indexed by date
    info: dict                              # raw provider metadata
    options_expirations: list[str] = field(default_factory=list)
    sector: str | None = None
    market_cap: float | None = None


class DataSource(Protocol):
    def get_history(self, ticker: str, days: int) -> pd.DataFrame: ...
    def get_snapshot(self, ticker: str, history_days: int) -> TickerSnapshot: ...
    def get_options_chain(
        self, ticker: str, expiration: str
    ) -> tuple[pd.DataFrame, pd.DataFrame]: ...


class YFinanceDataSource:
    """Default DataSource backed by yfinance with an in-process TTL cache."""

    def __init__(self, cache_ttl_minutes: int = 60, request_timeout: int = 30):
        self._ttl = timedelta(minutes=cache_ttl_minutes)
        self._timeout = request_timeout
        self._history_cache: dict[tuple[str, int], tuple[datetime, pd.DataFrame]] = {}
        self._snapshot_cache: dict[tuple[str, int], tuple[datetime, TickerSnapshot]] = {}

    # ------------------------------------------------------------------ history
    def get_history(self, ticker: str, days: int) -> pd.DataFrame:
        key = (ticker, days)
        cached = self._history_cache.get(key)
        if cached and datetime.utcnow() - cached[0] < self._ttl:
            return cached[1]

        import yfinance as yf

        end = date.today()
        start = end - timedelta(days=int(days * 1.6) + 30)  # cover weekends/holidays
        try:
            df = yf.download(
                ticker,
                start=start.isoformat(),
                end=(end + timedelta(days=1)).isoformat(),
                auto_adjust=True,
                progress=False,
                threads=False,
                timeout=self._timeout,
            )
        except Exception as exc:  # pragma: no cover - network
            logger.warning("history fetch failed for %s: %s", ticker, exc)
            df = pd.DataFrame()

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        if not df.empty:
            df = df.tail(days).copy()
        self._history_cache[key] = (datetime.utcnow(), df)
        return df

    # ----------------------------------------------------------------- snapshot
    def get_snapshot(self, ticker: str, history_days: int) -> TickerSnapshot:
        key = (ticker, history_days)
        cached = self._snapshot_cache.get(key)
        if cached and datetime.utcnow() - cached[0] < self._ttl:
            return cached[1]

        import yfinance as yf

        history = self.get_history(ticker, history_days)
        info: dict = {}
        expirations: list[str] = []
        try:
            t = yf.Ticker(ticker)
            info = getattr(t, "info", {}) or {}
            expirations = list(getattr(t, "options", []) or [])
        except Exception as exc:  # pragma: no cover - network
            logger.warning("metadata fetch failed for %s: %s", ticker, exc)

        snapshot = TickerSnapshot(
            ticker=ticker,
            history=history,
            info=info,
            options_expirations=expirations,
            sector=info.get("sector"),
            market_cap=_safe_float(info.get("marketCap")),
        )
        self._snapshot_cache[key] = (datetime.utcnow(), snapshot)
        return snapshot

    # ------------------------------------------------------------------ options
    def get_options_chain(
        self, ticker: str, expiration: str
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        import yfinance as yf

        try:
            chain = yf.Ticker(ticker).option_chain(expiration)
        except Exception as exc:  # pragma: no cover - network
            logger.warning("option_chain failed for %s @ %s: %s", ticker, expiration, exc)
            return pd.DataFrame(), pd.DataFrame()
        calls = chain.calls.copy() if chain.calls is not None else pd.DataFrame()
        puts = chain.puts.copy() if chain.puts is not None else pd.DataFrame()
        return calls, puts


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if np.isnan(f) or np.isinf(f):
        return None
    return f


# Tiny helper so engines can throttle batch fetches if the underlying provider
# rate limits aggressively.
def with_backoff(func, *, attempts: int = 3, base_delay: float = 1.0):
    last_exc: Exception | None = None
    for i in range(attempts):
        try:
            return func()
        except Exception as exc:  # pragma: no cover - exercised in integration
            last_exc = exc
            time.sleep(base_delay * (2**i))
    if last_exc:
        raise last_exc
