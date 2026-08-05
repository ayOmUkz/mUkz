"""The M2 enrichment pipeline: candles → context → stats → classification.

Runs after ingestion for a trading date. Per ticker (own transaction, same
failure isolation as ingest):

1. fetch + store daily and minute candles,
2. compute the day context (session VWAP, ATR, prior-day levels)
   into ``symbol_days``,
3. summarize the symbol's rolling dark-print size distribution
   into ``symbol_stats``,
4. classify every print of that session (UPDATE on ``prints``).

Classification is deterministic given (print, context, stats, config), so
re-running a day overwrites with identical values — idempotent by
construction.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, Protocol
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from sqlalchemy.engine import Connection, Engine

from app.analytics.classify import (
    liquidity_character,
    location_bucket,
    size_classification,
    timing_bucket,
    vwap_position,
)
from app.client.uw_client import UWAPIError
from app.config import Settings
from app.db import candles as candles_table
from app.db import insert_ignore, prints, symbol_days, symbol_stats
from app.enrichment.candles import (
    compute_atr,
    normalize_candles,
    prior_day_levels,
    session_vwap,
)
from app.enrichment.stats import size_distribution
from app.ingestion.store import log_rejections
from app.validation import Rejection

ET = ZoneInfo("America/New_York")


class CandleSource(Protocol):
    def ohlc(self, ticker: str, candle_size: str, **kwargs: Any) -> list[dict[str, Any]]: ...


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _upsert_by_key(conn: Connection, table: sa.Table, key: dict[str, Any], values: dict) -> None:
    condition = sa.and_(*(table.c[column] == v for column, v in key.items()))
    conn.execute(sa.delete(table).where(condition))
    conn.execute(table.insert().values(**key, **values))


def day_prints(conn: Connection, ticker: str, trading_date: date) -> list[dict[str, Any]]:
    """All stored prints of one ticker whose *Eastern* date is the session."""
    window_start = datetime.combine(trading_date, time(0, 0), tzinfo=UTC)
    window_end = window_start + timedelta(days=2)
    rows = conn.execute(
        sa.select(prints).where(
            prints.c.ticker == ticker,
            prints.c.executed_at >= window_start,
            prints.c.executed_at < window_end,
        )
    ).mappings().all()
    return [
        dict(row)
        for row in rows
        if _as_utc(row["executed_at"]).astimezone(ET).date() == trading_date
    ]


def fetch_and_store_candles(
    conn: Connection,
    client: CandleSource,
    ticker: str,
    trading_date: date,
    settings: Settings,
    *,
    now: datetime,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Fetch daily + minute candles, store them, return (daily, minute)."""
    cfg = settings.enrichment
    daily_raw = client.ohlc(
        ticker, "1d", timeframe="6M", end_date=trading_date.isoformat()
    )
    minute_raw = client.ohlc(
        ticker, cfg.minute_candle_size, date=trading_date.isoformat(), limit=2500
    )
    daily, bad_daily = normalize_candles(daily_raw, ticker=ticker, candle_size="1d")
    minute, bad_minute = normalize_candles(
        minute_raw, ticker=ticker, candle_size=cfg.minute_candle_size
    )
    insert_ignore(conn, candles_table, daily)
    insert_ignore(conn, candles_table, minute)
    unparseable = bad_daily + bad_minute
    if unparseable:
        log_rejections(
            conn,
            [
                Rejection(row={"ticker": ticker, **row}, stage="candle_parse",
                          reasons=["unrecognized_candle_shape"])
                for row in unparseable
            ],
            logged_at=now,
        )
    return daily, minute


def fetch_options_tilt(client: Any, ticker: str) -> dict[str, Any] | None:
    """Daily call/put premium from the options-volume endpoint (group D).

    Field naming is read tolerantly; clients without the method (older
    fakes, restricted plans) simply yield None — the evidence ledger then
    generates no group-D items, which is the honest default.
    """
    getter = getattr(client, "options_volume", None)
    if getter is None:
        return None
    try:
        rows = getter(ticker, limit=1)
    except UWAPIError:
        return None
    row = rows[0] if isinstance(rows, list) and rows else rows
    if not isinstance(row, dict):
        return None

    def _first(keys: tuple[str, ...]) -> Any:
        for key in keys:
            if row.get(key) is not None:
                try:
                    return abs(Decimal(str(row[key])))
                except (ArithmeticError, ValueError):
                    return None
        return None

    call = _first(("call_premium", "call_prem"))
    put = _first(("put_premium", "put_prem"))
    if call is None or put is None:
        return None
    return {"call_premium": call, "put_premium": put}


