"""The M3 analysis pipeline: prints + candles (already in the DB) → zones,
evidence, verdicts, scores, and an immutable signal per ticker-day.

Runs entirely off stored data — no network. The optional provider
cross-check (plan §9, exit criterion) is the one exception and takes a
client explicitly.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import Connection, Engine

from app.analytics import zones as zone_lib
from app.analytics.inference import build_evidence, infer, invalidation_conditions
from app.analytics.scoring import (
    data_quality_score,
    dpss,
    print_significance,
    trade_relevance,
)
from app.config import Settings
from app.db import candles, insert_ignore, prints, signals, symbol_days
from app.db import zone_events as zone_events_table
from app.db import zones as zones_table


def _weekdays_back(end: date, count: int) -> date:
    current = end
    remaining = count
    while remaining > 0:
        current -= timedelta(days=1)
        if current.weekday() < 5:
            remaining -= 1
    return current


def _window_rows(conn: Connection, ticker: str, start: date, end: date) -> list[dict]:
    window_start = datetime.combine(start, time(0, 0), tzinfo=UTC)
    window_end = datetime.combine(end + timedelta(days=2), time(0, 0), tzinfo=UTC)
    rows = conn.execute(
        sa.select(prints).where(
            prints.c.ticker == ticker,
            prints.c.executed_at >= window_start,
            prints.c.executed_at < window_end,
        )
    ).mappings().all()
    return [dict(row) for row in rows]


def _daily_candles(conn: Connection, ticker: str, end: date, *, lookback_days: int) -> list[dict]:
    window_start = datetime.combine(
        end - timedelta(days=lookback_days * 2), time(0, 0), tzinfo=UTC
    )
    window_end = datetime.combine(end + timedelta(days=1), time(0, 0), tzinfo=UTC)
    rows = conn.execute(
        sa.select(candles).where(
            candles.c.ticker == ticker,
            candles.c.candle_size == "1d",
            candles.c.ts >= window_start,
            candles.c.ts < window_end,
        )
    ).mappings().all()
    return sorted((dict(row) for row in rows), key=lambda row: row["ts"])


def _zone_row(
    ticker: str, as_of: date, window_start: date, metrics: dict, status: dict,
    score: float, *, now: datetime,
) -> dict[str, Any]:
    return {
        "ticker": ticker,
        "as_of_date": as_of,
        "window_start": window_start,
        "window_end": as_of,
        "price_low": metrics["price_low"],
        "price_high": metrics["price_high"],
        "wavg_price": metrics["wavg_price"],
        "total_shares": metrics["total_shares"],
        "total_notional": metrics["total_notional"],
        "print_count": metrics["print_count"],
        "unique_days": metrics["unique_days"],
        "first_print_at": metrics["first_print_at"],
        "last_print_at": metrics["last_print_at"],
        "pct_adv30": metrics["pct_adv30"],
        "pct_dark_volume": metrics["pct_dark_volume"],
        "tightness_atr": metrics["tightness_atr"],
        "strength_score": score,
        "strength_class": zone_lib.strength_class(score),
        "status": status["status"],
        "respected_touches": status["respected_touches"],
        "created_at": now,
    }


def analyze_ticker_day(
    conn: Connection, ticker: str, as_of: date, settings: Settings, *, now: datetime
) -> dict[str, Any]:
    window_start = _weekdays_back(as_of, settings.zones.window_days)
    window_rows = _window_rows(conn, ticker, window_start, as_of)
    if not window_rows:
        return {"skipped": "no_prints"}

    context = conn.execute(
        sa.select(symbol_days).where(
            symbol_days.c.ticker == ticker, symbol_days.c.trading_date == as_of
        )
    ).mappings().first()
    atr = context["atr14"] if context else None
    daily = _daily_candles(
        conn, ticker, as_of, lookback_days=settings.enrichment.daily_history_days
    )
    current_close = float(daily[-1]["close"]) if daily else None

    # --- zones -----------------------------------------------------------
    eligible = zone_lib.eligible_prints(window_rows)
    window_total_shares = sum(row["size"] for row in eligible)
    zone_summaries: list[dict[str, Any]] = []

    # Zones are rebuilt deterministically each run: wipe this key first.
    old_ids = conn.execute(
        sa.select(zones_table.c.id).where(
            zones_table.c.ticker == ticker, zones_table.c.as_of_date == as_of
        )
    ).scalars().all()
    if old_ids:
        conn.execute(sa.delete(zone_events_table).where(
            zone_events_table.c.zone_id.in_(old_ids)
        ))
        conn.execute(sa.delete(zones_table).where(zones_table.c.id.in_(old_ids)))

    for cluster in zone_lib.cluster_prints(
        eligible, atr=atr, config=settings.zones.epsilon
    ):
        metrics = zone_lib.zone_metrics(
            cluster, as_of=as_of, atr=atr, window_total_shares=window_total_shares
        )
        status = zone_lib.track_zone_status(
            metrics, daily, atr=atr, config=settings.zones
        )
        score, components = zone_lib.strength_score(
            metrics, status, weights=settings.zones.strength_weights, config=settings.zones
        )
        row = _zone_row(ticker, as_of, window_start, metrics, status, score, now=now)
        zone_id = conn.execute(zones_table.insert().values(**row)).inserted_primary_key[0]
        if status["events"]:
            conn.execute(
                zone_events_table.insert(),
                [{"zone_id": zone_id, **event} for event in status["events"]],
            )
        zone_summaries.append(
            {**row, "id": zone_id, "metrics": metrics, "status_info": status,
             "strength_components": components, "cluster": cluster}
        )

    # --- inference + scores on the strongest zone ------------------------
    issue_type = window_rows[-1].get("issue_type")
    quality, quality_components = data_quality_score(
        window_rows,
        has_vwap=bool(context and context["session_vwap"] is not None),
        has_atr=atr is not None,
    )

    options_tilt = None
    if context and context.get("call_premium") is not None:
        options_tilt = {
            "call_premium": context["call_premium"],
            "put_premium": context["put_premium"],
        }

    if zone_summaries:
        top = max(zone_summaries, key=lambda z: z["strength_score"])
        evidence = build_evidence(
            top["metrics"], top["status_info"], daily,
            current_close=current_close, options_tilt=options_tilt,
        )
        verdict = infer(evidence, settings.inference)
        invalidation = invalidation_conditions(
            top["metrics"], verdict["classification"], atr=atr
        )
        print_score = max(
            print_significance(row, settings.scoring.print_significance_weights)
            for row in top["cluster"]
        )
        zone_score = top["strength_score"]
        relevance, relevance_components = trade_relevance(
            current_close=current_close,
            zone_wavg=float(top["metrics"]["wavg_price"]),
            atr=atr,
            sessions_since_last=top["metrics"]["sessions_since_last"],
            half_life_sessions=settings.zones.recency_half_life_sessions,
        )
        top_zone_snapshot = {
            "wavg_price": float(top["metrics"]["wavg_price"]),
            "price_low": float(top["metrics"]["price_low"]),
            "price_high": float(top["metrics"]["price_high"]),
            "strength_score": zone_score,
            "strength_class": top["strength_class"],
            "status": top["status"],
            "unique_days": top["metrics"]["unique_days"],
            "total_shares": top["metrics"]["total_shares"],
            "strength_components": top["strength_components"],
        }
    else:
        verdict = {
            "classification": "insufficient_evidence",
            "confidence": 0.0,
            "net_weight": 0,
            "groups": [],
            "supporting": [],
            "contradicting": [],
        }
        invalidation = []
        print_score = max(
            (
                print_significance(row, settings.scoring.print_significance_weights)
                for row in window_rows
            ),
            default=0.0,
        )
        zone_score, relevance, relevance_components = 0.0, 0.0, {}
        top_zone_snapshot = None

    direction_score = verdict["confidence"] * 100
    if issue_type in ("ETF", "Index"):
        # Probable portfolio flow: weak single-name signal (plan §11).
        direction_score *= settings.scoring.etf_discount

    total = dpss(
        print_score=print_score,
        zone_score=zone_score,
        direction_score=round(direction_score, 2),
        relevance_score=relevance,
        quality_score=quality,
        weights=settings.scoring.dpss_weights,
    )

    inserted = insert_ignore(
        conn,
        signals,
        [
            {
                "ticker": ticker,
                "as_of_date": as_of,
                "classification": verdict["classification"],
                "confidence": verdict["confidence"],
                "dpss": total,
                "sub_scores": {
                    "print": print_score,
                    "zone": zone_score,
                    "direction": round(direction_score, 2),
                    "relevance": relevance,
                    "relevance_components": relevance_components,
                    "quality": quality,
                    "quality_components": quality_components,
                },
                "evidence": {
                    "supporting": verdict["supporting"],
                    "contradicting": verdict["contradicting"],
                    "net_weight": verdict["net_weight"],
                    "groups": verdict["groups"],
                },
                "invalidation": invalidation,
                "top_zone": top_zone_snapshot,
                "available_at": now,
            }
        ],
    )
    return {
        "zones": len(zone_summaries),
        "classification": verdict["classification"],
        "confidence": verdict["confidence"],
        "dpss": total,
        "signal_inserted": bool(inserted),
    }


def analyze_day(
    engine: Engine, settings: Settings, as_of: date, *, now: datetime | None = None
) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    window_start = datetime.combine(as_of, time(0, 0), tzinfo=UTC)
    window_end = window_start + timedelta(days=2)
    with engine.connect() as conn:
        tickers = conn.execute(
            sa.select(prints.c.ticker)
            .where(prints.c.executed_at >= window_start, prints.c.executed_at < window_end)
            .distinct()
        ).scalars().all()

    per_ticker: dict[str, Any] = {}
    for ticker in sorted(tickers):
        with engine.begin() as conn:
            per_ticker[ticker] = analyze_ticker_day(conn, ticker, as_of, settings, now=now)

    return {
        "date": as_of.isoformat(),
        "tickers": len(per_ticker),
        "signals": sum(1 for t in per_ticker.values() if t.get("signal_inserted")),
        "per_ticker": per_ticker,
    }


def crosscheck_price_levels(
    our_total_shares: int, provider_levels: dict[str, Any], *, tolerance: float = 0.15
) -> dict[str, Any]:
    """Compare our stored dark volume against the provider's own aggregation.

    An independent sanity check (plan §9): large disagreement means we are
    missing prints or double-counting, and should be treated as a
    data-quality problem — not silently accepted.
    """
    rows = provider_levels.get("stock_price_vol") or []
    provider_total = sum(int(row.get("dark_pool_volume") or 0) for row in rows)
    if provider_total == 0:
        return {"comparable": False, "reason": "provider_reported_zero"}
    ratio = our_total_shares / provider_total
    return {
        "comparable": True,
        "our_total_shares": our_total_shares,
        "provider_total_shares": provider_total,
        "ratio": round(ratio, 4),
        "within_tolerance": abs(1 - ratio) <= tolerance,
        "tolerance": tolerance,
    }
