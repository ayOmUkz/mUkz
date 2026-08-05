"""FastAPI service.

M0: health. M2: the classified dark-pool tape. M4: scanner categories,
the alert feed, and the per-ticker Phase-12 report. The dashboard that
consumes these arrives with M5 — see docs/PLAN.md §15/§19.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from functools import lru_cache
from typing import Annotated, Any

import sqlalchemy as sa
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.engine import Engine

from app.config import Settings, load_settings
from app.db import alerts as alerts_table
from app.db import make_engine, prints, signals
from app.reports import build_ticker_report
from app.scanner import scan

app = FastAPI(title="Dark Pool Intelligence Engine", version="0.4.0")

#: Tape columns, in display order (plan §15 "Dark-pool tape").
TAPE_COLUMNS = (
    "executed_at",
    "created_at",
    "report_delay_s",
    "ticker",
    "price",
    "size",
    "premium",
    "sale_cond_codes",
    "trade_code",
    "nbbo_bid",
    "nbbo_ask",
    "mid",
    "location_bucket",
    "location_confidence",
    "vwap_position",
    "timing_bucket",
    "size_class",
    "size_percentile",
    "size_confidence",
    "character",
    "quality_flags",
)


@lru_cache
def get_engine() -> Engine:
    from app.config import Secrets

    return make_engine(Secrets().database_url)


@lru_cache
def get_settings() -> Settings:
    return load_settings()


def _latest_signal_date(engine: Engine) -> date | None:
    with engine.connect() as conn:
        value = conn.execute(sa.select(sa.func.max(signals.c.as_of_date))).scalar()
    if value is None or isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/tape")
def tape(
    ticker: Annotated[str, Query(min_length=1, max_length=24)],
    engine: Annotated[Engine, Depends(get_engine)],
    trading_date: Annotated[date | None, Query(alias="date")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> dict[str, Any]:
    """The dark-pool tape for one symbol: validated prints, newest first."""
    conditions = [prints.c.ticker == ticker.upper()]
    if trading_date is not None:
        start = datetime.combine(trading_date, time(0, 0), tzinfo=UTC)
        conditions.append(prints.c.executed_at >= start)
        conditions.append(prints.c.executed_at < start + timedelta(days=2))
    columns = [prints.c[name] for name in TAPE_COLUMNS]
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                sa.select(*columns)
                .where(*conditions)
                .order_by(prints.c.executed_at.desc())
                .limit(limit)
            ).mappings().all()
    except sa.exc.OperationalError as exc:  # e.g. schema not created yet
        raise HTTPException(status_code=503, detail="database not ready") from exc
    return {
        "ticker": ticker.upper(),
        "count": len(rows),
        "prints": [{key: _jsonable(value) for key, value in row.items()} for row in rows],
    }


@app.get("/scan")
def scan_endpoint(
    engine: Annotated[Engine, Depends(get_engine)],
    settings: Annotated[Settings, Depends(get_settings)],
    trading_date: Annotated[date | None, Query(alias="date")] = None,
) -> dict[str, Any]:
    """The ten scanner categories for a session (default: latest analyzed)."""
    as_of = trading_date or _latest_signal_date(engine)
    if as_of is None:
        raise HTTPException(status_code=404, detail="no analyzed sessions yet")
    with engine.connect() as conn:
        return scan(conn, as_of, settings)


@app.get("/alerts")
def alerts_endpoint(
    engine: Annotated[Engine, Depends(get_engine)],
    trading_date: Annotated[date | None, Query(alias="date")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> dict[str, Any]:
    """The alert feed, newest first."""
    conditions = []
    if trading_date is not None:
        conditions.append(alerts_table.c.as_of_date == trading_date)
    with engine.connect() as conn:
        rows = conn.execute(
            sa.select(alerts_table)
            .where(*conditions)
            .order_by(alerts_table.c.created_at.desc(), alerts_table.c.id.desc())
            .limit(limit)
        ).mappings().all()
    alerts = []
    for row in rows:
        payload = row["payload"]
        alerts.append(
            {
                "rule": row["rule"],
                "ticker": row["ticker"],
                "as_of": row["as_of_date"].isoformat(),
                "payload": json.loads(payload) if isinstance(payload, str) else payload,
                "created_at": _jsonable(row["created_at"]),
            }
        )
    return {"count": len(alerts), "alerts": alerts}


@app.get("/report/{ticker}")
def report_endpoint(
    ticker: str,
    engine: Annotated[Engine, Depends(get_engine)],
    settings: Annotated[Settings, Depends(get_settings)],
    trading_date: Annotated[date | None, Query(alias="date")] = None,
) -> dict[str, Any]:
    """The per-ticker Phase-12 report as JSON."""
    as_of = trading_date or _latest_signal_date(engine)
    if as_of is None:
        raise HTTPException(status_code=404, detail="no analyzed sessions yet")
    with engine.connect() as conn:
        report = build_ticker_report(conn, ticker.upper(), as_of, settings)
    if report is None:
        raise HTTPException(
            status_code=404,
            detail=f"no signal for {ticker.upper()} on {as_of.isoformat()}",
        )
    return report
