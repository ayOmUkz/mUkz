"""Backtest engine tests — including the plan §17 self-test: a planted
edge the engine must find, and a planted look-ahead trap it must NOT
profit from."""

from datetime import UTC, date, datetime, timedelta

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from app.api.main import app, get_engine, get_settings
from app.backtest import render_backtest_report, run_backtest
from app.backtest.engine import collect_events, measure_event
from app.backtest.stats import aggregate_cohorts, bootstrap_ci, cohort_metrics
from app.config import Settings
from app.db import candles, ensure_schema, make_engine, signals, symbols

NOW = datetime(2026, 8, 10, 22, 0, tzinfo=UTC)
SIGNAL_DATE = date(2026, 7, 1)  # a Wednesday
SETTINGS = Settings.model_validate({"backtest": {"bootstrap_samples": 200}})
HORIZONS = SETTINGS.backtest.horizons


def bar(day: date, open_: float, close: float, *, spread: float = 1.0) -> dict:
    return {
        "date": day,
        "open": open_,
        "high": max(open_, close) + spread,
        "low": min(open_, close) - spread,
        "close": close,
    }


def weekdays(start: date, count: int) -> list[date]:
    days = []
    current = start
    while len(days) < count:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def drift_series(*, base: float = 100.0, per_session: float = 1.0) -> list[dict]:
    """Flat before the signal, steady drift after — the planted edge."""
    series = [bar(day, base, base, spread=0) for day in weekdays(date(2026, 6, 1), 20)]
    price = base
    for day in weekdays(SIGNAL_DATE + timedelta(days=1), 25):
        new_price = price + per_session
        series.append(bar(day, price, new_price, spread=0.5))
        price = new_price
    return series


def event(direction: int = 1, *, invalidation: list | None = None) -> dict:
    classification = "probable_accumulation" if direction > 0 else "probable_distribution"
    return {
        "ticker": "T",
        "signal_date": SIGNAL_DATE,
        "direction": direction,
        "classification": classification,
        "confidence": 0.6,
        "dpss": 65.0,
        "invalidation": invalidation or [],
        "unique_days": 4,
        "overlapping": False,
    }


def test_entry_is_next_session_open_and_horizon_math():
    closes = [101, 102, 103, 104, 105]
    series = [bar(SIGNAL_DATE, 100, 120, spread=0)]  # signal-day melt-up
    days = weekdays(SIGNAL_DATE + timedelta(days=1), 5)
    previous = 100.0
    for day, close in zip(days, closes, strict=True):
        series.append(
            {"date": day, "open": previous, "high": close + 1, "low": close - 2,
             "close": close}
        )
        previous = close

    measured = measure_event(event(), series, horizons=HORIZONS)
    assert measured["unmeasurable"] is None
    assert measured["entry_date"] == days[0]
    assert measured["entry_price"] == 100.0  # NOT the signal day's 120 close
    assert measured["returns"]["1"]["raw"] == pytest.approx(0.01)
    assert measured["returns"]["3"]["raw"] == pytest.approx(0.03)
    assert measured["returns"]["5"]["raw"] == pytest.approx(0.05)
    assert "20" not in measured["returns"]  # only 5 sessions exist: not faked
    assert measured["mfe"] == pytest.approx(0.06)   # best high: 106
    assert measured["mae"] == pytest.approx(-0.01)  # worst low: 99


def test_short_direction_mirrors_returns():
    closes = [99, 98, 97, 96, 95]
    series = []
    days = weekdays(SIGNAL_DATE + timedelta(days=1), 5)
    previous = 100.0
    for day, close in zip(days, closes, strict=True):
        series.append(
            {"date": day, "open": previous, "high": close + 1, "low": close - 2,
             "close": close}
        )
        previous = close
    measured = measure_event(event(direction=-1), series, horizons=HORIZONS)
    assert measured["returns"]["1"]["raw"] == pytest.approx(0.01)
    assert measured["returns"]["5"]["raw"] == pytest.approx(0.05)
    assert measured["mfe"] == pytest.approx(0.07)  # best low for a short: 93
    assert measured["mae"] == pytest.approx(0.0)   # worst high: 100 (entry level)


