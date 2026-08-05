"""Tests for the DarkPoolPrint model against recorded real API responses."""

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from app.models.print import DarkPoolPrint

FIXTURE = Path(__file__).parents[1] / "fixtures" / "darkpool_recent_sample.json"
# A time shortly after the fixture prints were recorded.
AS_OF = datetime(2026, 8, 5, 17, 0, tzinfo=UTC)


def load_rows() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def make_print(**overrides) -> DarkPoolPrint:
    row = {**load_rows()[0], **overrides}
    return DarkPoolPrint.model_validate(row)


def test_parses_real_api_rows():
    prints = [DarkPoolPrint.model_validate(row) for row in load_rows()]
    tsm = prints[0]
    assert tsm.ticker == "TSM"
    assert tsm.size == 5487
    assert tsm.price == Decimal("417.25")
    assert tsm.premium == Decimal("2289450.75")
    assert tsm.executed_at == datetime(2026, 8, 5, 16, 28, 21, tzinfo=UTC)
    assert tsm.report_delay_s == 1.0
    assert tsm.mid == (Decimal("417.34") + Decimal("417.46")) / 2


def test_real_rows_are_clean():
    for row in load_rows():
        print_ = DarkPoolPrint.model_validate(row)
        assert print_.quality_flags(as_of=AS_OF) == []


def test_naive_timestamps_become_utc():
    print_ = make_print(executed_at="2026-08-05T16:28:21", created_at="2026-08-05T16:28:22")
    assert print_.executed_at.tzinfo is not None
    assert print_.executed_at == datetime(2026, 8, 5, 16, 28, 21, tzinfo=UTC)


def test_derived_ratios():
    tsm = make_print()
    assert tsm.pct_adv30 is not None
    assert abs(tsm.pct_adv30 - 5487 / 14922272.136363636364) < 1e-12
    assert tsm.pct_day_volume is not None
    assert abs(tsm.pct_day_volume - 5487 / 7797577) < 1e-12
    assert tsm.price_vs_mid_bps is not None
    assert tsm.price_vs_mid_bps < 0  # executed below the quote midpoint


def test_canceled_is_flagged():
    assert "canceled" in make_print(canceled=True).quality_flags(as_of=AS_OF)


def test_premium_mismatch_is_flagged():
    tampered = make_print(premium="9999999.99")
    assert "premium_mismatch" in tampered.quality_flags(as_of=AS_OF)


def test_nonpositive_size_and_price_are_flagged():
    flags = make_print(size=0, price="0").quality_flags(as_of=AS_OF)
    assert "nonpositive_size" in flags
    assert "nonpositive_price" in flags


def test_crossed_quote_is_flagged():
    crossed = make_print(nbbo_bid="417.50", nbbo_ask="417.40")
    assert "crossed_quote" in crossed.quality_flags(as_of=AS_OF)


def test_empty_quote_is_flagged():
    empty = make_print(nbbo_bid_quantity=0)
    assert "empty_quote" in empty.quality_flags(as_of=AS_OF)


def test_report_before_execution_is_flagged():
    # Reported a full minute before it supposedly executed: broken clocks.
    weird = make_print(created_at="2026-08-05T16:27:21Z")
    assert "report_before_execution" in weird.quality_flags(as_of=AS_OF)


def test_one_second_delay_is_not_flagged_as_time_travel():
    assert "report_before_execution" not in make_print().quality_flags(as_of=AS_OF)


def test_future_execution_and_stale_print():
    print_ = make_print()
    before_execution = print_.executed_at - timedelta(hours=1)
    assert "future_execution" in print_.quality_flags(as_of=before_execution)
    much_later = print_.executed_at + timedelta(days=30)
    assert "stale_print" in print_.quality_flags(as_of=much_later)


def test_unknown_fields_are_kept_not_dropped():
    print_ = make_print(mystery_field="keep-me")
    assert print_.model_dump()["mystery_field"] == "keep-me"


def test_missing_quote_means_no_mid_and_no_location_math():
    print_ = make_print(nbbo_bid=None, nbbo_ask=None)
    assert print_.mid is None
    assert print_.spread_bps is None
    assert print_.price_vs_mid_bps is None
    assert print_.quality_flags(as_of=AS_OF) == []  # missing quote is not itself an error
