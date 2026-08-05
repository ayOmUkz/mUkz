"""Tests for the Phase-12 report builder, renderer, and verdict rules."""

from datetime import UTC, date, datetime, timedelta

import pytest

from app.config import Settings
from app.db import candles, ensure_schema, make_engine, signals, symbol_days, symbols
from app.db import zones as zones_table
from app.reports import build_ticker_report, final_verdict, render_markdown

AS_OF = date(2026, 8, 5)
NOW = datetime(2026, 8, 5, 22, 0, tzinfo=UTC)
SETTINGS = Settings()


@pytest.fixture()
def engine():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    ensure_schema(engine)
    with engine.begin() as conn:
        conn.execute(symbols.insert().values(
            ticker="ACC", sector="Technology", issue_type="Common Stock",
            first_seen_at=NOW, last_seen_at=NOW,
        ))
        # Rising SPY: 30 daily bars -> market trend "up".
        for i in range(30):
            ts = datetime(2026, 6, 20, tzinfo=UTC) + timedelta(days=i)
            close = 500 + i
            conn.execute(candles.insert().values(
                ticker="SPY", candle_size="1d", ts=ts,
                open=close, high=close + 1, low=close - 1, close=close, volume=1,
            ))
        conn.execute(candles.insert().values(
            ticker="ACC", candle_size="1d", ts=datetime(2026, 8, 5, tzinfo=UTC),
            open=100, high=101, low=99, close=100, volume=1_000_000,
        ))
        conn.execute(symbol_days.insert().values(
            ticker="ACC", trading_date=AS_OF, atr14=2.0, minute_bars=390, updated_at=NOW,
        ))
        conn.execute(zones_table.insert().values(
            ticker="ACC", as_of_date=AS_OF, window_start=AS_OF, window_end=AS_OF,
            price_low=98.5, price_high=99.5, wavg_price=99.0,
            total_shares=1_000_000, total_notional=60_000_000, print_count=6,
            unique_days=4, first_print_at=NOW - timedelta(days=3),
            last_print_at=NOW - timedelta(days=1),
            pct_adv30=0.02, pct_dark_volume=0.5, tightness_atr=0.5,
            strength_score=75.0, strength_class="strong", status="respected",
            respected_touches=2, created_at=NOW,
        ))
        conn.execute(signals.insert().values(
            ticker="ACC", as_of_date=AS_OF, classification="probable_accumulation",
            confidence=0.65, dpss=72.0,
            sub_scores={"print": 70, "zone": 75, "direction": 65,
                        "relevance": 85, "quality": 90},
            evidence={
                "supporting": [
                    {"id": "A_repeat_holding", "group": "A", "direction": 1,
                     "weight": 2, "description": "repeated prints while price holds"},
                    {"id": "B_respected", "group": "B", "direction": 1,
                     "weight": 2, "description": "zone respected 2x"},
                ],
                "contradicting": [
                    {"id": "C_down_volume", "group": "C", "direction": -1,
                     "weight": 1, "description": "down-day volume heavier"},
                ],
                "groups": ["A", "B", "C"],
            },
            invalidation=[{"type": "daily_close_below", "level": 97.5,
                           "description": "daily close below 97.50"}],
            top_zone={"wavg_price": 99.0, "price_low": 98.5, "price_high": 99.5,
                      "strength_score": 75.0, "strength_class": "strong",
                      "status": "respected", "unique_days": 4,
                      "total_shares": 1_000_000, "strength_components": {}},
            available_at=NOW,
        ))
    return engine


def test_build_report_fields(engine):
    with engine.connect() as conn:
        report = build_ticker_report(conn, "ACC", AS_OF, SETTINGS)
    assert report is not None
    assert report["current_price"] == 100.0
    assert report["market_regime"]["spy_trend"] == "up"
    assert report["sector"] == "Technology"
    assert report["sector_trend"] is None  # XLK candles absent: honest n/a
    # Bullish signal + SPY up + respected zone -> confirmed, not conflicting.
    assert "market_confirmed" in report["context"]["labels"]
    assert "technically_confirmed" in report["context"]["labels"]

    assert report["summary"]["main_zone"]["wavg_price"] == 99.0
    assert report["summary"]["freshness_sessions"] == 1
    assert report["levels"]["primary_support"] == 99.0
    assert report["levels"]["primary_resistance"] is None
    assert report["levels"]["invalidation_level"] == 97.5
    assert report["interpretation"]["bullish_evidence"] == [
        "repeated prints while price holds", "zone respected 2x",
    ]
    assert report["interpretation"]["contradictory_evidence"] == [
        "down-day volume heavier",
    ]
    assert report["verdict"] == "high-priority watch"  # probable, DPSS 72, confirmed


def test_report_none_without_signal(engine):
    with engine.connect() as conn:
        assert build_ticker_report(conn, "NOPE", AS_OF, SETTINGS) is None


def test_render_markdown_has_all_sections(engine):
    with engine.connect() as conn:
        report = build_ticker_report(conn, "ACC", AS_OF, SETTINGS)
    text = render_markdown(report)
    for section in (
        "# ACC — 2026-08-05",
        "Current price: 100.00",
        "Market regime: SPY up",
        "## Dark-pool summary",
        "- Main dark-pool zone: 98.50–99.50 (wavg 99.00, strong, respected)",
        "## Interpretation",
        "- Classification: probable_accumulation",
        "## Important levels",
        "- Invalidation level: 97.50",
        "## Scenario map",
        "- Bearish scenario: A daily close below 97.50",
        "## Final verdict: high-priority watch",
        "probabilities, not promises",
    ):
        assert section in text, f"missing: {section}"


def verdict(**overrides) -> str:
    defaults = dict(
        classification="probable_accumulation", dpss=72.0, quality=90.0,
        context_summary="market_confirmed", min_dpss=40,
    )
    return final_verdict(**{**defaults, **overrides})


def test_final_verdict_rules():
    assert verdict() == "high-priority watch"
    assert verdict(classification="insufficient_evidence") == "insufficient evidence"
    assert verdict(quality=40.0) == "avoid"
    assert verdict(context_summary="conflicting") == "actionable only after confirmation"
    assert verdict(dpss=55.0) == "watch"  # probable but below high-priority bar
    assert verdict(classification="possible_accumulation", context_summary="isolated",
                   dpss=65.0) == "watch"
    assert verdict(classification="neutral_institutional_activity", dpss=45.0) == "watch"
    assert verdict(classification="neutral_institutional_activity",
                   dpss=30.0) == "insufficient evidence"
    assert verdict(classification="possible_distribution", dpss=30.0,
                   context_summary="isolated") == "watch"
