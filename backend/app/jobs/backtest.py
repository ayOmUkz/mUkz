"""Run the event-study backtest over every stored signal.

    python -m app.jobs.backtest
    python -m app.jobs.backtest --start 2026-06-01 --end 2026-08-05
    python -m app.jobs.backtest --report-dir reports_out
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime
from pathlib import Path

from app.backtest import render_backtest_report, run_backtest
from app.config import load_config
from app.db import ensure_schema, make_engine


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", help="First signal date YYYY-MM-DD (default: all)")
    parser.add_argument("--end", help="Last signal date YYYY-MM-DD (default: all)")
    parser.add_argument("--report-dir", default="reports_out")
    args = parser.parse_args()

    config = load_config()
    engine = make_engine(config.secrets.database_url)
    ensure_schema(engine)

    run = run_backtest(
        engine,
        config.settings,
        start=date.fromisoformat(args.start) if args.start else None,
        end=date.fromisoformat(args.end) if args.end else None,
    )
    report = render_backtest_report(run)

    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    path = report_dir / f"backtest_{stamp}_{run['config_hash']}.md"
    path.write_text(report, encoding="utf-8")

    print(json.dumps({"run_id": run["run_id"], "config_hash": run["config_hash"],
                      "summary": run["summary"], "report": str(path)},
                     indent=2, default=str))


if __name__ == "__main__":
    main()
