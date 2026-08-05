"""The ten default scanner categories (plan §13).

Every result row carries a plain-English ``why`` string assembled from the
same stored evidence the dashboard shows — a symbol never ranks without
being able to explain itself. Category 7 (options-confirmed) is present
but stays empty until options context (evidence group D) is wired in; an
empty category is honest, a guessed one is not.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from app.analytics.context import market_context
from app.config import Settings
from app.db import candles, prints, signals, symbol_days
from app.db import zone_events as zone_events_table
from app.db import zones as zones_table

CATEGORIES = (
    "fresh_institutional_activity",
    "repeated_accumulation_zones",
    "repeated_distribution_zones",
    "zone_reclaims",
    "zone_rejections",
    "unusual_single_prints",
    "options_confirmed",       # activates when evidence group D lands
    "price_conflict",
    "levels_likely_to_matter",
    "approaching_historical_levels",
)


def _json(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else (value or {})


def _day_window(as_of: date) -> tuple[datetime, datetime]:
    start = datetime.combine(as_of, time(0, 0), tzinfo=UTC)
    return start, start + timedelta(days=2)


def _closes_and_atr(conn: Connection, as_of: date) -> dict[str, dict[str, float | None]]:
    """Latest close + ATR per ticker (from stored candles / symbol_days)."""
    window_start = datetime.combine(as_of - timedelta(days=10), time(0, 0), tzinfo=UTC)
    window_end = datetime.combine(as_of + timedelta(days=1), time(0, 0), tzinfo=UTC)
    out: dict[str, dict[str, float | None]] = {}
    rows = conn.execute(
        sa.select(candles.c.ticker, candles.c.ts, candles.c.close)
        .where(
            candles.c.candle_size == "1d",
            candles.c.ts >= window_start,
            candles.c.ts < window_end,
        )
        .order_by(candles.c.ts)
    ).all()
    for ticker, _ts, close in rows:  # later rows overwrite: last close wins
        out.setdefault(ticker, {})["close"] = float(close)
    atr_rows = conn.execute(
        sa.select(symbol_days.c.ticker, symbol_days.c.atr14).where(
            symbol_days.c.trading_date == as_of
        )
    ).all()
    for ticker, atr in atr_rows:
        out.setdefault(ticker, {})["atr"] = atr
    return out


def scan(conn: Connection, as_of: date, settings: Settings) -> dict[str, Any]:
    """Run all categories for one session. Pure read — no writes."""
    cfg = settings.scanner
    limit = cfg.limit_per_category
    day_start, day_end = _day_window(as_of)
    price_context = _closes_and_atr(conn, as_of)

    signal_rows = [
        dict(row)
        for row in conn.execute(
            sa.select(signals).where(signals.c.as_of_date == as_of)
        ).mappings()
    ]
    for row in signal_rows:
        row["sub_scores"] = _json(row["sub_scores"])
        row["evidence"] = _json(row["evidence"])
        row["top_zone"] = _json(row["top_zone"]) if row["top_zone"] else None

    zone_rows = [
        dict(row)
        for row in conn.execute(
            sa.select(zones_table).where(zones_table.c.as_of_date == as_of)
        ).mappings()
    ]

    def why_from_signal(row: dict[str, Any]) -> str:
        parts = [f"DPSS {row['dpss']}", row["classification"].replace("_", " ")]
        supporting = row["evidence"].get("supporting", [])
        contradicting = row["evidence"].get("contradicting", [])
        strongest = max(
            supporting + contradicting, key=lambda item: item["weight"], default=None
        )
        if strongest:
            parts.append(strongest["description"])
        return "; ".join(parts)

    results: dict[str, list[dict[str, Any]]] = {name: [] for name in CATEGORIES}

    # 1. Fresh institutional activity ------------------------------------
    fresh = [row for row in signal_rows if row["dpss"] >= cfg.min_dpss]
    results["fresh_institutional_activity"] = [
        {
            "ticker": row["ticker"],
            "dpss": row["dpss"],
            "classification": row["classification"],
            "why": why_from_signal(row),
        }
        for row in sorted(fresh, key=lambda r: -r["dpss"])[:limit]
    ]

    # 2 & 3. Repeated accumulation / distribution zones ------------------
    for name, suffix in (
        ("repeated_accumulation_zones", "accumulation"),
        ("repeated_distribution_zones", "distribution"),
    ):
        matches = [
            row
            for row in signal_rows
            if row["classification"].endswith(suffix)
            and (row["top_zone"] or {}).get("unique_days", 0) >= 3
        ]
        results[name] = [
            {
                "ticker": row["ticker"],
                "dpss": row["dpss"],
                "confidence": row["confidence"],
                "zone": row["top_zone"]["wavg_price"],
                "why": (
                    f"{row['classification'].replace('_', ' ')} — prints on "
                    f"{row['top_zone']['unique_days']} sessions around "
                    f"{row['top_zone']['wavg_price']:.2f}; {why_from_signal(row)}"
                ),
            }
            for row in sorted(matches, key=lambda r: -r["dpss"])[:limit]
        ]

    # 4 & 5. Reclaims / rejections on strong+ zones ----------------------
    strong_ids = {
        row["id"]: row
        for row in zone_rows
        if row["strength_score"] >= cfg.strong_zone_strength
    }
    recent_start = as_of - timedelta(days=cfg.recent_sessions + 2)  # calendar pad
    if strong_ids:
        event_rows = conn.execute(
            sa.select(zone_events_table).where(
                zone_events_table.c.zone_id.in_(list(strong_ids)),
                zone_events_table.c.session_date >= recent_start,
                zone_events_table.c.event.in_(("reclaim", "reject")),
            )
        ).mappings().all()
    else:
        event_rows = []
    for event in event_rows:
        zone = strong_ids[event["zone_id"]]
        category = "zone_reclaims" if event["event"] == "reclaim" else "zone_rejections"
        results[category].append(
            {
                "ticker": zone["ticker"],
                "zone": float(zone["wavg_price"]),
                "strength": zone["strength_score"],
                "session": event["session_date"].isoformat(),
                "why": (
                    f"{event['event']} at {float(zone['wavg_price']):.2f} on "
                    f"{event['session_date'].isoformat()} (zone strength "
                    f"{zone['strength_score']:.0f})"
                ),
            }
        )
    for name in ("zone_reclaims", "zone_rejections"):
        results[name] = sorted(results[name], key=lambda r: -r["strength"])[:limit]

    # 6. Unusually large single prints -----------------------------------
    big = conn.execute(
        sa.select(prints).where(
            prints.c.executed_at >= day_start,
            prints.c.executed_at < day_end,
            prints.c.size_class.in_(("unusual", "extreme")),
        )
    ).mappings().all()
    results["unusual_single_prints"] = [
        {
            "ticker": row["ticker"],
            "size": row["size"],
            "premium": float(row["premium"]),
            "size_class": row["size_class"],
            "why": (
                f"{row['size_class']} print: {row['size']:,} shares "
                f"(${float(row['premium']) / 1e6:.1f}M) — {row['character']}, "
                f"{row['timing_bucket']}"
            ),
        }
        for row in sorted(big, key=lambda r: -float(r["premium"]))[:limit]
    ]

    # 7. Options-confirmed: waits for evidence group D (documented above).
    results["options_confirmed"] = [
        {
            "ticker": row["ticker"],
            "dpss": row["dpss"],
            "why": "options-flow evidence present",
        }
        for row in signal_rows
        if any(item["group"] == "D" for item in row["evidence"].get("supporting", []))
    ][:limit]

    # 8. Dark pool vs price conflict -------------------------------------
    conflicted = [
        row
        for row in signal_rows
        if sum(i["weight"] for i in row["evidence"].get("supporting", [])) >= 2
        and sum(i["weight"] for i in row["evidence"].get("contradicting", [])) >= 2
    ]
    results["price_conflict"] = [
        {
            "ticker": row["ticker"],
            "classification": row["classification"],
            "why": (
                "meaningful evidence on both sides — flagged for review, "
                "not auto-labeled"
            ),
        }
        for row in conflicted[:limit]
    ]

    # 9. Levels likely to matter today -----------------------------------
    for zone in zone_rows:
        if zone["strength_score"] < cfg.strong_zone_strength:
            continue
        price_info = price_context.get(zone["ticker"], {})
        close, atr = price_info.get("close"), price_info.get("atr")
        if close is None or not atr:
            continue
        distance_atr = abs(close - float(zone["wavg_price"])) / atr
        if distance_atr <= cfg.near_price_atr:
            results["levels_likely_to_matter"].append(
                {
                    "ticker": zone["ticker"],
                    "zone": float(zone["wavg_price"]),
                    "strength": zone["strength_score"],
                    "distance_atr": round(distance_atr, 2),
                    "why": (
                        f"strength-{zone['strength_score']:.0f} zone at "
                        f"{float(zone['wavg_price']):.2f} is "
                        f"{distance_atr:.1f} ATR from price ({close:.2f})"
                    ),
                }
            )
    results["levels_likely_to_matter"].sort(key=lambda r: r["distance_atr"])
    results["levels_likely_to_matter"] = results["levels_likely_to_matter"][:limit]

    # 10. Historical zones approaching current price ---------------------
    historical = conn.execute(
        sa.select(zones_table).where(
            zones_table.c.as_of_date < as_of,
            zones_table.c.status == "untested",
            zones_table.c.strength_score >= cfg.strong_zone_strength,
        )
    ).mappings().all()
    seen: set[tuple[str, float]] = set()
    for zone in historical:
        price_info = price_context.get(zone["ticker"], {})
        close = price_info.get("close")
        if close is None:
            continue
        wavg = float(zone["wavg_price"])
        key = (zone["ticker"], round(wavg, 2))
        if key in seen:
            continue
        gap = abs(close - wavg) / close
        if gap <= cfg.approach_pct:
            seen.add(key)
            results["approaching_historical_levels"].append(
                {
                    "ticker": zone["ticker"],
                    "zone": wavg,
                    "from_date": zone["as_of_date"].isoformat(),
                    "gap_pct": round(gap * 100, 2),
                    "why": (
                        f"untested zone from {zone['as_of_date'].isoformat()} at "
                        f"{wavg:.2f} is {gap * 100:.1f}% from price"
                    ),
                }
            )
    results["approaching_historical_levels"].sort(key=lambda r: r["gap_pct"])
    results["approaching_historical_levels"] = (
        results["approaching_historical_levels"][:limit]
    )

    return {
        "date": as_of.isoformat(),
        "market": market_context(conn, as_of),
        "categories": results,
    }