def test_lookahead_trap_yields_nothing():
    """A +20% move ON the signal day, flat afterwards: honest return ≈ 0."""
    series = [bar(SIGNAL_DATE, 100, 120, spread=0)]
    for day in weekdays(SIGNAL_DATE + timedelta(days=1), 21):
        series.append(bar(day, 120, 120, spread=0))
    measured = measure_event(event(), series, horizons=HORIZONS)
    for horizon in ("1", "3", "5", "20"):
        assert measured["returns"][horizon]["raw"] == pytest.approx(0.0, abs=1e-12)


def test_market_adjustment_subtracts_benchmark():
    days = weekdays(SIGNAL_DATE + timedelta(days=1), 5)
    series = []
    previous = 100.0
    for index, day in enumerate(days):
        close = 100 + index + 1
        series.append({"date": day, "open": previous, "high": close, "low": previous,
                       "close": close})
        previous = close
    flat_spy = {day: {"open": 100.0, "close": 100.0} for day in days}
    same_drift_spy = {
        day: {"open": bar_["open"], "close": bar_["close"]}
        for day, bar_ in zip(days, series, strict=True)
    }
    with_flat = measure_event(event(), series, horizons=[1, 3], spy_by_date=flat_spy)
    assert with_flat["returns"]["3"]["market_adj"] == pytest.approx(
        with_flat["returns"]["3"]["raw"]
    )
    with_drift = measure_event(
        event(), series, horizons=[1, 3], spy_by_date=same_drift_spy
    )
    assert with_drift["returns"]["3"]["market_adj"] == pytest.approx(0.0, abs=1e-12)


def test_invalidation_becomes_false_positive():
    days = weekdays(SIGNAL_DATE + timedelta(days=1), 5)
    closes = [101, 97, 99, 100, 101]  # breaches 98 on session 2
    series = []
    previous = 100.0
    for day, close in zip(days, closes, strict=True):
        series.append({"date": day, "open": previous, "high": close + 1,
                       "low": close - 1, "close": close})
        previous = close
    measured = measure_event(
        event(invalidation=[{"type": "daily_close_below", "level": 98.0}]),
        series,
        horizons=[1, 3, 5],
    )
    assert measured["invalidated_at_session"] == 2
    one_day = cohort_metrics([measured], 1, bootstrap_samples=50, seed=1)
    three_day = cohort_metrics([measured], 3, bootstrap_samples=50, seed=1)
    assert one_day["false_positive_rate"] == 0.0   # breach came after 1d exit
    assert three_day["false_positive_rate"] == 1.0


def insert_signal(conn, ticker: str, as_of: date, classification: str) -> None:
    conn.execute(signals.insert().values(
        ticker=ticker, as_of_date=as_of, classification=classification,
        confidence=0.6, dpss=65.0, sub_scores={}, evidence={},
        invalidation=[{"type": "daily_close_below", "level": 50.0}],
        top_zone={"unique_days": 4}, available_at=NOW,
    ))


def test_collect_events_overlap_control():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    ensure_schema(engine)
    with engine.begin() as conn:
        insert_signal(conn, "AAA", date(2026, 7, 1), "probable_accumulation")
        insert_signal(conn, "AAA", date(2026, 7, 8), "probable_accumulation")   # 5 sessions
        insert_signal(conn, "AAA", date(2026, 7, 9), "probable_distribution")  # other side
        insert_signal(conn, "AAA", date(2026, 8, 5), "possible_accumulation")  # 25 sessions
    with engine.connect() as conn:
        events = collect_events(conn, max_horizon=20)
    flags = [(e["signal_date"].isoformat(), e["direction"], e["overlapping"])
             for e in events]
    assert ("2026-07-01", 1, False) in flags
    assert ("2026-07-08", 1, True) in flags    # same side, inside the window
    assert ("2026-07-09", -1, False) in flags  # opposite side: independent
    assert ("2026-08-05", 1, False) in flags   # window expired


