"""Print one ticker's Phase-12 report as markdown (or JSON with --json).

    python -m app.jobs.report --ticker NVDA
    python -m app.jobs.report --ticker NVDA --date 2026-08-05 --json
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime, timedelta

from app.config import load_config
from app.db import ensure_schema, make_engine
from app.jobs.ingest import trading_days_back
from app.reports import build_ticker_report, render_markdown


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--date", help="Trading date YYYY-MM-DD (default: last weekday)")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown")
    args = parser.parse_args()

    config = load_config()
    engine = make_engine(config.secrets.database_url)
    ensure_schema(engine)

    if args.date:
        as_of = date.fromisoformat(args.date)
    else:
        as_of = trading_days_back(datetime.now(UTC).date() - timedelta(days=1), 1)[0]

    with engine.connect() as conn:
        report = build_ticker_report(conn, args.ticker.upper(), as_of, config.settings)
    if report is None:
        print(f"No signal stored for {args.ticker.upper()} on {as_of.isoformat()} — "
              "run app.jobs.analyze first.")
        raise SystemExit(1)
    print(json.dumps(report, indent=2, default=str) if args.json else render_markdown(report))


if __name__ == "__main__":
    main()
