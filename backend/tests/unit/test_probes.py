"""Tests for the three M1 verification probes (fake client, no network)."""

from datetime import date

from app.client.uw_client import UWAPIError
from app.ingestion.probes import (
    probe_float_availability,
    probe_historical_depth,
    probe_nbbo_timing,
)

TODAY = date(2026, 8, 5)


class DepthFake:
    """Has data only after a fixed cutoff date."""

    def __init__(self, earliest: date):
        self.earliest = earliest
        self.calls = 0

    def ticker_darkpool_trades(self, ticker, *, date, limit):
        self.calls += 1
        from datetime import date as date_type

        return [{"ok": 1}] if date_type.fromisoformat(date) >= self.earliest else []


def test_historical_depth_finds_boundary_within_resolution():
    true_earliest = TODAY.replace(year=2024)  # ~2 years of history
    fake = DepthFake(true_earliest)
    result = probe_historical_depth(fake, "SPY", today=TODAY)
    assert result["boundary_found"] is True
    found = date.fromisoformat(result["earliest_confirmed"])
    # Confirmed date must have data, and sit within resolution of the truth.
    assert found >= true_earliest
    assert (found - true_earliest).days <= result["resolution_days"] + 3
    assert result["calls"] == fake.calls


def test_historical_depth_range_exhausted_when_data_never_ends():
    fake = DepthFake(date(2000, 1, 1))
    result = probe_historical_depth(fake, "SPY", today=TODAY)
    assert result["boundary_found"] is False
    assert "earliest_confirmed" in result


def _print_row(price, bid, ask, executed, created):
    return {
        "price": price,
        "nbbo_bid": bid,
        "nbbo_ask": ask,
        "executed_at": executed,
        "created_at": created,
    }


class NbboFake:
    def __init__(self, rows):
        self.rows = rows

    def iter_ticker_darkpool_trades(self, ticker, **kwargs):
        yield from self.rows


def test_nbbo_timing_probe_separates_prompt_and_late_cohorts():
    rows = [
        # Prompt (1s delay), inside the quote.
        _print_row("100.05", "100.00", "100.10", "2026-08-05T15:00:00Z", "2026-08-05T15:00:01Z"),
        # Prompt, inside.
        _print_row("100.09", "100.00", "100.10", "2026-08-05T15:01:00Z", "2026-08-05T15:01:01Z"),
        # Late (30 min), OUTSIDE the attached quote.
        _print_row("99.00", "100.00", "100.10", "2026-08-05T15:00:00Z", "2026-08-05T15:30:00Z"),
        # Late, inside.
        _print_row("100.02", "100.00", "100.10", "2026-08-05T14:00:00Z", "2026-08-05T14:30:00Z"),
        # Mid-delay (5 min): belongs to neither cohort.
        _print_row("100.05", "100.00", "100.10", "2026-08-05T15:00:00Z", "2026-08-05T15:05:00Z"),
        # Crossed quote: excluded entirely.
        _print_row("100.05", "100.20", "100.10", "2026-08-05T15:00:00Z", "2026-08-05T15:00:01Z"),
    ]
    result = probe_nbbo_timing(NbboFake(rows), "SPY", date_str="2026-08-05")
    assert result["prompt"] == {"n": 2, "inside": 2, "inside_rate": 1.0}
    assert result["late"] == {"n": 2, "inside": 1, "inside_rate": 0.5}


class FloatFake:
    def ticker_info(self, ticker):
        if ticker == "MISSING":
            raise UWAPIError("not found", status_code=404)
        return {
            "full_name": "Apple Inc",
            "float": 15000000000,
            "shares_outstanding": "15500000000",
            "sector": "Technology",
        }

    def short_screener(self, **kwargs):
        return [{"ticker": "AAPL", "total_float": 15000000000, "days_to_cover": 1.2}]


def test_float_probe_reports_field_names_and_errors():
    result = probe_float_availability(FloatFake(), ["AAPL", "MISSING"])
    assert result["stock_info_fields"]["AAPL"] == {
        "float": 15000000000,
        "shares_outstanding": "15500000000",
    }
    assert result["stock_info_fields"]["MISSING"] == {"error": 404}
    assert result["short_screener_float_fields"] == ["total_float"]
    assert result["short_screener_error"] is None