def test_bootstrap_is_deterministic_and_nulls_are_detected():
    values = [0.01, -0.01, 0.02, -0.02, 0.0, 0.01, -0.01]
    assert bootstrap_ci(values, samples=300, seed=7) == bootstrap_ci(
        values, samples=300, seed=7
    )
    events = [
        {
            "overlapping": False,
            "unmeasurable": None,
            "returns": {"1": {"raw": value, "market_adj": None, "sector_adj": None,
                              "vol_adj": None}},
            "mfe": abs(value),
            "mae": -abs(value),
            "invalidated_at_session": None,
            "segments": {"side": "accumulation"},
        }
        for value in values
    ]
    results, no_edge = aggregate_cohorts(
        events, horizons=[1], min_n=5, bootstrap_samples=300, seed=7
    )
    assert "all_directional" in no_edge  # mean ~0: honestly reported as no edge
    all_row = next(r for r in results if r["cohort"] == "all_directional")
    assert all_row["metrics"]["n"] == 7


def seed_candles(conn, ticker: str, series: list[dict]) -> None:
    conn.execute(
        candles.insert(),
        [
            {
                "ticker": ticker,
                "candle_size": "1d",
                "ts": datetime.combine(row["date"], datetime.min.time(), tzinfo=UTC),
                "open": row["open"],
                "high": row["high"],
                "low": row["low"],
                "close": row["close"],
                "volume": 1_000_000,
            }
            for row in series
        ],
    )


@pytest.fixture()
def seeded_engine():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    ensure_schema(engine)
    with engine.begin() as conn:
        spy = [bar(day, 100, 100, spread=0.5)
               for day in weekdays(date(2026, 6, 1), 50)]
        seed_candles(conn, "SPY", spy)
        for i in range(6):
            ticker = f"EDGE{i}"
            insert_signal(conn, ticker, SIGNAL_DATE, "probable_accumulation")
            seed_candles(conn, ticker, drift_series())
            conn.execute(symbols.insert().values(
                ticker=ticker, sector="Technology", issue_type="Common Stock",
                first_seen_at=NOW, last_seen_at=NOW,
            ))
        insert_signal(conn, "TRAP", SIGNAL_DATE, "probable_accumulation")
        trap = [bar(SIGNAL_DATE, 100, 120, spread=0)]
        trap += [bar(day, 120, 120, spread=0)
                 for day in weekdays(SIGNAL_DATE + timedelta(days=1), 25)]
        seed_candles(conn, "TRAP", trap)
        conn.execute(symbols.insert().values(
            ticker="TRAP", sector="Technology", issue_type="Common Stock",
            first_seen_at=NOW, last_seen_at=NOW,
        ))
    return engine


def test_run_backtest_finds_the_edge_but_not_the_trap(seeded_engine):
    run = run_backtest(seeded_engine, SETTINGS, now=NOW)
    summary = run["summary"]
    assert summary["events_total"] == 7
    assert summary["events_headline"] == 7
    assert summary["events_overlapping"] == 0

    all_rows = {
        row["horizon"]: row["metrics"]
        for row in run["results"]
        if row["cohort"] == "all_directional"
    }
    # Six drifting tickers +1%/session, one flat trap: clear positive edge.
    assert all_rows[5]["mean_return"] > 0.03
    assert all_rows[5]["ci_low"] > 0
    assert "all_directional" not in summary["no_edge_cohorts"]

    # The trap event itself earned nothing — the signal-day move was never
    # credited (look-ahead protection working).
    with seeded_engine.connect() as conn:
        trap_returns = conn.execute(
            sa.text("SELECT returns FROM backtest_events WHERE ticker = 'TRAP'")
        ).scalar()
    import json as _json

    parsed = _json.loads(trap_returns) if isinstance(trap_returns, str) else trap_returns
    assert parsed["5"]["raw"] == pytest.approx(0.0, abs=1e-12)

    report = render_backtest_report(run)
    assert run["config_hash"] in report
    assert "## No demonstrated edge" in report
    assert "intraday" in report.lower()  # the honesty disclosure is present


def test_backtest_api_endpoint(seeded_engine):
    run_backtest(seeded_engine, SETTINGS, now=NOW)
    app.dependency_overrides[get_engine] = lambda: seeded_engine
    app.dependency_overrides[get_settings] = lambda: SETTINGS
    try:
        body = TestClient(app).get("/backtest").json()
        assert body["summary"]["events_total"] == 7
        assert any(row["cohort"] == "all_directional" for row in body["results"])
        assert body["config_hash"]
    finally:
        app.dependency_overrides.clear()
