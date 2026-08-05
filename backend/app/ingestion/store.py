"""Storage helpers for the ingestion pipeline (all take an open connection)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from app.db import (
    api_probes,
    data_quality_log,
    ingest_runs,
    insert_ignore,
    prints,
    raw_prints,
    symbols,
)
from app.validation import Rejection, ValidatedPrint, print_record


def _parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def store_raw(
    conn: Connection, rows: list[dict[str, Any]], *, ingested_at: datetime
) -> tuple[int, list[dict[str, Any]]]:
    """Store API rows verbatim. Returns (inserted_count, unstorable_rows).

    A row is unstorable only if it lacks the identity fields (ticker +
    executed_at) the table requires; those rows still get quality-logged by
    the caller. Duplicates are skipped silently (idempotent re-runs).
    """
    records: list[dict[str, Any]] = []
    unstorable: list[dict[str, Any]] = []
    for row in rows:
        executed_at = _parse_ts(row.get("executed_at"))
        ticker = row.get("ticker")
        if not ticker or executed_at is None:
            unstorable.append(row)
            continue
        records.append(
            {
                "ticker": ticker,
                "tracking_id": row.get("tracking_id"),
                "executed_at": executed_at,
                "payload": row,
                "ingested_at": ingested_at,
            }
        )
    inserted = insert_ignore(conn, raw_prints, records)
    return inserted, unstorable


def store_prints(
    conn: Connection,
    validated: list[ValidatedPrint],
    *,
    late_report_seconds: int,
    ingested_at: datetime,
) -> int:
    records = [
        print_record(vp, late_report_seconds=late_report_seconds, ingested_at=ingested_at)
        for vp in validated
    ]
    return insert_ignore(conn, prints, records)


def log_rejections(
    conn: Connection,
    rejections: list[Rejection],
    *,
    logged_at: datetime,
    stage_override: str | None = None,
) -> int:
    if not rejections:
        return 0
    rows = [
        {
            "ticker": rejection.row.get("ticker"),
            "tracking_id": rejection.row.get("tracking_id"),
            "executed_at": _parse_ts(rejection.row.get("executed_at")),
            "stage": stage_override or rejection.stage,
            "reasons": rejection.reasons,
            "payload": rejection.row,
            "logged_at": logged_at,
        }
        for rejection in rejections
    ]
    conn.execute(data_quality_log.insert(), rows)
    return len(rows)


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def upsert_symbols(conn: Connection, rows: list[dict[str, Any]], *, seen_at: datetime) -> int:
    """Refresh the symbols table from the freshest print per ticker."""
    freshest: dict[str, dict[str, Any]] = {}
    for row in rows:
        ticker = row.get("ticker")
        if not ticker:
            continue
        current = freshest.get(ticker)
        if current is None or (row.get("created_at") or "") > (current.get("created_at") or ""):
            freshest[ticker] = row

    touched = 0
    for ticker, row in freshest.items():
        values = {
            "sector": row.get("sector"),
            "issue_type": row.get("issue_type"),
            "avg30_volume": _to_decimal(row.get("avg30_volume")),
            "last_seen_at": seen_at,
        }
        updated = conn.execute(
            symbols.update().where(symbols.c.ticker == ticker).values(**values)
        ).rowcount
        if not updated:
            insert_ignore(
                conn, symbols, [{"ticker": ticker, "first_seen_at": seen_at, **values}]
            )
        touched += 1
    return touched


def store_probe(conn: Connection, probe: str, result: dict[str, Any], *, ran_at: datetime) -> None:
    conn.execute(api_probes.insert(), {"probe": probe, "ran_at": ran_at, "result": result})


def start_run(conn: Connection, run_date: date, *, started_at: datetime) -> int:
    result = conn.execute(
        ingest_runs.insert().values(run_date=run_date, started_at=started_at)
    )
    return int(result.inserted_primary_key[0])


def finish_run(
    conn: Connection, run_id: int, *, finished_at: datetime, stats: dict[str, Any]
) -> None:
    conn.execute(
        sa.update(ingest_runs)
        .where(ingest_runs.c.id == run_id)
        .values(finished_at=finished_at, stats=stats)
    )
