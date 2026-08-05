"""Print validation: decide, for every raw row, clean / flagged / rejected.

Flags come from :meth:`DarkPoolPrint.quality_flags`. They split into:

* **fatal** — the row cannot be trusted at all (canceled, impossible values,
  broken timestamps). It never reaches the ``prints`` table; it is recorded
  in ``data_quality_log`` instead.
* **non-fatal** — the trade itself is fine but its attached quote is not
  (crossed/empty quote). The print is kept, the flags travel with it, and
  ``location_confidence`` is downgraded so nothing downstream trusts the
  at-bid/at-ask math (plan §8, "Stale/crossed quotes").

Rows that do not even parse (missing price, junk types) are rejected at the
"parse" stage with the validation error preserved.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pydantic import ValidationError

from app.models.print import DarkPoolPrint

#: Flags that disqualify a print from analytics entirely.
FATAL_FLAGS = frozenset(
    {
        "canceled",
        "missing_ticker",
        "nonpositive_price",
        "nonpositive_size",
        "premium_mismatch",
        "report_before_execution",
        "future_execution",
        "stale_print",
    }
)

#: Flags that only invalidate quote-based (location) math.
QUOTE_FLAGS = frozenset({"crossed_quote", "nonpositive_quote", "empty_quote"})


@dataclass
class ValidatedPrint:
    print: DarkPoolPrint
    flags: list[str]


@dataclass
class Rejection:
    row: dict[str, Any]
    stage: str  # "parse" or "quality"
    reasons: list[str]


@dataclass
class ValidationResult:
    clean: list[ValidatedPrint] = field(default_factory=list)
    rejected: list[Rejection] = field(default_factory=list)

    @property
    def flagged_count(self) -> int:
        return sum(1 for vp in self.clean if vp.flags)

    def counts(self) -> dict[str, int]:
        return {
            "clean": len(self.clean),
            "flagged": self.flagged_count,
            "rejected": len(self.rejected),
        }


def validate_rows(rows: list[dict[str, Any]], *, as_of: datetime) -> ValidationResult:
    """Validate raw API rows against a fixed evaluation time.

    ``as_of`` must be the end of the session being ingested (not wall-clock
    now), so that backfilling an old day does not mark everything "stale"
    and re-running a day is reproducible.
    """
    result = ValidationResult()
    for row in rows:
        try:
            parsed = DarkPoolPrint.model_validate(row)
        except ValidationError as exc:
            reasons = [
                f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
                for error in exc.errors()
            ]
            result.rejected.append(Rejection(row=row, stage="parse", reasons=reasons))
            continue

        flags = parsed.quality_flags(as_of=as_of)
        fatal = sorted(FATAL_FLAGS.intersection(flags))
        if fatal:
            result.rejected.append(Rejection(row=row, stage="quality", reasons=flags))
        else:
            result.clean.append(ValidatedPrint(print=parsed, flags=flags))
    return result


def location_confidence(
    print_: DarkPoolPrint, flags: list[str], *, late_report_seconds: int
) -> str:
    """How much the at-bid/at-ask location math can be trusted.

    * ``none`` — quote missing or unusable; never classify location.
    * ``low``  — quote present but the print was reported late; until the M1
      NBBO-timing probe resolves whether quotes are execution-time or
      report-time snapshots, late prints are not trusted (plan §2.3).
    * ``ok``   — quote present, prompt report.
    """
    if print_.mid is None or QUOTE_FLAGS.intersection(flags):
        return "none"
    if print_.report_delay_s > late_report_seconds:
        return "low"
    return "ok"


def print_record(
    validated: ValidatedPrint, *, late_report_seconds: int, ingested_at: datetime
) -> dict[str, Any]:
    """Map a validated print onto a row for the ``prints`` table."""
    p = validated.print
    return {
        "ticker": p.ticker,
        "executed_at": p.executed_at,
        "created_at": p.created_at,
        "trf_executed_at": p.trf_executed_at,
        "price": p.price,
        "size": p.size,
        "premium": p.premium,
        "market_center": p.market_center,
        "sale_cond_codes": p.sale_cond_codes,
        "trade_code": p.trade_code,
        "ext_hour_sold_codes": p.ext_hour_sold_codes,
        "trade_settlement": p.trade_settlement,
        "nbbo_bid": p.nbbo_bid,
        "nbbo_ask": p.nbbo_ask,
        "nbbo_bid_quantity": p.nbbo_bid_quantity,
        "nbbo_ask_quantity": p.nbbo_ask_quantity,
        "volume": p.volume,
        "avg30_volume": p.avg30_volume,
        "tracking_id": p.tracking_id,
        "sector": p.sector,
        "issue_type": p.issue_type,
        "mid": p.mid,
        "spread_bps": p.spread_bps,
        "price_vs_mid_bps": p.price_vs_mid_bps,
        "report_delay_s": p.report_delay_s,
        "pct_adv30": p.pct_adv30,
        "pct_day_volume": p.pct_day_volume,
        "quality_flags": validated.flags,
        "location_confidence": location_confidence(
            p, validated.flags, late_report_seconds=late_report_seconds
        ),
        "ingested_at": ingested_at,
    }
