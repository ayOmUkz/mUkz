"""The per-ticker report (plan §12 output format), as JSON and markdown.

Every number traces back to stored rows; every conclusion carries its
evidence, its contradicting evidence, and its invalidation levels. The
report never issues a guaranteed prediction — scenarios are conditionals.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from app.analytics.context import (
    context_label,
    load_daily,
    market_context,
    sector_trend,
    signal_direction,
)
from app.analytics.zones import sessions_between
from app.config import Settings
from app.db import signals, symbols
from app.db import zones as zones_table

VERDICT_HIGH_PRIORITY_DPSS = 70
VERDICT_AVOID_QUALITY = 50


def _json(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else (value or None)


def final_verdict(
    *, classification: str, dpss: float, quality: float, context_summary: str,
    min_dpss: int,
) -> str:
    """Map scores + context onto the plan's five verdicts."""
    if classification == "insufficient_evidence":
        return "insufficient evidence"
    if quality < VERDICT_AVOID_QUALITY:
        return "avoid"
    directional = classification.startswith(("probable", "possible"))
    if directional and context_summary == "conflicting":
        return "actionable only after confirmation"
    if (
        classification.startswith("probable")
        and dpss >= VERDICT_HIGH_PRIORITY_DPSS
        and context_summary not in ("isolated", "conflicting")
    ):
        return "high-priority watch"
    if dpss >= min_dpss:
        return "watch"
    return "watch" if directional else "insufficient evidence"


def _fmt(value: float | None, prefix: str = "") -> str:
    return f"{prefix}{value:,.2f}" if value is not None else "n/a"


def build_ticker_report(
    conn: Connection, ticker: str, as_of: date, settings: Settings
) -> dict[str, Any] | None:
    """Assemble the full Phase-12 report; None when no signal exists."""
    signal = conn.execute(
        sa.select(signals).where(
            signals.c.ticker == ticker, signals.c.as_of_date == as_of
        )
    ).mappings().first()
    if signal is None:
        return None
    evidence = _json(signal["evidence"]) or {}
    sub_scores = _json(signal["sub_scores"]) or {}
    invalidation = _json(signal["invalidation"]) or []
    top_zone = _json(signal["top_zone"])

    zone_rows = [
        dict(row)
        for row in conn.execute(
            sa.select(zones_table)
            .where(zones_table.c.ticker == ticker, zones_table.c.as_of_date == as_of)
            .order_by(zones_table.c.strength_score.desc())
        ).mappings()
    ]
    daily = load_daily(conn, ticker, as_of)
    current_close = float(daily[-1]["close"]) if daily else None
    symbol = conn.execute(
        sa.select(symbols).where(symbols.c.ticker == ticker)
    ).mappings().first()
    sector = symbol["sector"] if symbol else None

    market = market_context(conn, as_of)
    sector_trend_value = sector_trend(conn, sector, as_of)
    direction = signal_direction(signal["classification"])
    context = context_label(
        direction=direction,
        spy_trend=market["spy_trend"],
        sector_trend_value=sector_trend_value,
        zone_status=(top_zone or {}).get("status"),
    )

    # --- levels ----------------------------------------------------------
    support = resistance = None
    if current_close is not None:
        below = [z for z in zone_rows if float(z["wavg_price"]) <= current_close]
        above = [z for z in zone_rows if float(z["wavg_price"]) > current_close]
        support = float(below[0]["wavg_price"]) if below else None
        resistance = float(above[0]["wavg_price"]) if above else None
    reclaim_level = (
        float(top_zone["price_high"]) if top_zone and top_zone.get("status") == "broken"
        else None
    )
    breakdown_level = float(top_zone["price_low"]) if top_zone else None
    invalidation_level = next(
        (c.get("level") for c in invalidation if c.get("level") is not None), None
    )

    # --- summary ---------------------------------------------------------
    total_shares = sum(z["total_shares"] for z in zone_rows)
    total_notional = sum(float(z["total_notional"]) for z in zone_rows)
    freshness_sessions = None
    distance_pct = None
    if top_zone and current_close:
        distance_pct = round(
            (current_close - top_zone["wavg_price"]) / top_zone["wavg_price"] * 100, 2
        )
    if zone_rows:
        top_row = zone_rows[0]
        last_date = top_row["last_print_at"]
        last_date = last_date.date() if hasattr(last_date, "date") else as_of
        freshness_sessions = sessions_between(last_date, as_of)

    pct_adv = max((z["pct_adv30"] or 0.0 for z in zone_rows), default=None)
    quality = sub_scores.get("quality", 0.0)
    verdict = final_verdict(
        classification=signal["classification"],
        dpss=signal["dpss"],
        quality=quality,
        context_summary=context["summary"],
        min_dpss=settings.scanner.min_dpss,
    )

    supporting = evidence.get("supporting", [])
    contradicting = evidence.get("contradicting", [])
    aligned = supporting if direction >= 0 else contradicting
    opposing = contradicting if direction >= 0 else supporting

    classification_text = signal["classification"].replace("_", " ")
    if direction != 0:
        likely = (
            f"{classification_text} (confidence {signal['confidence']:.2f}) — "
            f"{len(aligned)} aligned evidence item(s) across groups "
            f"{'/'.join(evidence.get('groups', []))}"
        )
        alternative = (
            "the prints may be hedging or routine liquidity; "
            f"{len(opposing)} item(s) point the other way"
        )
    else:
        likely = f"{classification_text} — no directional call is supported"
        alternative = "collect more sessions of evidence before interpreting"

    return {
        "ticker": ticker,
        "as_of": as_of.isoformat(),
        "current_price": current_close,
        "market_regime": market,
        "sector": sector,
        "sector_trend": sector_trend_value,
        "context": context,
        "summary": {
            "relevant_prints": sum(z["print_count"] for z in zone_rows),
            "total_shares": total_shares,
            "total_notional": total_notional,
            "main_zone": (
                {
                    "wavg_price": top_zone["wavg_price"],
                    "low": top_zone["price_low"],
                    "high": top_zone["price_high"],
                    "strength_score": top_zone["strength_score"],
                    "strength_class": top_zone["strength_class"],
                    "status": top_zone["status"],
                }
                if top_zone
                else None
            ),
            "distance_from_price_pct": distance_pct,
            "pct_of_adv30": pct_adv,
            "freshness_sessions": freshness_sessions,
            "data_quality_score": quality,
        },
        "interpretation": {
            "classification": signal["classification"],
            "confidence": signal["confidence"],
            "bullish_evidence": [i["description"] for i in supporting],
            "bearish_evidence": [i["description"] for i in contradicting],
            "contradictory_evidence": [i["description"] for i in opposing],
            "most_likely": likely,
            "alternative": alternative,
        },
        "levels": {
            "primary_support": support,
            "primary_resistance": resistance,
            "reclaim_level": reclaim_level,
            "breakdown_level": breakdown_level,
            "invalidation_level": invalidation_level,
        },
        "scenarios": {
            "bullish": (
                f"If price holds above {_fmt(support)} and reclaims/extends over "
                f"{_fmt(resistance)}, the accumulation case strengthens."
            ),
            "neutral": (
                f"Between {_fmt(support)} and {_fmt(resistance)} the dark-pool tape "
                "is balanced; no edge until one side gives."
            ),
            "bearish": (
                f"A daily close below {_fmt(invalidation_level or breakdown_level)} "
                "invalidates the constructive read and favors distribution."
            ),
        },
        "scores": sub_scores,
        "dpss": signal["dpss"],
        "verdict": verdict,
    }


