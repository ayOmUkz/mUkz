"""Tests for the pure classification rules (plan §7)."""

from datetime import UTC, datetime
from decimal import Decimal

from app.analytics.classify import (
    liquidity_character,
    location_bucket,
    size_classification,
    timing_bucket,
    vwap_position,
)
from app.config import SizeClassConfig

BID, ASK = Decimal("100.00"), Decimal("101.00")


def loc(price: str) -> str | None:
    return location_bucket(Decimal(price), BID, ASK)


def test_location_buckets_across_the_spread():
    assert loc("99.80") == "below_bid"
    assert loc("100.00") == "at_bid"
    assert loc("100.05") == "at_bid"      # within 10% of the spread
    assert loc("100.15") == "near_bid"
    assert loc("100.35") == "below_mid"
    assert loc("100.50") == "at_mid"
    assert loc("100.65") == "above_mid"
    assert loc("100.80") == "near_ask"
    assert loc("100.95") == "at_ask"
    assert loc("101.20") == "above_ask"


def test_location_none_without_usable_quote():
    assert location_bucket(Decimal("100"), None, ASK) is None
    assert location_bucket(Decimal("100"), Decimal("101"), Decimal("100.5")) is None  # crossed


def et(hour_utc: int, minute: int = 0) -> datetime:
    # 2026-08-05 is a Wednesday; Eastern Daylight Time = UTC-4.
    return datetime(2026, 8, 5, hour_utc, minute, tzinfo=UTC)


def bucket_at(hour_utc: int, minute: int = 0) -> str:
    return timing_bucket(et(hour_utc, minute), report_delay_s=1.0, late_report_seconds=900)


def test_timing_buckets_in_eastern_time():
    assert bucket_at(13, 0) == "premarket"    # 09:00 ET
    assert bucket_at(13, 45) == "open"        # 09:45
    assert bucket_at(15, 0) == "morning"      # 11:00
    assert bucket_at(16, 30) == "lunch"       # 12:30
    assert bucket_at(18, 0) == "afternoon"    # 14:00
    assert bucket_at(19, 45) == "close"       # 15:45
    assert bucket_at(21, 0) == "after_hours"  # 17:00


def test_timing_late_report_overrides_session():
    assert timing_bucket(et(15), report_delay_s=1200, late_report_seconds=900) == "late_report"


def test_timing_weekend_is_after_hours():
    saturday = datetime(2026, 8, 8, 15, 0, tzinfo=UTC)
    assert timing_bucket(saturday, report_delay_s=1, late_report_seconds=900) == "after_hours"


def test_vwap_position_band():
    vwap = Decimal("100")
    assert vwap_position(Decimal("100.05"), vwap) == "near"   # 5 bps, inside 10 bps band
    assert vwap_position(Decimal("101"), vwap) == "above"
    assert vwap_position(Decimal("99"), vwap) == "below"
    assert vwap_position(Decimal("100"), None) is None


HIST_STATS = {"sample_size": 500, "p50": 100.0, "p90": 1000.0, "p99": 5000.0, "p999": 20000.0}
CFG = SizeClassConfig()


def classify_size(size: int, premium: str, stats=None, pct_adv30=None):
    return size_classification(
        size=size,
        premium=Decimal(premium),
        pct_adv30=pct_adv30,
        stats=stats,
        config=CFG,
    )


def test_size_class_against_own_history():
    assert classify_size(500, "1000000", HIST_STATS)[0] == "normal"
    assert classify_size(1500, "1000000", HIST_STATS)[0] == "elevated"
    assert classify_size(6000, "1000000", HIST_STATS)[0] == "unusual"
    assert classify_size(25000, "1000000", HIST_STATS)[0] == "extreme"
    assert classify_size(500, "1000000", HIST_STATS)[2] == "historical"


def test_size_class_adv_override_is_always_extreme():
    size_class, _, confidence = classify_size(10, "1000", HIST_STATS, pct_adv30=0.02)
    assert (size_class, confidence) == ("extreme", "historical")
    # Cold start too: 2% of ADV in one print is exceptional regardless of history.
    assert classify_size(10, "1000", None, pct_adv30=0.02)[0] == "extreme"


def test_size_class_cold_start_uses_notional_buckets():
    thin = {"sample_size": 10, "p50": 1.0, "p90": 2.0, "p99": 3.0, "p999": 4.0}
    assert classify_size(1, "500000", thin) == ("normal", None, "provisional")
    assert classify_size(1, "2000000", thin) == ("elevated", None, "provisional")
    assert classify_size(1, "6000000", thin) == ("unusual", None, "provisional")
    assert classify_size(1, "25000000", thin) == ("extreme", None, "provisional")


def character(**overrides) -> str:
    defaults = dict(
        sale_cond_codes=None,
        trade_code=None,
        size=1000,
        size_class="normal",
        nbbo_bid_quantity=500,
        nbbo_ask_quantity=500,
        report_delay_s=1.0,
        location="at_mid",
        late_report_seconds=900,
    )
    return liquidity_character(**{**defaults, **overrides})


def test_character_condition_codes_come_first():
    assert character(sale_cond_codes="odd_lot_execution") == "odd_lot"
    assert character(sale_cond_codes="average_price_trade") == "probable_vwap_execution"
    assert character(trade_code="derivative_priced") == "derivative_linked"
    assert character(trade_code="qualified_contingent_trade") == "derivative_linked"
    assert character(sale_cond_codes="contingent_trade") == "derivative_linked"
    assert character(sale_cond_codes="prior_reference_price") == "possible_negotiated_block"


def test_character_late_big_edge_print_is_possible_block():
    assert (
        character(size_class="unusual", report_delay_s=1200, location="at_bid")
        == "possible_negotiated_block"
    )
    # Same but reported promptly: not a negotiated-block candidate.
    assert character(size_class="unusual", location="at_bid") == "routine_off_exchange"


def test_character_size_dwarfing_displayed_quote_is_dark_crossing():
    assert (
        character(size=100_000, size_class="elevated", nbbo_bid_quantity=100,
                  nbbo_ask_quantity=100)
        == "probable_dark_crossing"
    )
    # A normal-class print never gets the crossing label from size alone.
    assert (
        character(size=100_000, size_class="normal", nbbo_bid_quantity=100,
                  nbbo_ask_quantity=100)
        == "routine_off_exchange"
    )
