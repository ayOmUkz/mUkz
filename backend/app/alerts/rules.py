"""Alert rules evaluated after the nightly analyze run (plan §14).

Dedup and cooldowns are database-backed: every alert has a stable
``base_key`` (rule : ticker : subject), and a rule stays silent while an
alert with the same key exists inside the cooldown window. At nightly
cadence this replaces the Redis SETNX design from the plan — Redis joins
in with the intraday upgrade (M7), where sub-day cooldowns matter.

A per-symbol daily cap keeps one busy ticker from drowning the digest.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from app.config import Settings
from app.db import alerts as alerts_table
from app.db import candles, prints, signals
from app.db import zones as zones_table


def _json(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else (value or [])


def _existing_within_cooldown(
    conn: Connection, base_key: str, *, now: datetime, cooldown_hours: int
) -> bool:
    cutoff = now - timedelta(hours=cooldown_hours)
    found = conn.execute(
        sa.select(alerts_table.c.id)
        .where(alerts_table.c.base_key == base_key, alerts_table.c.created_at > cutoff)
        .limit(1)
    ).first()
    return found is not None


def _emit(
    conn: Connection,
    pending: list[dict[str, Any]],
    *,
    as_of: date,
    now: datetime,
    settings: Settings,
) -> list[dict[str, Any]]:
    """Apply cooldown + per-symbol cap, insert survivors, return them."""
    emitted: list[dict[str, Any]] = []
    per_symbol: dict[str, int] = {}
    cap = settings.alerts.max_alerts_per_symbol_per_day
    for alert in pending:
        if per_symbol.get(alert["ticker"], 0) >= cap:
            continue
        if _existing_within_cooldown(
            conn, alert["base_key"], now=now, cooldown_hours=settings.alerts.cooldown_hours
        ):
            continue
        conn.execute(
            alerts_table.insert().values(
                rule=alert["rule"],
                ticker=alert["ticker"],
                as_of_date=as_of,
                base_key=alert["base_key"],
                payload=alert["payload"],
                created_at=now,
                delivered=["dashboard"],
            )
        )
        per_symbol[alert["ticker"]] = per_symbol.get(alert["ticker"], 0) + 1
        emitted.append(alert)
    return emitted


def evaluate_alerts(
    conn: Connection, as_of: date, settings: Settings, *, now: datetime | None = None
) -> list[dict[str, Any]]:
    """Evaluate every rule for one session; returns the alerts actually emitted."""
    now = now or datetime.now(UTC)
    day_start = datetime.combine(as_of, time(0, 0), tzinfo=UTC)
    day_end = day_start + timedelta(days=2)
    pending: list[dict[str, Any]] = []

    # --- new extreme prints ---------------------------------------------
    extreme = conn.execute(
        sa.select(prints).where(
            prints.c.executed_at >= day_start,
            prints.c.executed_at < day_end,
            prints.c.size_class == "extreme",
        )
    ).mappings().all()
    for row in extreme:
        pending.append(
            {
                "rule": "extreme_print",
                "ticker": row["ticker"],
                "base_key": f"extreme_print:{row['ticker']}:{row['tracking_id']}",
                "payload": {
                    "size": row["size"],
                    "premium": float(row["premium"]),
                    "price": float(row["price"]),
                    "character": row["character"],
                    "executed_at": row["executed_at"].isoformat(),
                },
            }
        )

    # --- zone-level rules ------------------------------------------------
    zone_rows = conn.execute(
        sa.select(zones_table).where(zones_table.c.as_of_date == as_of)
    ).mappings().all()
    for zone in zone_rows:
        wavg = float(zone["wavg_price"])
        zone_key = f"{zone['ticker']}:{wavg:.2f}"
        if zone["unique_days"] >= 3 and zone["strength_score"] >= 60:
            pending.append(
                {
                    "rule": "repeated_prints_zone",
                    "ticker": zone["ticker"],
                    "base_key": f"repeated_prints_zone:{zone_key}",
                    "payload": {
                        "zone": wavg,
                        "unique_days": zone["unique_days"],
                        "strength": zone["strength_score"],
                    },
                }
            )
        if float(zone["total_notional"]) >= settings.alerts.min_zone_notional:
            pending.append(
                {
                    "rule": "zone_notional_threshold",
                    "ticker": zone["ticker"],
                    "base_key": f"zone_notional_threshold:{zone_key}",
                    "payload": {
                        "zone": wavg,
                        "total_notional": float(zone["total_notional"]),
                    },
                }
            )
        if zone["status"] in ("reclaimed", "broken"):
            pending.append(
                {
                    "rule": f"zone_{zone['status']}",
                    "ticker": zone["ticker"],
                    "base_key": f"zone_{zone['status']}:{zone_key}",
                    "payload": {"zone": wavg, "strength": zone["strength_score"]},
                }
            )

    # --- directional signals ---------------------------------------------
    signal_rows = conn.execute(
        sa.select(signals).where(signals.c.as_of_date == as_of)
    ).mappings().all()
    for row in signal_rows:
        if (
            row["classification"].startswith(("probable", "possible"))
            and row["dpss"] >= settings.alerts.min_dpss
        ):
            pending.append(
                {
                    "rule": "directional_signal",
                    "ticker": row["ticker"],
                    "base_key": f"directional_signal:{row['ticker']}:{row['classification']}",
                    "payload": {
                        "classification": row["classification"],
                        "confidence": row["confidence"],
                        "dpss": row["dpss"],
                    },
                }
            )

    # --- invalidation of earlier directional signals ---------------------
    closes = {
        row.ticker: float(row.close)
        for row in conn.execute(
            sa.select(candles.c.ticker, candles.c.close).where(
                candles.c.candle_size == "1d",
                candles.c.ts >= day_start,
                candles.c.ts < day_start + timedelta(days=1),
            )
        )
    }
    prior = conn.execute(
        sa.select(signals).where(
            signals.c.as_of_date < as_of,
            signals.c.as_of_date >= as_of - timedelta(days=14),
        )
    ).mappings().all()
    latest_prior: dict[str, dict] = {}
    for row in sorted(prior, key=lambda r: r["as_of_date"]):
        latest_prior[row["ticker"]] = dict(row)
    for ticker, row in latest_prior.items():
        if not row["classification"].startswith(("probable", "possible")):
            continue
        close = closes.get(ticker)
        if close is None:
            continue
        for condition in _json(row["invalidation"]):
            level = condition.get("level")
            if level is None:
                continue
            hit = (condition["type"] == "daily_close_below" and close < level) or (
                condition["type"] == "daily_close_above" and close > level
            )
            if hit:
                pending.append(
                    {
                        "rule": "signal_invalidated",
                        "ticker": ticker,
                        "base_key": (
                            f"signal_invalidated:{ticker}:{row['as_of_date'].isoformat()}"
                        ),
                        "payload": {
                            "signal_date": row["as_of_date"].isoformat(),
                            "classification": row["classification"],
                            "condition": condition,
                            "close": close,
                        },
                    }
                )
                break

    # --- stale directional signals ---------------------------------------
    today_tickers = {row["ticker"] for row in signal_rows}
    stale_cutoff = as_of - timedelta(days=settings.alerts.stale_sessions + 2)
    for ticker, row in latest_prior.items():
        if ticker in today_tickers:
            continue
        if not row["classification"].startswith(("probable", "possible")):
            continue
        if row["as_of_date"] <= stale_cutoff:
            pending.append(
                {
                    "rule": "stale_signal",
                    "ticker": ticker,
                    "base_key": f"stale_signal:{ticker}:{row['as_of_date'].isoformat()}",
                    "payload": {
                        "signal_date": row["as_of_date"].isoformat(),
                        "classification": row["classification"],
                        "note": "no fresh dark-pool evidence since",
                    },
                }
            )

    return _emit(conn, pending, as_of=as_of, now=now, settings=settings)
