"""Market context (plan §12): trends and confirmation labels.

Context never *creates* a signal — it only confirms, conflicts, or
isolates one. Trends are computed from candles already stored by the
enrich stage; when a benchmark's candles are not in the database (e.g. a
sector ETF nobody ingested), the answer is honestly ``None``, never a
guess. Options-flow confirmation (evidence group D) plugs in here in a
later increment.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from statistics import fmean
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from app.db import candles

#: SPDR sector ETFs, keyed by the API's sector names.
SECTOR_ETFS = {
    "Technology": "XLK",
    "Financial Services": "XLF",
    "Healthcare": "XLV",
    "Energy": "XLE",
    "Consumer Cyclical": "XLY",
    "Consumer Defensive": "XLP",
    "Industrials": "XLI",
    "Basic Materials": "XLB",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Communication Services": "XLC",
}
#: Bars needed before a trend call is made at all.
MIN_TREND_BARS = 25
#: Relative SMA slope below which the trend is "sideways".
TREND_SLOPE_EPS = 0.001


def trend_from_daily(daily_bars: list[dict[str, Any]]) -> str | None:
    """"up" / "down" / "sideways" from closes vs a 20-bar average and its slope.

    Deliberately simple and deterministic; returns None on thin history.
    """
    ordered = sorted(daily_bars, key=lambda bar: bar["ts"])
    closes = [float(bar["close"]) for bar in ordered]
    if len(closes) < MIN_TREND_BARS:
        return None
    sma_now = fmean(closes[-20:])
    sma_prev = fmean(closes[-25:-5])
    close = closes[-1]
    if close > sma_now and sma_now > sma_prev * (1 + TREND_SLOPE_EPS):
        return "up"
    if close < sma_now and sma_now < sma_prev * (1 - TREND_SLOPE_EPS):
        return "down"
    return "sideways"


def load_daily(conn: Connection, ticker: str, as_of: date, *, days: int = 90) -> list[dict]:
    window_start = datetime.combine(as_of - timedelta(days=days), time(0, 0), tzinfo=UTC)
    window_end = datetime.combine(as_of + timedelta(days=1), time(0, 0), tzinfo=UTC)
    rows = conn.execute(
        sa.select(candles).where(
            candles.c.ticker == ticker,
            candles.c.candle_size == "1d",
            candles.c.ts >= window_start,
            candles.c.ts < window_end,
        )
    ).mappings().all()
    return sorted((dict(row) for row in rows), key=lambda row: row["ts"])


def ticker_trend(conn: Connection, ticker: str, as_of: date) -> str | None:
    return trend_from_daily(load_daily(conn, ticker, as_of))


def market_context(conn: Connection, as_of: date) -> dict[str, str | None]:
    return {
        "spy_trend": ticker_trend(conn, "SPY", as_of),
        "qqq_trend": ticker_trend(conn, "QQQ", as_of),
    }


def sector_trend(conn: Connection, sector: str | None, as_of: date) -> str | None:
    etf = SECTOR_ETFS.get(sector or "")
    return ticker_trend(conn, etf, as_of) if etf else None


def signal_direction(classification: str) -> int:
    if classification.endswith("accumulation"):
        return +1
    if classification.endswith("distribution"):
        return -1
    return 0


def context_label(
    *,
    direction: int,
    spy_trend: str | None,
    sector_trend_value: str | None,
    zone_status: str | None,
) -> dict[str, Any]:
    """Confirmation labels for one signal (plan §12).

    Returns ``{"labels": [...], "conflicts": [...], "summary": str}`` where
    summary is one of the plan's states: the joined confirmation labels,
    "conflicting", or "isolated".
    """
    if direction == 0:
        return {"labels": [], "conflicts": [], "summary": "isolated"}

    wanted = "up" if direction > 0 else "down"
    opposite = "down" if direction > 0 else "up"
    labels: list[str] = []
    conflicts: list[str] = []

    if spy_trend == wanted:
        labels.append("market_confirmed")
    elif spy_trend == opposite:
        conflicts.append("market")

    if sector_trend_value == wanted:
        labels.append("sector_confirmed")
    elif sector_trend_value == opposite:
        conflicts.append("sector")

    bullish_statuses = ("respected", "reclaimed")
    if (direction > 0 and zone_status in bullish_statuses) or (
        direction < 0 and zone_status == "broken"
    ):
        labels.append("technically_confirmed")

    if conflicts:
        summary = "conflicting"
    elif labels:
        summary = "+".join(labels)
    else:
        summary = "isolated"
    return {"labels": labels, "conflicts": conflicts, "summary": summary}
