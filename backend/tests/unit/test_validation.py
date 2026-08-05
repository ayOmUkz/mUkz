"""Tests for the validation layer (clean / flagged / rejected split)."""

import json
from datetime import UTC, datetime
from pathlib import Path

from app.validation import print_record, validate_rows

FIXTURE = Path(__file__).parents[1] / "fixtures" / "darkpool_recent_sample.json"
# Fixture prints executed 2026-08-05; session cutoff two days later.
AS_OF = datetime(2026, 8, 7, 0, 0, tzinfo=UTC)


def fixture_rows() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def poisoned(**overrides) -> dict:
    return {**fixture_rows()[0], **overrides}


def test_real_rows_all_clean():
    result = validate_rows(fixture_rows(), as_of=AS_OF)
    assert result.counts() == {"clean": 3, "flagged": 0, "rejected": 0}


def test_unparseable_row_rejected_at_parse_stage():
    row = poisoned(price=None)
    result = validate_rows([row], as_of=AS_OF)
    assert len(result.rejected) == 1
    assert result.rejected[0].stage == "parse"
    assert any("price" in reason for reason in result.rejected[0].reasons)


def test_canceled_row_rejected_at_quality_stage():
    result = validate_rows([poisoned(canceled=True)], as_of=AS_OF)
    assert len(result.rejected) == 1
    assert result.rejected[0].stage == "quality"
    assert "canceled" in result.rejected[0].reasons


def test_premium_mismatch_rejected():
    result = validate_rows([poisoned(premium="1.00")], as_of=AS_OF)
    assert result.rejected and "premium_mismatch" in result.rejected[0].reasons


def test_stale_print_rejected():
    old = poisoned(
        executed_at="2026-07-01T16:00:00Z",
        created_at="2026-07-01T16:00:01Z",
        trf_executed_at="2026-07-01T16:00:00Z",
    )
    result = validate_rows([old], as_of=AS_OF)
    assert result.rejected and "stale_print" in result.rejected[0].reasons


def test_crossed_quote_kept_but_flagged_with_no_location_confidence():
    row = poisoned(nbbo_bid="417.50", nbbo_ask="417.40")
    result = validate_rows([row], as_of=AS_OF)
    assert result.counts() == {"clean": 1, "flagged": 1, "rejected": 0}
    record = print_record(
        result.clean[0], late_report_seconds=900, ingested_at=AS_OF
    )
    assert record["quality_flags"] == ["crossed_quote"]
    assert record["location_confidence"] == "none"


def test_late_report_downgrades_location_confidence():
    # Executed 16:00, reported 16:20 -> 1200s delay, past the 900s threshold.
    late = poisoned(
        executed_at="2026-08-05T16:00:00Z",
        created_at="2026-08-05T16:20:00Z",
    )
    result = validate_rows([late], as_of=AS_OF)
    assert result.counts()["clean"] == 1
    record = print_record(result.clean[0], late_report_seconds=900, ingested_at=AS_OF)
    assert record["location_confidence"] == "low"
    assert record["report_delay_s"] == 1200.0


def test_prompt_print_with_good_quote_is_ok():
    result = validate_rows(fixture_rows(), as_of=AS_OF)
    record = print_record(result.clean[0], late_report_seconds=900, ingested_at=AS_OF)
    assert record["location_confidence"] == "ok"
    assert record["mid"] is not None
    assert record["quality_flags"] == []
