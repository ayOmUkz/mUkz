"""The nightly pipeline: ingest → enrich → analyze → alerts → digest → reports.

    python -m app.jobs.nightly                     # last trading day
    python -m app.jobs.nightly --date 2026-08-05
    python -m app.jobs.nightly --report-dir reports_out

Schedule it however you like (cron, systemd timer, Task Scheduler); each
run is idempotent, so re-running a day is always safe.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import Engine

from app.alerts import build_digest, evaluate_alerts, send_digest
from app.analytics.analyze import analyze_day
from app.client.uw_client import UWClient
from app.config import AppConfig, Settings, load_config
from app.db import ensure_schema, make_engine, signals
from app.enrichment.enrich import enrich_day
from app.ingestion.ingest import ingest_day
from app.jobs.ingest import trading_days_back
from app.reports import build_ticker_report, render_markdown


def run_nightly(
    engine: Engine,
    client: Any,
    settings: Settings,
    trading_date: date,
    *,
    report_dir: Path | None = None,
) -> dict[str, Any]:
    """Run the full chain for one date; returns a stage-by-stage summary."""
    ingest_stats = ingest_day(engine, client, settings, trading_date)
    enrich_stats = enrich_day(engine, client, settings, trading_date)
    analyze_stats = analyze_day(engine, settings, trading_date)

    with engine.begin() as conn:
        emitted = evaluate_alerts(conn, trading_date, settings)

    reports_written: list[str] = []
    with engine.connect() as conn:
        tickers = conn.execute(
            sa.select(signals.c.ticker).where(signals.c.as_of_date == trading_date)
        ).scalars().all()
        for ticker in sorted(tickers):
            report = build_ticker_report(conn, ticker, trading_date, settings)
            if report is None:
                continue
            if report_dir is not None:
                report_dir.mkdir(parents=True, exist_ok=True)
                stem = report_dir / f"{trading_date.isoformat()}_{ticker}"
                stem.with_suffix(".json").write_text(
                    json.dumps(report, indent=2, default=str), encoding="utf-8"
                )
                stem.with_suffix(".md").write_text(render_markdown(report), encoding="utf-8")
            reports_written.append(ticker)

    return {
        "date": trading_date.isoformat(),
        "ingest": ingest_stats["totals"],
        "enrich": {k: v for k, v in enrich_stats.items() if k != "per_ticker"},
        "analyze": {k: v for k, v in analyze_stats.items() if k != "per_ticker"},
        "alerts": emitted,
        "reports": reports_written,
    }


def _email_digest(config: AppConfig, trading_date: date, emitted: list[dict]) -> dict:
    if not config.settings.alerts.email_digest:
        return {"sent": False, "reason": "digest_disabled"}
    subject, body = build_digest(trading_date, emitted)
    return send_digest(config.secrets, subject, body)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Trading date YYYY-MM-DD (default: last weekday)")
    parser.add_argument("--report-dir", default="reports_out", help="Where to write reports")
    args = parser.parse_args()

    config = load_config()
    engine = make_engine(config.secrets.database_url)
    ensure_schema(engine)

    if args.date:
        trading_date = date.fromisoformat(args.date)
    else:
        trading_date = trading_days_back(datetime.now(UTC).date() - timedelta(days=1), 1)[0]

    api = config.settings.api
    with UWClient(
        config.secrets.uw_api_token,
        base_url=api.base_url,
        requests_per_minute=api.requests_per_minute,
        max_retries=api.max_retries,
        backoff_seconds=tuple(api.backoff_seconds),
        timeout=api.timeout_seconds,
    ) as client:
        summary = run_nightly(
            engine, client, config.settings, trading_date,
            report_dir=Path(args.report_dir),
        )

    summary["email"] = _email_digest(config, trading_date, summary["alerts"])
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
