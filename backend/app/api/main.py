"""FastAPI service.

M0 gave it a health endpoint; M2 adds the dark-pool tape (the milestone's
exit criterion: classified prints are queryable). The full dashboard API
arrives with M5 — see docs/PLAN.md §15/§19.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from functools import lru_cache
from typing import Annotated, Any

import sqlalchemy as sa
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.engine import Engine

from app.db import make_engine, prints

app = FastAPI(title="Dark Pool Intelligence Engine", version="0.2.0")

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
