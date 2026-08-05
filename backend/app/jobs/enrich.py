"""Enrich + classify stored prints for one day or a backfill window.

Run AFTER ``app.jobs.ingest`` for the same dates:

    python -m app.jobs.enrich                    # last trading day
    python -m app.jobs.enrich --date 2026-08-05
    python -m app.jobs.enrich --backfill-days 14
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime, timedelta

from app.client.uw_client import UWClient
from app.config import load_config
from app.db import ensure_schema, make_engine
from app.enrichment.enrich import enrich_day
from app.jobs.ingest import trading_days_back


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Trading date YYYY-MM-DD (default: last weekday)")
    parser.add_argument(
        "--backfill-days", type=int, default=1, help="How many trading days to enrich"
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
            stats = enrich_day(engine, client, config.settings, trading_date)
            summary = {k: v for k, v in stats.items() if k != "per_ticker"}
            print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
