"""Tests for zone clustering, metrics, strength, and status tracking."""

import random
from datetime import UTC, datetime
from decimal import Decimal

from app.analytics.zones import (
    cluster_prints,
    eligible_prints,
    epsilon_for,
    sessions_between,
    strength_class,
    strength_score,
    track_zone_status,
    zone_metrics,
)
from app.config import ZoneEpsilonConfig, ZonesConfig

CFG = ZonesConfig()


def make_print(price: str, size: int = 1000, executed: str = "2026-08-05T15:00:00Z",
               size_class: str = "elevated", character: str = "routine_off_exchange",
               avg30: str = "1000000") -> dict:
    return {
        "price": Decimal(price),
        "size": size,
        "premium": Decimal(price) * size,
        "executed_at": datetime.fromisoformat(executed),
        "size_class": size_class,
        "character": character,
        "avg30_volume": Decimal(avg30),
    }


def bar(day: int, low: float, high: float, close: float, volume: int = 1000) -> dict:
    return {
        "ts": datetime(2026, 8, day, 0, 0, tzinfo=UTC),
        "low": Decimal(str(low)),
        "high": Decimal(str(high)),
        "close": Decimal(str(close)),
        "volume": volume,
    }


def test_epsilon_is_max_of_three_knobs():
    config = ZoneEpsilonConfig()
    assert epsilon_for(Decimal("100"), None, config) == Decimal("0.15")  # 0.15% of price
    assert epsilon_for(Decimal("100"), 2.0, config) == Decimal("0.5")   # 0.25 x ATR wins
    assert epsilon_for(Decimal("1"), None, config) == Decimal("0.02")   # 2 ticks floor


def test_eligible_prints_filters_normal_and_odd_lots():
    rows = [
        make_print("100"),
        make_print("100", size_class="normal"),
        make_print("100", character="odd_lot"),
        make_print("100", size_class="extreme"),
    ]
    assert len(eligible_prints(rows)) == 2


def test_clustering_groups_within_tolerance():
    rows = [make_print("100.00"), make_print("100.10"), make_print("100.05"),
            make_print("105.00")]
    clusters = cluster_prints(rows, atr=1.0, config=ZoneEpsilonConfig())  # eps 0.25
    assert [len(c) for c in clusters] == [3, 1]
    assert clusters[1][0]["price"] == Decimal("105.00")


def test_clustering_is_permutation_invariant():
    rows = [make_print(p) for p in ("100.00", "100.10", "100.05", "105.00", "104.90")]
    baseline = cluster_prints(rows, atr=1.0, config=ZoneEpsilonConfig())
    shuffled = rows[:]
    random.Random(7).shuffle(shuffled)
    again = cluster_prints(shuffled, atr=1.0, config=ZoneEpsilonConfig())
    as_sets = lambda cs: sorted(sorted(str(r["price"]) for r in c) for c in cs)  # noqa: E731
    assert as_sets(baseline) == as_sets(again)


def test_bigger_epsilon_never_yields_more_clusters():
    rows = [make_print(str(100 + i * 0.2)) for i in range(10)]
    tight = cluster_prints(rows, atr=0.1, config=ZoneEpsilonConfig())
    loose = cluster_prints(rows, atr=5.0, config=ZoneEpsilonConfig())
    assert len(loose) <= len(tight)


def test_zone_metrics_weighted_average_and_days():
    rows = [
        make_print("100.00", size=600, executed="2026-08-03T15:00:00Z"),
        make_print("101.00", size=400, executed="2026-08-05T15:00:00Z"),
    ]
    metrics = zone_metrics(
        rows, as_of=datetime(2026, 8, 5, tzinfo=UTC).date(), atr=2.0,
        window_total_shares=2000,
    )
    assert metrics["wavg_price"] == Decimal("100.400000")
    assert metrics["total_shares"] == 1000
    assert metrics["unique_days"] == 2
    assert metrics["pct_adv30"] == 0.001            # 1000 / 1,000,000
    assert metrics["pct_dark_volume"] == 0.5        # 1000 / 2000
    assert metrics["tightness_atr"] == 0.5          # $1 width / 2.0 ATR
    assert metrics["sessions_since_last"] == 0