def build_day_context(
    conn: Connection,
    ticker: str,
    trading_date: date,
    daily: list[dict[str, Any]],
    minute: list[dict[str, Any]],
    settings: Settings,
    *,
    now: datetime,
    options_tilt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    vwap = session_vwap(minute)
    atr = compute_atr(daily, settings.enrichment.atr_period)
    prior_high, prior_low, prior_close = prior_day_levels(daily, trading_date)
    context = {
        "session_vwap": vwap,
        "atr14": atr,
        "prior_high": prior_high,
        "prior_low": prior_low,
        "prior_close": prior_close,
        "minute_bars": len(minute),
        "call_premium": (options_tilt or {}).get("call_premium"),
        "put_premium": (options_tilt or {}).get("put_premium"),
    }
    _upsert_by_key(
        conn,
        symbol_days,
        {"ticker": ticker, "trading_date": trading_date},
        {**context, "updated_at": now},
    )
    return context


def build_symbol_stats(
    conn: Connection, ticker: str, trading_date: date, settings: Settings, *, now: datetime
) -> dict[str, Any]:
    """Rolling size distribution from our own stored prints (plan §7)."""
    window_start = datetime.combine(
        trading_date - timedelta(days=settings.size_classes.history_days),
        time(0, 0),
        tzinfo=UTC,
    )
    window_end = datetime.combine(trading_date + timedelta(days=1), time(0, 0), tzinfo=UTC)
    sizes = (
        conn.execute(
            sa.select(prints.c.size).where(
                prints.c.ticker == ticker,
                prints.c.executed_at >= window_start,
                prints.c.executed_at < window_end,
            )
        )
        .scalars()
        .all()
    )
    stats = size_distribution(list(sizes))
    _upsert_by_key(
        conn,
        symbol_stats,
        {"ticker": ticker, "as_of_date": trading_date},
        {**stats, "updated_at": now},
    )
    return stats


def classify_row(
    row: dict[str, Any], context: dict[str, Any], stats: dict[str, Any], settings: Settings
) -> dict[str, Any]:
    """Pure mapping from one stored print to its classification columns."""
    late_seconds = settings.location.late_report_seconds
    quote_usable = row["location_confidence"] in ("ok", "low")
    location = (
        location_bucket(
            row["price"],
            row["nbbo_bid"],
            row["nbbo_ask"],
            spread_tolerance=settings.location.spread_tolerance,
        )
        if quote_usable
        else None
    )
    size_class, size_pct, size_conf = size_classification(
        size=row["size"],
        premium=row["premium"],
        pct_adv30=row["pct_adv30"],
        stats=stats,
        config=settings.size_classes,
    )
    return {
        "size_class": size_class,
        "size_percentile": size_pct,
        "size_confidence": size_conf,
        "location_bucket": location,
        "vwap_position": vwap_position(
            row["price"], context.get("session_vwap"),
            band_pct=settings.location.vwap_band_pct,
        ),
        "timing_bucket": timing_bucket(
            _as_utc(row["executed_at"]),
            report_delay_s=row["report_delay_s"],
            late_report_seconds=late_seconds,
        ),
        "character": liquidity_character(
            sale_cond_codes=row["sale_cond_codes"],
            trade_code=row["trade_code"],
            size=row["size"],
            size_class=size_class,
            nbbo_bid_quantity=row["nbbo_bid_quantity"],
            nbbo_ask_quantity=row["nbbo_ask_quantity"],
            report_delay_s=row["report_delay_s"],
            location=location,
            late_report_seconds=late_seconds,
        ),
    }


def enrich_ticker_day(
    conn: Connection,
    client: CandleSource,
    ticker: str,
    trading_date: date,
    settings: Settings,
    *,
    now: datetime,
) -> dict[str, Any]:
    daily, minute = fetch_and_store_candles(
        conn, client, ticker, trading_date, settings, now=now
    )
    context = build_day_context(
        conn, ticker, trading_date, daily, minute, settings, now=now,
        options_tilt=fetch_options_tilt(client, ticker),
    )
    stats = build_symbol_stats(conn, ticker, trading_date, settings, now=now)

    classified = 0
    for row in day_prints(conn, ticker, trading_date):
        updates = classify_row(row, context, stats, settings)
        conn.execute(
            prints.update()
            .where(
                prints.c.ticker == row["ticker"],
                prints.c.tracking_id == row["tracking_id"],
                prints.c.executed_at == row["executed_at"],
            )
            .values(**updates)
        )
        classified += 1
    return {
        "daily_bars": len(daily),
        "minute_bars": len(minute),
        "has_vwap": context["session_vwap"] is not None,
        "has_atr": context["atr14"] is not None,
        "stats_sample": stats["sample_size"],
        "classified": classified,
    }


def enrich_day(
    engine: Engine,
    client: CandleSource,
    settings: Settings,
    trading_date: date,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Enrich + classify every ticker that has prints for the session."""
    now = now or datetime.now(UTC)
    window_start = datetime.combine(trading_date, time(0, 0), tzinfo=UTC)
    window_end = window_start + timedelta(days=2)
    with engine.connect() as conn:
        tickers = (
            conn.execute(
                sa.select(prints.c.ticker)
                .where(
                    prints.c.executed_at >= window_start,
                    prints.c.executed_at < window_end,
                )
                .distinct()
            )
            .scalars()
            .all()
        )

    per_ticker: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for ticker in sorted(tickers):
        try:
            with engine.begin() as conn:
                per_ticker[ticker] = enrich_ticker_day(
                    conn, client, ticker, trading_date, settings, now=now
                )
        except UWAPIError as exc:
            errors[ticker] = str(exc)

    return {
        "date": trading_date.isoformat(),
        "tickers": len(per_ticker),
        "classified": sum(t["classified"] for t in per_ticker.values()),
        "errors": errors,
        "per_ticker": per_ticker,
    }
