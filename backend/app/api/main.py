"""FastAPI service.

M0: health. M2: the classified dark-pool tape. M4: scanner categories,
the alert feed, and the per-ticker Phase-12 report. M5: the status and
symbol-detail endpoints the Next.js dashboard consumes, plus CORS for it.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from functools import lru_cache
from typing import Annotated, Any

import sqlalchemy as sa
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.engine import Engine

from app.analytics.context import load_daily
from app.config import Settings, load_settings
from app.db import alerts as alerts_table
from app.db import data_quality_log, ingest_runs, make_engine, prints, signals, symbol_days
from app.db import zones as zones_table
from app.reports import build_ticker_report
from app.scanner import scan

app = FastAPI(title="Dark Pool Intelligence Engine", version="0.5.0")

# The dashboard runs on another origin (localhost:3000 in the default
# docker-compose). The UW API token never travels through here — the
# browser only ever talks to this service.
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["GET"],
    allow_headers=["*"],
)

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


@app.get("/status")
def status_endpoint(engine: Annotated[Engine, Depends(get_engine)]) -> dict[str, Any]:
    """Data-quality banner: last run, quarantine count, table counts."""
    with engine.connect() as conn:
        run = conn.execute(
            sa.select(ingest_runs).order_by(ingest_runs.c.id.desc()).limit(1)
        ).mappings().first()
        counts = {
            "prints": conn.execute(
                sa.select(sa.func.count()).select_from(prints)
            ).scalar(),
            "quarantined": conn.execute(
                sa.select(sa.func.count()).select_from(data_quality_log)
            ).scalar(),
            "zones": conn.execute(
                sa.select(sa.func.count()).select_from(zones_table)
            ).scalar(),
            "signals": conn.execute(
                sa.select(sa.func.count()).select_from(signals)
            ).scalar(),
            "alerts": conn.execute(
                sa.select(sa.func.count()).select_from(alerts_table)
            ).scalar(),
        }
    last_run = None
    if run is not None:
        stats = run["stats"]
        last_run = {
            "date": _jsonable(run["run_date"]) if not isinstance(run["run_date"], date)
            else run["run_date"].isoformat(),
            "started_at": _jsonable(run["started_at"]),
            "finished_at": _jsonable(run["finished_at"]),
            "stats": json.loads(stats) if isinstance(stats, str) else stats,
        }
    latest = _latest_signal_date(engine)
    return {
        "last_run": last_run,
        "latest_signal_date": latest.isoformat() if latest else None,
        "counts": counts,
    }


@app.get("/symbol/{ticker}")
def symbol_endpoint(
    ticker: str,
    engine: Annotated[Engine, Depends(get_engine)],
    trading_date: Annotated[date | None, Query(alias="date")] = None,
) -> dict[str, Any]:
    """Everything the symbol-detail chart needs: candles, zones, prints."""
    symbol = ticker.upper()
    as_of = trading_date or _latest_signal_date(engine)
    if as_of is None:
        raise HTTPException(status_code=404, detail="no analyzed sessions yet")
    day_start = datetime.combine(as_of, time(0, 0), tzinfo=UTC)
    day_end = day_start + timedelta(days=2)
    with engine.connect() as conn:
        daily = load_daily(conn, symbol, as_of)
        day_row = conn.execute(
            sa.select(symbol_days).where(
                symbol_days.c.ticker == symbol, symbol_days.c.trading_date == as_of
            )
        ).mappings().first()
        zone_rows = conn.execute(
            sa.select(zones_table)
            .where(zones_table.c.ticker == symbol, zones_table.c.as_of_date == as_of)
            .order_by(zones_table.c.strength_score.desc())
        ).mappings().all()
        print_rows = conn.execute(
            sa.select(
                prints.c.executed_at, prints.c.price, prints.c.size,
                prints.c.size_class, prints.c.size_percentile, prints.c.premium,
            ).where(
                prints.c.ticker == symbol,
                prints.c.executed_at >= day_start,
                prints.c.executed_at < day_end,
            ).order_by(prints.c.executed_at)
        ).mappings().all()
        signal = conn.execute(
            sa.select(signals).where(
                signals.c.ticker == symbol, signals.c.as_of_date == as_of
            )
        ).mappings().first()

    if not daily and not zone_rows and not print_rows:
        raise HTTPException(status_code=404, detail=f"nothing stored for {symbol}")

    invalidation: list[dict[str, Any]] = []
    signal_summary = None
    if signal is not None:
        raw = signal["invalidation"]
        invalidation = json.loads(raw) if isinstance(raw, str) else (raw or [])
        signal_summary = {
            "classification": signal["classification"],
            "confidence": signal["confidence"],
            "dpss": signal["dpss"],
        }
    return {
        "ticker": symbol,
        "date": as_of.isoformat(),
        "candles": [
            {
                "time": row["ts"].date().isoformat(),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
            }
            for row in daily
        ],
        "vwap": float(day_row["session_vwap"]) if day_row and day_row["session_vwap"]
        else None,
        "atr": day_row["atr14"] if day_row else None,
        "zones": [
            {
                "low": float(row["price_low"]),
                "high": float(row["price_high"]),
                "wavg": float(row["wavg_price"]),
                "strength_score": row["strength_score"],
                "strength_class": row["strength_class"],
                "status": row["status"],
                "unique_days": row["unique_days"],
                "total_shares": row["total_shares"],
            }
            for row in zone_rows
        ],
        "prints": [
            {
                "executed_at": _jsonable(row["executed_at"]),
                "session": _as_session_date(row["executed_at"]),
                "price": float(row["price"]),
                "size": row["size"],
                "size_class": row["size_class"],
                "size_percentile": row["size_percentile"],
                "premium": float(row["premium"]),
            }
            for row in print_rows
        ],
        "invalidation": invalidation,
        "signal": signal_summary,
    }


def _as_session_date(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.date().isoformat()