def test_sessions_between_skips_weekends():
    # Wed Aug 5 -> Mon Aug 10: Thu, Fri, Mon = 3 sessions.
    assert sessions_between(datetime(2026, 8, 5).date(), datetime(2026, 8, 10).date()) == 3
    assert sessions_between(datetime(2026, 8, 5).date(), datetime(2026, 8, 5).date()) == 0


def full_marks_metrics() -> dict:
    return {
        "pct_adv30": 0.05,
        "unique_days": 5,
        "sessions_since_last": 0,
        "tightness_atr": 0.4,
        "pct_dark_volume": 1.0,
        "wavg_price": Decimal("100"),
    }


def test_strength_score_full_marks_and_class():
    score, components = strength_score(
        full_marks_metrics(),
        {"status": "respected", "respected_touches": 2},
        weights=CFG.strength_weights,
        config=CFG,
    )
    assert score == 100.0
    assert components == {"pct_adv30": 30.0, "recurrence": 20.0, "recency": 15.0,
                          "tightness": 10.0, "concentration": 10.0, "reactions": 15.0}
    assert strength_class(score) == "exceptional"
    assert strength_class(70) == "strong"
    assert strength_class(50) == "moderate"
    assert strength_class(10) == "weak"


def test_strength_score_broken_zone_loses_reaction_points():
    _, components = strength_score(
        full_marks_metrics(),
        {"status": "broken", "respected_touches": 0},
        weights=CFG.strength_weights,
        config=CFG,
    )
    assert components["reactions"] == 0.0


ZONE = {
    "price_low": Decimal("99"),
    "price_high": Decimal("101"),
    "wavg_price": Decimal("100"),
    "first_print_at": datetime(2026, 8, 5, 15, 0, tzinfo=UTC),
}


def test_status_respected_then_broken_then_reclaimed():
    # ATR 2 -> respect/break thresholds of 1.0 beyond the zone edges.
    bars = [
        bar(6, 102, 104, 103),      # above, no touch
        bar(7, 100.5, 103, 102.5),  # touch, closes >= 102 -> respected
        bar(10, 97, 102, 97.5),     # touch + close <= 98 -> broken downward
        bar(11, 100, 103, 101.5),   # closes back above the zone -> reclaimed
    ]
    result = track_zone_status(ZONE, bars, atr=2.0, config=CFG)
    assert result["status"] == "reclaimed"
    assert result["respected_touches"] == 1
    # The reclaiming bar also overlaps the zone, so it logs its own touch.
    assert [e["event"] for e in result["events"]] == [
        "touch", "reject", "touch", "break", "reclaim", "touch",
    ]


def test_status_untested_when_price_never_returns():
    bars = [bar(6, 102, 104, 103), bar(7, 103, 105, 104)]
    result = track_zone_status(ZONE, bars, atr=2.0, config=CFG)
    assert result["status"] == "untested"
    assert result["events"] == []


def test_status_broken_stays_broken_outside_reclaim_window():
    bars = [
        bar(6, 102, 104, 103),     # establish side: above
        bar(7, 96, 102, 97.0),     # touch + break down
        bar(10, 95, 96.5, 96),     # below ...
        bar(11, 95, 96.5, 96),
        bar(12, 95, 96.5, 96),
        bar(13, 100, 103, 102),    # back above, but window (3 sessions) passed
    ]
    result = track_zone_status(ZONE, bars, atr=2.0, config=CFG)
    assert result["status"] == "broken"
    assert result["break_to"] == "below"


def test_status_ignores_bars_before_zone_formed():
    earlier = [bar(3, 99, 101, 100)]  # would be a touch, but zone formed Aug 5
    result = track_zone_status(ZONE, earlier, atr=2.0, config=CFG)
    assert result["status"] == "untested"
