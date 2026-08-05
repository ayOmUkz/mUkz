"""The event-study engine (plan §16). Honesty rules, enforced in code:

* Events come from the **immutable** ``signals`` table — we replay exactly
  what was written on the night it was written, never a recomputation.
* Entry is the **next session's open** after the signal date. The signal
  day's own move can never be credited (the classic look-ahead trap; the
  test suite plants one and asserts we don't profit from it).
* One active event per (ticker, direction): a new signal inside the
  previous event's evaluation window is flagged ``overlapping`` and kept
  out of headline cohorts, so one long episode can't count five times.
* In EOD mode only daily horizons exist. Intraday horizons (5m/15m/…)
  need intraday ingestion (M7) and are not fabricated from daily bars.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import Connection, Engine

from app.analytics.context import SECTOR_ETFS, trend_from_daily
from app.analytics.zones import sessions_between
from app.backtest.stats import aggregate_cohorts
from app.config import Settings
from app.db import (
    backtest_events,
    backtest_results,
    backtest_runs,
    candles,
    signals,
    symbol_days,
    symbols,
)

DIRECTIONAL_PREFIXES = ("probable", "possible")


def _json(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def collect_events(
    conn: Connection,
    *,
    start: date | None = None,
    end: date | None = None,
    max_horizon: int,
) -> list[dict[str, Any]]:
    """Directional signals as events, oldest first, with overlap control."""
    conditions = [signals.c.classification.like("probable%")
                  | signals.c.classification.like("possible%")]
    if start is not None:
        conditions.append(signals.c.as_of_date >= start)
    if end is not None:
        conditions.append(signals.c.as_of_date <= end)
    rows = conn.execute(
        sa.select(signals).where(*conditions).order_by(signals.c.as_of_date)
    ).mappings().all()

    events: list[dict[str, Any]] = []
    active_until: dict[tuple[str, int], date] = {}
    for row in rows:
        direction = 1 if row["classification"].endswith("accumulation") else -1
        key = (row["ticker"], direction)
        previous = active_until.get(key)
        overlapping = previous is not None and sessions_between(
            previous, row["as_of_date"]
        ) < max_horizon
        if not overlapping:
            active_until[key] = row["as_of_date"]
        top_zone = _json(row["top_zone"]) or {}
        events.append(
            {
                "ticker": row["ticker"],
                "signal_date": row["as_of_date"],
                "direction": direction,
                "classification": row["classification"],
                "confidence": row["confidence"],
                "dpss": row["dpss"],
                "invalidation": _json(row["invalidation"]) or [],
                "unique_days": top_zone.get("unique_days", 0),
                "overlapping": overlapping,
            }
        )
    return events


def load_series(conn: Connection, ticker: str) -> list[dict[str, Any]]:
    """All stored daily bars for one ticker, oldest first."""
    rows = conn.execute(
        sa.select(candles).where(
            candles.c.ticker == ticker, candles.c.candle_size == "1d"
        ).order_by(candles.c.ts)
    ).mappings().all()
    return [
        {
            "date": row["ts"].date(),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
        }
        for row in rows
    ]


def _benchmark_return(
    by_date: dict[date, dict[str, Any]], entry_date: date, exit_date: date
) -> float | None:
    entry_bar, exit_bar = by_date.get(entry_date), by_date.get(exit_date)
    if entry_bar is None or exit_bar is None or entry_bar["open"] <= 0:
        return None
    return exit_bar["close"] / entry_bar["open"] - 1


def measure_event(
    event: dict[str, Any],
    series: list[dict[str, Any]],
    *,
    horizons: list[int],
    spy_by_date: dict[date, dict[str, Any]] | None = None,
    sector_by_date: dict[date, dict[str, Any]] | None = None,
    atr: float | None = None,
) -> dict[str, Any]:
    """Attach entry, per-horizon returns, MFE/MAE and invalidation info."""
    measured = dict(event)
    direction = event["direction"]
    window = [bar for bar in series if bar["date"] > event["signal_date"]]
    if not window:
        measured.update({"unmeasurable": "no_entry_session"})
        return measured
    entry_bar = window[0]
    entry = entry_bar["open"]
    if entry <= 0:
        measured.update({"unmeasurable": "bad_entry_price"})
        return measured
    max_horizon = horizons[-1]
    window = window[:max_horizon]

    invalidated_at: int | None = None
    for index, bar in enumerate(window, start=1):
        for condition in event.get("invalidation", []):
            level = condition.get("level")
            if level is None:
                continue
            hit = (
                condition.get("type") == "daily_close_below" and bar["close"] < level
            ) or (condition.get("type") == "daily_close_above" and bar["close"] > level)
            if hit:
                invalidated_at = index
                break
        if invalidated_at is not None:
            break

    returns: dict[str, dict[str, float | None]] = {}
    for horizon in horizons:
        if len(window) < horizon:
            continue
        exit_bar = window[horizon - 1]
        raw = direction * (exit_bar["close"] / entry - 1)
        market_adj = None
        if spy_by_date is not None:
            bench = _benchmark_return(spy_by_date, entry_bar["date"], exit_bar["date"])
            if bench is not None:
                market_adj = raw - direction * bench
        sector_adj = None
        if sector_by_date:
            bench = _benchmark_return(sector_by_date, entry_bar["date"], exit_bar["date"])
            if bench is not None:
                sector_adj = raw - direction * bench
        vol_adj = None
        if atr and atr > 0:
            vol_adj = raw / (atr / entry)
        returns[str(horizon)] = {
            "raw": raw,
            "market_adj": market_adj,
            "sector_adj": sector_adj,
            "vol_adj": vol_adj,
        }

    favorable = max(
        direction * ((bar["high"] if direction > 0 else bar["low"]) / entry - 1)
        for bar in window
    )
    adverse = min(
        direction * ((bar["low"] if direction > 0 else bar["high"]) / entry - 1)
        for bar in window
    )
    measured.update(
        {
            "unmeasurable": None,
            "entry_date": entry_bar["date"],
            "entry_price": entry,
            "returns": returns,
            "mfe": favorable,
            "mae": adverse,
            "invalidated_at_session": invalidated_at,
        }
    )
    return measured


def _spy_regime_by_date(spy_series: list[dict[str, Any]]) -> dict[date, str | None]:
    """SPY trend as of each date, using only bars up to that date."""
    regimes: dict[date, str | None] = {}
    bars: list[dict[str, Any]] = []
    for bar in spy_series:
        bars.append({"ts": bar["date"], "close": bar["close"]})
        regimes[bar["date"]] = trend_from_daily(
            [{"ts": b["ts"], "close": b["close"]} for b in bars]
        )
    return regimes


def _segments(event: dict[str, Any], *, issue_type: str | None, sector: str | None,
              regime: str | None) -> dict[str, str]:
    return {
        "classification": event["classification"],
        "side": "accumulation" if event["direction"] > 0 else "distribution",
        "instrument": "etf" if issue_type in ("ETF", "Index") else "stock",
        "sector": sector or "unknown",
        "recurrence": "repeated_zone" if event.get("unique_days", 0) >= 3 else "single_burst",
        "dpss_band": "dpss>=60" if event["dpss"] >= 60 else "dpss<60",
        "regime": f"spy_{regime}" if regime else "spy_unknown",
    }


def run_backtest(
    engine: Engine,
    settings: Settings,
    *,
    start: date | None = None,
    end: date | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Collect, measure, aggregate, persist. Returns the run summary."""
    now = now or datetime.now(UTC)
    cfg = settings.backtest
    config_payload = {
        "horizons": cfg.horizons,
        "entry": "next_session_open",
        "bootstrap_samples": cfg.bootstrap_samples,
        "seed": cfg.seed,
        "min_cohort_n": cfg.min_cohort_n,
    }
    config_hash = hashlib.sha256(
        json.dumps(config_payload, sort_keys=True).encode()
    ).hexdigest()[:12]

    with engine.connect() as conn:
        events = collect_events(conn, start=start, end=end, max_horizon=cfg.max_horizon)
        spy_series = load_series(conn, "SPY")
        spy_by_date = {bar["date"]: bar for bar in spy_series}
        regimes = _spy_regime_by_date(spy_series)
        symbol_meta = {
            row["ticker"]: dict(row)
            for row in conn.execute(sa.select(symbols)).mappings()
        }
        series_cache: dict[str, list[dict[str, Any]]] = {}
        sector_cache: dict[str, dict[date, dict[str, Any]]] = {}
        measured: list[dict[str, Any]] = []
        for event in events:
            ticker = event["ticker"]
            if ticker not in series_cache:
                series_cache[ticker] = load_series(conn, ticker)
            meta = symbol_meta.get(ticker, {})
            sector = meta.get("sector")
            sector_etf = SECTOR_ETFS.get(sector or "")
            if sector_etf and sector_etf not in sector_cache:
                sector_cache[sector_etf] = {
                    bar["date"]: bar for bar in load_series(conn, sector_etf)
                }
            atr_row = conn.execute(
                sa.select(symbol_days.c.atr14).where(
                    symbol_days.c.ticker == ticker,
                    symbol_days.c.trading_date == event["signal_date"],
                )
            ).scalar()
            result = measure_event(
                event,
                series_cache[ticker],
                horizons=cfg.horizons,
                spy_by_date=spy_by_date or None,
                sector_by_date=sector_cache.get(sector_etf or ""),
                atr=atr_row,
            )
            result["segments"] = _segments(
                result,
                issue_type=meta.get("issue_type"),
                sector=sector,
                regime=regimes.get(event["signal_date"]),
            )
            measured.append(result)

    results, nulls = aggregate_cohorts(
        measured,
        horizons=cfg.horizons,
        min_n=cfg.min_cohort_n,
        bootstrap_samples=cfg.bootstrap_samples,
        seed=cfg.seed,
    )

    headline = [event for event in measured
                if not event["overlapping"] and event.get("unmeasurable") is None]
    summary = {
        "events_total": len(measured),
        "events_headline": len(headline),
        "events_overlapping": sum(1 for e in measured if e["overlapping"]),
        "events_unmeasurable": sum(
            1 for e in measured if e.get("unmeasurable") is not None
        ),
        "cohorts": len({row["cohort"] for row in results}),
        "no_edge_cohorts": nulls,
        "notes": [
            "entry is the next session's open after the signal date — the "
            "signal day's own move is never credited",
            "intraday horizons (5m/15m/30m/1h) require intraday ingestion "
            "(M7) and are not fabricated from daily bars",
            "sector-adjusted returns exist only where the sector ETF's "
            "candles are stored",
            "history depth is bounded by the API's per-ticker history and "
            "what has been ingested — disclosed, not hidden",
        ],
    }

    with engine.begin() as conn:
        run_id = int(
            conn.execute(
                backtest_runs.insert().values(
                    created_at=now,
                    start_date=start,
                    end_date=end,
                    config=config_payload,
                    config_hash=config_hash,
                    summary=summary,
                )
            ).inserted_primary_key[0]
        )
        if measured:
            conn.execute(
                backtest_events.insert(),
                [
                    {
                        "run_id": run_id,
                        "ticker": e["ticker"],
                        "signal_date": e["signal_date"],
                        "direction": e["direction"],
                        "classification": e["classification"],
                        "confidence": e["confidence"],
                        "dpss": e["dpss"],
                        "overlapping": e["overlapping"],
                        "unmeasurable": e.get("unmeasurable"),
                        "entry_date": e.get("entry_date"),
                        "entry_price": e.get("entry_price"),
                        "returns": e.get("returns"),
                        "mfe": e.get("mfe"),
                        "mae": e.get("mae"),
                        "invalidated_at_session": e.get("invalidated_at_session"),
                        "segments": e["segments"],
                    }
                    for e in measured
                ],
            )
        if results:
            conn.execute(
                backtest_results.insert(),
                [{"run_id": run_id, **row} for row in results],
            )

    return {"run_id": run_id, "config_hash": config_hash, "summary": summary,
            "results": results}


def signal_date_range(engine: Engine) -> tuple[date | None, date | None]:
    with engine.connect() as conn:
        row = conn.execute(
            sa.select(
                sa.func.min(signals.c.as_of_date), sa.func.max(signals.c.as_of_date)
            )
        ).one()
    first, last = row

    def _coerce(value: Any) -> date | None:
        if value is None or isinstance(value, date):
            return value
        return date.fromisoformat(str(value))

    return _coerce(first), _coerce(last)
