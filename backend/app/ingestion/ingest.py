"""The M1 ingestion pipeline: discovery → deep fetch → validate → store.

Hybrid universe (plan decision): a cheap whole-tape discovery pass finds the
symbols with qualifying dark-pool activity; the deep per-ticker fetch then
pulls *every* print for the watchlist plus the discovered candidates.

Each ticker is ingested in its own transaction, so one bad symbol or one
API hiccup never rolls back a whole day.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Protocol

from sqlalchemy.engine import Engine

from app.client.uw_client import UWAPIError
from app.config import Settings
from app.ingestion import store
from app.validation import validate_rows


class DarkPoolSource(Protocol):
    """What the pipeline needs from a client (real UWClient or a test fake)."""

    def recent_darkpool_trades(self, **kwargs: Any) -> list[dict[str, Any]]: ...

    def iter_ticker_darkpool_trades(self, ticker: str, **kwargs: Any): ...


def session_cutoff(trading_date: date) -> datetime:
    """The ``as_of`` used to validate a session's prints.

    End of the trading date plus a margin (after-hours prints report late),
    so validation is reproducible: re-running a backfill months later yields
    the same clean/stale/future verdicts as running it that evening.
    """
    return datetime.combine(trading_date + timedelta(days=2), time(0, 0), tzinfo=UTC)


def discover_candidates(
    client: DarkPoolSource, settings: Settings, trading_date: date
) -> list[str]:
    """Whole-tape scan: tickers with qualifying prints, biggest premium first."""
    rows = client.recent_darkpool_trades(
        date=trading_date.isoformat(),
        limit=settings.discovery.limit,
        min_premium=settings.discovery.min_premium,
        min_size=settings.discovery.min_size,
        order_by="premium",
        order="desc",
    )
    candidates: list[str] = []
    seen: set[str] = set()
    for row in rows:
        ticker = row.get("ticker")
        if ticker and ticker not in seen:
            seen.add(ticker)
            candidates.append(ticker)
    return candidates


def build_universe(
    watchlist: list[str], discovered: list[str], *, cap: int
) -> list[str]:
    """Watchlist always in; discovered symbols fill the remaining budget."""
    universe = list(dict.fromkeys(watchlist))
    for ticker in discovered:
        if len(universe) >= cap:
            break
        if ticker not in universe:
            universe.append(ticker)
    return universe


def ingest_ticker_day(
    conn,
    client: DarkPoolSource,
    ticker: str,
    trading_date: date,
    settings: Settings,
    *,
    now: datetime,
) -> dict[str, Any]:
    rows = list(
        client.iter_ticker_darkpool_trades(ticker, date=trading_date.isoformat(), page_limit=500)
    )
    raw_inserted, unstorable = store.store_raw(conn, rows, ingested_at=now)
    result = validate_rows(rows, as_of=session_cutoff(trading_date))
    clean_inserted = store.store_prints(
        conn,
        result.clean,
        late_report_seconds=settings.location.late_report_seconds,
        ingested_at=now,
    )
    store.log_rejections(conn, result.rejected, logged_at=now)
    if unstorable:
        from app.validation import Rejection

        store.log_rejections(
            conn,
            [Rejection(row=row, stage="raw", reasons=["missing_identity_fields"])
             for row in unstorable],
            logged_at=now,
        )
    store.upsert_symbols(conn, rows, seen_at=now)
    return {
        "fetched": len(rows),
        "raw_inserted": raw_inserted,
        "prints_inserted": clean_inserted,
        **result.counts(),
        "unstorable": len(unstorable),
    }


def ingest_day(
    engine: Engine,
    client: DarkPoolSource,
    settings: Settings,
    trading_date: date,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Run the full pipeline for one trading date. Returns the run stats."""
    now = now or datetime.now(UTC)

    with engine.begin() as conn:
        run_id = store.start_run(conn, trading_date, started_at=now)

    try:
        discovered = discover_candidates(client, settings, trading_date)
        discovery_error = None
    except UWAPIError as exc:
        discovered, discovery_error = [], str(exc)

    universe = build_universe(
        settings.universe.watchlist, discovered, cap=settings.discovery.max_symbols_per_day
    )

    per_ticker: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for ticker in universe:
        try:
            with engine.begin() as conn:
                per_ticker[ticker] = ingest_ticker_day(
                    conn, client, ticker, trading_date, settings, now=now
                )
        except UWAPIError as exc:
            errors[ticker] = str(exc)

    stats = {
        "date": trading_date.isoformat(),
        "discovered": len(discovered),
        "discovery_error": discovery_error,
        "universe": len(universe),
        "totals": {
            key: sum(t.get(key, 0) for t in per_ticker.values())
            for key in (
                "fetched",
                "raw_inserted",
                "prints_inserted",
                "clean",
                "flagged",
                "rejected",
                "unstorable",
            )
        },
        "errors": errors,
        "per_ticker": per_ticker,
    }
    with engine.begin() as conn:
        store.finish_run(conn, run_id, finished_at=datetime.now(UTC), stats=stats)
    return stats
