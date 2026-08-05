"""The three M1 verification probes (docs/PLAN.md §2).

Each probe answers a question the API documentation left open, and its
result is stored in ``api_probes`` so the answer is on record:

1. **Historical depth** — how far back does per-ticker dark-pool history go?
2. **NBBO timing** — is the quote attached to a print from *execution* time
   or *report* time? (Decides whether late prints get location math at all.)
3. **Float availability** — do the info/short endpoints expose float /
   shares outstanding, and under which field names?

Probes never guess: they measure, and they report sample sizes.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol

from app.client.uw_client import UWAPIError


class ProbeSource(Protocol):
    def ticker_darkpool_trades(self, ticker: str, **kwargs: Any) -> list[dict[str, Any]]: ...

    def iter_ticker_darkpool_trades(self, ticker: str, **kwargs: Any): ...

    def ticker_info(self, ticker: str) -> dict[str, Any]: ...

    def short_screener(self, **kwargs: Any) -> list[dict[str, Any]]: ...


def _weekdays_back(start: date, count: int) -> list[date]:
    """``count`` weekdays walking backwards from ``start`` (inclusive)."""
    days: list[date] = []
    current = start
    while len(days) < count:
        if current.weekday() < 5:
            days.append(current)
        current -= timedelta(days=1)
    return days


def probe_historical_depth(
    client: ProbeSource,
    ticker: str = "SPY",
    *,
    today: date,
    max_offsets: tuple[int, ...] = (7, 30, 90, 180, 365, 730, 1095, 1825, 2555, 3650),
    resolution_days: int = 7,
) -> dict[str, Any]:
    """Walk backwards until the per-ticker endpoint stops returning data.

    Samples 3 consecutive weekdays at each offset (so a single holiday can't
    fake an empty period), then bisects the boundary to ~1 week resolution.
    """
    calls = 0

    def has_data(anchor: date) -> bool:
        nonlocal calls
        for day in _weekdays_back(anchor, 3):
            calls += 1
            if client.ticker_darkpool_trades(ticker, date=day.isoformat(), limit=1):
                return True
        return False

    last_good: int | None = None
    first_bad: int | None = None
    for offset in max_offsets:
        if has_data(today - timedelta(days=offset)):
            last_good = offset
        else:
            first_bad = offset
            break

    if last_good is None:
        return {"ticker": ticker, "boundary_found": False, "no_data_at_all": True, "calls": calls}
    if first_bad is None:
        return {
            "ticker": ticker,
            "boundary_found": False,
            "earliest_confirmed": (today - timedelta(days=last_good)).isoformat(),
            "note": f"data still present {last_good} days back; probe range exhausted",
            "calls": calls,
        }

    low, high = last_good, first_bad
    while high - low > resolution_days:
        mid = (low + high) // 2
        if has_data(today - timedelta(days=mid)):
            low = mid
        else:
            high = mid
    return {
        "ticker": ticker,
        "boundary_found": True,
        "earliest_confirmed": (today - timedelta(days=low)).isoformat(),
        "empty_at": (today - timedelta(days=high)).isoformat(),
        "resolution_days": high - low,
        "calls": calls,
    }


def _dec(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def probe_nbbo_timing(
    client: ProbeSource,
    ticker: str,
    *,
    date_str: str,
    prompt_max_delay_s: float = 60.0,
    late_min_delay_s: float = 900.0,
) -> dict[str, Any]:
    """Compare quote-consistency of prompt vs late-reported prints.

    For each print with a usable quote, check whether the execution price
    sits inside the attached NBBO. If the quote were captured at *execution*
    time, late prints should be inside about as often as prompt prints. If
    it is captured at *report* time, late prints (whose price is from many
    minutes earlier) will fall outside far more often — and location math on
    late prints must stay disabled (plan §2.3).
    """

    def bucket() -> dict[str, int]:
        return {"n": 0, "inside": 0}

    prompt, late = bucket(), bucket()
    for row in client.iter_ticker_darkpool_trades(ticker, date=date_str, page_limit=500):
        price = _dec(row.get("price"))
        bid = _dec(row.get("nbbo_bid"))
        ask = _dec(row.get("nbbo_ask"))
        try:
            executed = datetime.fromisoformat(row["executed_at"])
            created = datetime.fromisoformat(row["created_at"])
        except (KeyError, TypeError, ValueError):
            continue
        if price is None or bid is None or ask is None or bid <= 0 or bid >= ask:
            continue
        delay = (created - executed).total_seconds()
        if delay <= prompt_max_delay_s:
            target = prompt
        elif delay >= late_min_delay_s:
            target = late
        else:
            continue
        target["n"] += 1
        if bid <= price <= ask:
            target["inside"] += 1

    def rate(b: dict[str, int]) -> float | None:
        return round(b["inside"] / b["n"], 4) if b["n"] else None

    return {
        "ticker": ticker,
        "date": date_str,
        "prompt": {**prompt, "inside_rate": rate(prompt)},
        "late": {**late, "inside_rate": rate(late)},
        "reading": (
            "similar inside_rates -> quote likely captured at execution time; "
            "late much lower -> quote is a report-time snapshot, keep "
            "location_confidence=low for late prints"
        ),
    }


_FLOAT_KEY_HINTS = ("float", "share", "outstanding")


def probe_float_availability(
    client: ProbeSource, tickers: list[str]
) -> dict[str, Any]:
    """Check where float / shares outstanding actually live, per ticker."""
    stock_info: dict[str, Any] = {}
    for ticker in tickers:
        try:
            info = client.ticker_info(ticker)
        except UWAPIError as exc:
            stock_info[ticker] = {"error": exc.status_code or str(exc)}
            continue
        if not isinstance(info, dict):
            stock_info[ticker] = {"error": "unexpected_shape"}
            continue
        stock_info[ticker] = {
            key: info[key]
            for key in info
            if any(hint in key.lower() for hint in _FLOAT_KEY_HINTS)
        }

    screener_fields: set[str] = set()
    screener_error: str | None = None
    try:
        rows = client.short_screener(tickers=",".join(tickers), limit=len(tickers))
        for row in rows if isinstance(rows, list) else []:
            screener_fields.update(
                key for key in row if any(hint in key.lower() for hint in _FLOAT_KEY_HINTS)
            )
    except UWAPIError as exc:
        screener_error = str(exc)

    return {
        "tickers": tickers,
        "stock_info_fields": stock_info,
        "short_screener_float_fields": sorted(screener_fields),
        "short_screener_error": screener_error,
    }


def run_all_probes(
    client: ProbeSource,
    *,
    today: date | None = None,
    depth_ticker: str = "SPY",
    nbbo_ticker: str = "SPY",
    float_tickers: tuple[str, ...] = ("AAPL", "NVDA", "IWM"),
) -> dict[str, dict[str, Any]]:
    today = today or datetime.now(UTC).date()
    last_weekday = _weekdays_back(today - timedelta(days=1), 1)[0]
    return {
        "historical_depth": probe_historical_depth(client, depth_ticker, today=today),
        "nbbo_timing": probe_nbbo_timing(client, nbbo_ticker, date_str=last_weekday.isoformat()),
        "float_availability": probe_float_availability(client, list(float_tickers)),
    }
