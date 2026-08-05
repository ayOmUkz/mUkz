"""``DarkPoolPrint`` — our typed contract with the API's dark-pool trade record.

Field meanings are documented in plain language in docs/PLAN.md §3. Two rules
apply everywhere in this codebase:

* analytics key off ``executed_at`` — when the trade actually happened;
* backtests key off ``created_at`` — when the tape (and therefore we) knew.

A print never proves direction by itself: every trade has a buyer AND a
seller, and the record does not say who initiated. This model only
normalizes, derives arithmetic facts, and reports data-quality problems —
interpretation lives in ``app.analytics`` (later milestones).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator

#: Reporting clocks can disagree by a little without meaning anything.
CLOCK_SKEW_TOLERANCE = timedelta(seconds=2)
#: Prints executed longer ago than this (relative to ``as_of``) are stale.
STALE_AFTER = timedelta(days=7)
#: Allowed relative gap between ``premium`` and ``price * size``.
PREMIUM_MISMATCH_TOLERANCE = Decimal("0.01")


class DarkPoolPrint(BaseModel):
    """One off-exchange (dark pool / TRF) stock trade as reported by the API."""

    # Unknown fields are kept, never silently dropped (plan §2.5); frozen so a
    # print can't be mutated after validation.
    model_config = ConfigDict(extra="allow", frozen=True)

    ticker: str
    size: int
    price: Decimal
    premium: Decimal
    executed_at: datetime
    created_at: datetime
    trf_executed_at: datetime | None = None
    canceled: bool = False

    market_center: str | None = None
    sale_cond_codes: str | None = None
    trade_code: str | None = None
    ext_hour_sold_codes: str | None = None
    trade_settlement: str | None = None

    nbbo_bid: Decimal | None = None
    nbbo_ask: Decimal | None = None
    nbbo_bid_quantity: int | None = None
    nbbo_ask_quantity: int | None = None

    volume: int | None = None
    avg30_volume: Decimal | None = None
    tracking_id: int | None = None
    sector: str | None = None
    issue_type: str | None = None

    @field_validator("executed_at", "created_at", "trf_executed_at", mode="after")
    @classmethod
    def _force_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    # ------------------------------------------------------- derived facts

    @property
    def mid(self) -> Decimal | None:
        """Midpoint of the attached NBBO quote, if both sides are present."""
        if self.nbbo_bid is None or self.nbbo_ask is None:
            return None
        return (self.nbbo_bid + self.nbbo_ask) / 2

    @property
    def spread(self) -> Decimal | None:
        if self.nbbo_bid is None or self.nbbo_ask is None:
            return None
        return self.nbbo_ask - self.nbbo_bid

    @property
    def spread_bps(self) -> float | None:
        """Quoted spread in basis points of the midpoint."""
        mid = self.mid
        spread = self.spread
        if mid is None or spread is None or mid <= 0:
            return None
        return float(spread / mid) * 10_000

    @property
    def price_vs_mid_bps(self) -> float | None:
        """Execution price vs quote midpoint, in basis points (+ above, - below)."""
        mid = self.mid
        if mid is None or mid <= 0:
            return None
        return float((self.price - mid) / mid) * 10_000

    @property
    def report_delay_s(self) -> float:
        """Seconds between execution and the print hitting the tape."""
        return (self.created_at - self.executed_at).total_seconds()

    @property
    def pct_adv30(self) -> float | None:
        """This print's size as a fraction of 30-day average daily volume."""
        if self.avg30_volume is None or self.avg30_volume <= 0:
            return None
        return float(Decimal(self.size) / self.avg30_volume)

    @property
    def pct_day_volume(self) -> float | None:
        """This print's size as a fraction of the day's volume so far."""
        if self.volume is None or self.volume <= 0:
            return None
        return self.size / self.volume

    # ----------------------------------------------------- quality control

    def quality_flags(self, *, as_of: datetime | None = None) -> list[str]:
        """Every data-quality problem with this print (empty list = clean).

        ``as_of`` is the evaluation time; pipelines pass it explicitly so runs
        are reproducible. Defaults to "now" (UTC) for interactive use.
        Flag semantics and the false signals they prevent: docs/PLAN.md §8.
        """
        evaluation_time = as_of if as_of is not None else datetime.now(UTC)
        flags: list[str] = []

        if self.canceled:
            flags.append("canceled")
        if not self.ticker.strip():
            flags.append("missing_ticker")
        if self.price <= 0:
            flags.append("nonpositive_price")
        if self.size <= 0:
            flags.append("nonpositive_size")

        if self.price > 0 and self.size > 0:
            expected = self.price * self.size
            if abs(self.premium - expected) > expected * PREMIUM_MISMATCH_TOLERANCE:
                flags.append("premium_mismatch")

        if self.created_at + CLOCK_SKEW_TOLERANCE < self.executed_at:
            flags.append("report_before_execution")
        if self.executed_at > evaluation_time + CLOCK_SKEW_TOLERANCE:
            flags.append("future_execution")
        elif evaluation_time - self.executed_at > STALE_AFTER:
            flags.append("stale_print")

        if self.nbbo_bid is not None and self.nbbo_ask is not None:
            if self.nbbo_bid <= 0 or self.nbbo_ask <= 0:
                flags.append("nonpositive_quote")
            elif self.nbbo_bid >= self.nbbo_ask:
                flags.append("crossed_quote")
        if self.nbbo_bid_quantity == 0 or self.nbbo_ask_quantity == 0:
            flags.append("empty_quote")

        return flags
