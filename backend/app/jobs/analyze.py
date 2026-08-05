"""Analyze stored prints into zones + signals for one day or a window.

Run AFTER ingest + enrich for the same dates. Analysis itself needs no
network access; ``--crosscheck`` additionally verifies our stored dark
volume against the provider's own price-levels aggregation (plan §9).

    python -m app.jobs.analyze
    python -m app.jobs.analyze --date 2026-08-05 --crosscheck
    python -m app.jobs.analyze --backfill-days 14
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime, time, timedelta

import sqlalchemy as sa

from app.analytics.analyze import analyze_day, crosscheck_price_levels
from app.client.uw_client import UWClient
from app.config import load_config
from app.db import ensure_schema, make_engine, prints
from app.ingestion.store import store_probe
from app.jobs.ingest import trading_days_back


def run_crosscheck(engine, client: UWClient, trading_date: date) -> dict[str, dict]:
    window_start = datetime.combine(trading_date, time(0, 0), tzinfo=UTC)
    window_end = window_start + timedelta(days=2)
    results: dict[str, dict] = {}
    with engine.begin() as conn:
        tickers = conn.execute(
            sa.select(prints.c.ticker)
            .where(prints.c.executed_at >= window_start, prints.c.executed_at < window_end)
            .distinct()
        ).scalars().all()
        for ticker in sorted(tickers):
            ours = conn.execute(
                sa.select(sa.func.sum(prints.c.size)).where(
                    prints.c.ticker == ticker,
                    prints.c.executed_at >= window_start,
                    prints.c.executed_at < window_end,
                )
            ).scalar() or 0
            levels = client.darkpool_price_levels(ticker, date=trading_date.isoformat())
            results[ticker] = crosscheck_price_levels(int(ours), levels or {})
        store_probe(
            conn,
            "price_levels_crosscheck",
            {"date": trading_date.isoformat(), "results": results},
            ran_at=datetime.now(UTC),
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Trading date YYYY-MM-DD (default: last weekday)")
    parser.add_argument(
        "--backfill-days", type=int, default=1, help="How many trading days to analyze"
    )
    parser.add_argument(
        "--crosscheck",
        action="store_true",
        help="Also verify stored dark volume against the provider's price levels",
    )
    args = parser.parse_args()

    config = load_config()
    engine = make_engine(config.secrets.database_url)
    ensure_schema(engine)

    if args.date:
        end = date.fromisoformat(args.date)
    else:
        end = trading_days_back(datetime.now(UTC).date() - timedelta(days=1), 1)[0]

    for trading_date in trading_days_back(end, args.backfill_days):
        stats = analyze_day(engine, config.settings, trading_date)
        print(json.dumps(stats, indent=2, default=str))

        if args.crosscheck:
            api = config.settings.api
            with UWClient(
                config.secrets.uw_api_token,
                base_url=api.base_url,
                requests_per_minute=api.requests_per_minute,
                max_retries=api.max_retries,
                backoff_seconds=tuple(api.backoff_seconds),
                timeout=api.timeout_seconds,
            ) as client:
                checks = run_crosscheck(engine, client, trading_date)
            print(json.dumps({"crosscheck": checks}, indent=2, default=str))


if __name__ == "__main__":
    main()