def render_markdown(report: dict[str, Any]) -> str:
    """The Phase-12 layout, verbatim sections (plan §12)."""
    summary = report["summary"]
    interp = report["interpretation"]
    levels = report["levels"]
    zone = summary["main_zone"]
    market = report["market_regime"]

    def bullets(items: list[str]) -> str:
        return "\n".join(f"  - {item}" for item in items) if items else "  - none"

    zone_text = (
        f"{zone['low']:.2f}–{zone['high']:.2f} (wavg {zone['wavg_price']:.2f}, "
        f"{zone['strength_class']}, {zone['status']})"
        if zone
        else "n/a"
    )
    lines = [
        f"# {report['ticker']} — {report['as_of']}",
        "",
        f"Current price: {_fmt(report['current_price'])}",
        f"Market regime: SPY {market['spy_trend'] or 'n/a'}, "
        f"QQQ {market['qqq_trend'] or 'n/a'}",
        f"Sector trend: {report['sector'] or 'n/a'} "
        f"({report['sector_trend'] or 'n/a'}); context: {report['context']['summary']}",
        "",
        "## Dark-pool summary",
        f"- Number of relevant prints: {summary['relevant_prints']}",
        f"- Total shares: {summary['total_shares']:,}",
        f"- Total notional: {_fmt(summary['total_notional'], '$')}",
        f"- Main dark-pool zone: {zone_text}",
        f"- Distance from current price: {summary['distance_from_price_pct']}%",
        f"- Percentage of average daily volume: "
        f"{summary['pct_of_adv30']:.2%}" if summary["pct_of_adv30"] is not None
        else "- Percentage of average daily volume: n/a",
        f"- Freshness: {summary['freshness_sessions']} session(s) since last print",
        f"- Data-quality score: {summary['data_quality_score']}",
        "",
        "## Interpretation",
        f"- Classification: {interp['classification']}",
        f"- Confidence: {interp['confidence']:.2f}",
        "- Bullish evidence:",
        bullets(interp["bullish_evidence"]),
        "- Bearish evidence:",
        bullets(interp["bearish_evidence"]),
        "- Contradictory evidence:",
        bullets(interp["contradictory_evidence"]),
        f"- Most likely institutional interpretation: {interp['most_likely']}",
        f"- Alternative interpretation: {interp['alternative']}",
        "",
        "## Important levels",
        f"- Primary dark-pool support: {_fmt(levels['primary_support'])}",
        f"- Primary dark-pool resistance: {_fmt(levels['primary_resistance'])}",
        f"- Reclaim level: {_fmt(levels['reclaim_level'])}",
        f"- Breakdown level: {_fmt(levels['breakdown_level'])}",
        f"- Invalidation level: {_fmt(levels['invalidation_level'])}",
        "",
        "## Scenario map",
        f"- Bullish scenario: {report['scenarios']['bullish']}",
        f"- Neutral scenario: {report['scenarios']['neutral']}",
        f"- Bearish scenario: {report['scenarios']['bearish']}",
        "",
        f"## Final verdict: {report['verdict']}",
        "",
        f"_DPSS {report['dpss']} — probabilities, not promises._",
        "",
    ]
    return "\n".join(lines)
