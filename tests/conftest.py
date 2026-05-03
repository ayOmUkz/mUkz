"""Shared fixtures: an in-memory FakeDataSource and synthetic OHLCV builders."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from scanner.data_sources import TickerSnapshot


def make_history(
    days: int = 400,
    start_price: float = 50.0,
    drift: float = 0.0,
    vol: float = 0.02,
    volume: int = 1_000_000,
    seed: int = 42,
    recent_trend_days: int = 30,
    recent_trend_pct: float | None = None,
) -> pd.DataFrame:
    """Build deterministic OHLCV history with a controlled drift + vol.

    ``recent_trend_pct`` overrides the noisy walk over the last
    ``recent_trend_days`` bars, producing a clean linear price ramp.
    Use this whenever a test needs a guaranteed recent return (e.g. to
    pass the ``min_1m_return`` momentum filter) without seed roulette.
    """
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(end=date.today(), periods=days)
    n = len(idx)
    daily_returns = rng.normal(loc=drift, scale=vol, size=n)
    prices = start_price * np.exp(np.cumsum(daily_returns))

    if recent_trend_pct is not None and recent_trend_days > 0 and n > recent_trend_days:
        anchor = float(prices[-recent_trend_days - 1])
        target = anchor * (1.0 + recent_trend_pct)
        ramp = np.linspace(anchor, target, recent_trend_days + 1)[1:]
        prices = prices.copy()
        prices[-recent_trend_days:] = ramp
    df = pd.DataFrame(
        {
            "Open": prices * (1 - 0.001),
            "High": prices * (1 + 0.005),
            "Low": prices * (1 - 0.005),
            "Close": prices,
            "Volume": np.full(n, volume, dtype=float),
        },
        index=idx,
    )
    return df


def make_chain(
    underlying: float,
    strikes: list[float] | None = None,
    iv: float = 0.30,
    volume: int = 500,
    open_interest: int = 800,
    spread_pct: float = 0.04,
) -> pd.DataFrame:
    """Synthetic chain with a simple intrinsic+time-value pricing model.

    The mid price is ``intrinsic + 5% of underlying``, and bid/ask are
    placed symmetrically around the mid using ``spread_pct`` (default
    4%). This keeps generated chains realistic enough to exercise the
    bid-ask filter without reaching for an options pricing library.
    """
    if strikes is None:
        strikes = [underlying * (1 + d) for d in (-0.10, -0.05, 0.0, 0.05, 0.10)]
    rows = []
    time_value = 0.05 * float(underlying)
    for k in strikes:
        intrinsic = max(0.0, float(underlying) - float(k))
        mid = max(0.50, intrinsic + time_value)
        half = mid * (spread_pct / 2.0)
        rows.append(
            {
                "strike": float(k),
                "bid": round(mid - half, 2),
                "ask": round(mid + half, 2),
                "volume": volume,
                "openInterest": open_interest,
                "impliedVolatility": iv,
            }
        )
    return pd.DataFrame(rows)


@dataclass
class FakeDataSource:
    histories: dict[str, pd.DataFrame] = field(default_factory=dict)
    infos: dict[str, dict] = field(default_factory=dict)
    expirations: dict[str, list[str]] = field(default_factory=dict)
    chains: dict[tuple[str, str], tuple[pd.DataFrame, pd.DataFrame]] = field(default_factory=dict)

    def get_history(self, ticker: str, days: int) -> pd.DataFrame:
        df = self.histories.get(ticker, pd.DataFrame())
        if df.empty:
            return df
        return df.tail(days).copy()

    def get_snapshot(self, ticker: str, history_days: int) -> TickerSnapshot:
        info = self.infos.get(ticker, {})
        return TickerSnapshot(
            ticker=ticker,
            history=self.get_history(ticker, history_days),
            info=info,
            options_expirations=list(self.expirations.get(ticker, [])),
            sector=info.get("sector"),
            market_cap=info.get("marketCap"),
        )

    def get_options_chain(self, ticker: str, expiration: str):
        return self.chains.get((ticker, expiration), (pd.DataFrame(), pd.DataFrame()))


@pytest.fixture
def fake_data() -> FakeDataSource:
    return FakeDataSource()


def near_future_date(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()
