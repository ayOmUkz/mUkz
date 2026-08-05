"""Ingest dark-pool prints for one day or a backfill window.

Usage (from ``backend/`` with the venv active, .env filled in):

    python -m app.jobs.ingest                    # last trading day
    python -m app.jobs.ingest --date 2026-08-05  # a specific session
    python -m app.jobs.ingest --backfill-days 14 # the M1 exit criterion
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime, timedelta

from app.client.uw_client import UWClient
from app.config import load_config
from app.db import ensure_schema, make_engine
from app.ingestion.ingest import ingest_day


def trading_days_back(end: date, count: int) -> list[date]:
    """The last ``count`` weekdays ending at ``end`` (newest first)."""
    days: list[date] = []
    current = end
    while len(days) < count:
        if current.weekday() < 5:
            days.append(current)
        current -= timedelta(days=1)
    return days


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Trading date YYYY-MM-DD (default: last weekday)")
    parser.add_argument(
        "--backfill-days", type=int, default=1, help="How many trading days to ingest"
    )
    args = parser.parse_args()

    config = load_config()
    engine = make_engine(config.secrets.database_url)
    ensure_schema(engine)

    if args.date:
        end = date.fromisoformat(args.date)
    else:
        end = trading_days_back(datetime.now(UTC).date() - timedelta(days=1), 1)[0]

    api = config.settings.api
    with UWClient(
        config.secrets.uw_api_token,
        base_url=api.base_url,
        requests_per_minute=api.requests_per_minute,
        max_retries=api.max_retries,
        backoff_seconds=tuple(api.backoff_seconds),
        timeout=api.timeout_seconds,
    ) as client:
        for trading_date in trading_days_back(end, args.backfill_days):
            stats = ingest_day(engine, client, config.settings, trading_date)
            summary = {k: v for k, v in stats.items() if k != "per_ticker"}
            print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
