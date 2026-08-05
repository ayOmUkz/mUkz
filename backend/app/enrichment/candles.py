"""Candle normalization and the price math built on candles.

The provider's candle field names vary by surface (``open`` vs ``o``,
``volume`` vs ``vol``, ``start_time`` vs ``start``, and daily bars carry
only a ``date``), so everything goes through :func:`normalize_candles`
first. Rows that cannot be normalized are returned separately — never
silently dropped (plan §2.5).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any

#: Accepted aliases per canonical field, tried in order.
_ALIASES: dict[str, tuple[str, ...]] = {
    "open": ("open", "o"),
    "high": ("high", "h"),
    "low": ("low", "l"),
    "close": ("close", "c"),
    "volume": ("volume", "vol", "v"),
    "ts": ("start_time", "start", "t", "date"),
    "session": ("market", "market_time", "session"),
}


def _pick(row: dict[str, Any], field: str) -> Any:
    for alias in _ALIASES[field]:
        if alias in row and row[alias] is not None:
            return row[alias]
    return None


def _dec(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _ts(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if isinstance(parsed, datetime):
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return None


def normalize_candles(
    rows: list[dict[str, Any]], *, ticker: str, candle_size: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Map raw candle rows onto the ``candles`` table shape.

    Returns ``(records, unparseable_rows)``. A bare date string (daily bars)
    becomes midnight UTC of that date.
    """
    records: list[dict[str, Any]] = []
    unparseable: list[dict[str, Any]] = []
    for row in rows:
        raw_ts = _pick(row, "ts")
        ts = _ts(raw_ts)
        if ts is None and isinstance(raw_ts, str):
            try:
                ts = datetime.combine(date.fromisoformat(raw_ts), time(0, 0), tzinfo=UTC)
            except ValueError:
                ts = None
        open_, high = _dec(_pick(row, "open")), _dec(_pick(row, "high"))
        low, close = _dec(_pick(row, "low")), _dec(_pick(row, "close"))
        if ts is None or None in (open_, high, low, close):
            unparseable.append(row)
            continue
        volume = _pick(row, "volume")
        records.append(
            {
                "ticker": ticker,
                "candle_size": candle_size,
                "ts": ts,
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": int(volume) if volume is not None else None,
                "session": _pick(row, "session"),
            }
        )
    return records, unparseable


def session_vwap(minute_records: list[dict[str, Any]]) -> Decimal | None:
    """Volume-weighted average price from minute bars (typical price basis).

    If bars carry a session marker, only regular-session bars count; without
    markers all bars count (documented approximation).
    """
    marked = [r for r in minute_records if r.get("session") in ("r", "regular")]
    bars = marked or minute_records
    weighted = Decimal(0)
    total_volume = 0
    for bar in bars:
        volume = bar.get("volume") or 0
        if volume <= 0:
            continue
        typical = (bar["high"] + bar["low"] + bar["close"]) / 3
        weighted += typical * volume
        total_volume += volume
    if total_volume == 0:
        return None
    return (weighted / total_volume).quantize(Decimal("0.000001"))


def compute_atr(daily_records: list[dict[str, Any]], period: int) -> float | None:
    """Average True Range over the last ``period`` daily bars (SMA of TR).

    Needs at least ``period + 1`` bars (true range references the previous
    close). Returns None when history is insufficient — callers must treat
    a missing ATR as "no volatility context", not zero.
    """
    bars = sorted(daily_records, key=lambda r: r["ts"])
    if len(bars) < period + 1:
        return None
    true_ranges: list[Decimal] = []
    for previous, current in zip(bars[:-1], bars[1:], strict=True):
        previous_close = previous["close"]
        true_range = max(
            current["high"] - current["low"],
            abs(current["high"] - previous_close),
            abs(current["low"] - previous_close),
        )
        true_ranges.append(true_range)
    recent = true_ranges[-period:]
    return float(sum(recent) / len(recent))


def prior_day_levels(
    daily_records: list[dict[str, Any]], trading_date: date
) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    """(high, low, close) of the last daily bar strictly before the date."""
    earlier = [r for r in daily_records if r["ts"].date() < trading_date]
    if not earlier:
        return None, None, None
    last = max(earlier, key=lambda r: r["ts"])
    return last["high"], last["low"], last["close"]
