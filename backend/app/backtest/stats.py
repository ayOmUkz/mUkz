"""Cohort statistics for the backtest (plan §16).

Every cohort reports its sample size and a bootstrap confidence interval —
no cohort speaks without saying how much data is behind it. The bootstrap
is seeded, so re-running a study yields identical intervals.
"""

from __future__ import annotations

import random
from statistics import fmean, median
from typing import Any


def bootstrap_ci(
    values: list[float], *, samples: int, seed: int, alpha: float = 0.05
) -> tuple[float, float]:
    """Percentile bootstrap CI for the mean (deterministic given the seed)."""
    rng = random.Random(seed)
    means = sorted(
        fmean(rng.choices(values, k=len(values))) for _ in range(samples)
    )
    lower = means[int(alpha / 2 * samples)]
    upper = means[min(samples - 1, int((1 - alpha / 2) * samples))]
    return lower, upper


def cohort_metrics(
    events: list[dict[str, Any]],
    horizon: int,
    *,
    bootstrap_samples: int,
    seed: int,
) -> dict[str, Any] | None:
    """Metrics for one cohort at one horizon; None when nothing measured."""
    key = str(horizon)
    rows = [
        event
        for event in events
        if event.get("returns") and key in event["returns"]
    ]
    if not rows:
        return None
    raw = [event["returns"][key]["raw"] for event in rows]
    market = [
        event["returns"][key]["market_adj"]
        for event in rows
        if event["returns"][key]["market_adj"] is not None
    ]
    vol = [
        event["returns"][key]["vol_adj"]
        for event in rows
        if event["returns"][key]["vol_adj"] is not None
    ]
    ci_low, ci_high = bootstrap_ci(raw, samples=bootstrap_samples, seed=seed)
    false_positives = sum(
        1
        for event in rows
        if event.get("invalidated_at_session") is not None
        and event["invalidated_at_session"] < horizon
    )
    return {
        "n": len(rows),
        "hit_rate": round(sum(1 for value in raw if value > 0) / len(raw), 4),
        "mean_return": round(fmean(raw), 6),
        "median_return": round(median(raw), 6),
        "ci_low": round(ci_low, 6),
        "ci_high": round(ci_high, 6),
        "mean_market_adj": round(fmean(market), 6) if market else None,
        "mean_vol_adj": round(fmean(vol), 4) if vol else None,
        "mean_mfe": round(fmean([event["mfe"] for event in rows]), 6),
        "mean_mae": round(fmean([event["mae"] for event in rows]), 6),
        "worst_mae": round(min(event["mae"] for event in rows), 6),
        "false_positive_rate": round(false_positives / len(rows), 4),
    }


def aggregate_cohorts(
    measured: list[dict[str, Any]],
    *,
    horizons: list[int],
    min_n: int,
    bootstrap_samples: int,
    seed: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    """(result rows, cohorts with no demonstrated edge).

    Headline cohorts exclude overlapping and unmeasurable events (plan §16
    bias controls). A cohort lands on the "no edge" list when its sample is
    big enough to judge AND its confidence interval fails to exclude zero —
    null results are published, not buried.
    """
    headline = [
        event
        for event in measured
        if not event["overlapping"] and event.get("unmeasurable") is None
    ]

    cohorts: dict[str, list[dict[str, Any]]] = {"all_directional": headline}
    for event in headline:
        for segment_key, segment_value in event.get("segments", {}).items():
            if segment_key == "classification":
                cohorts.setdefault(segment_value, []).append(event)
            else:
                cohorts.setdefault(f"{segment_key}:{segment_value}", []).append(event)

    results: list[dict[str, Any]] = []
    no_edge: list[str] = []
    for cohort_name, events in sorted(cohorts.items()):
        judged_any = False
        edge_somewhere = False
        for horizon in horizons:
            metrics = cohort_metrics(
                events, horizon, bootstrap_samples=bootstrap_samples, seed=seed
            )
            if metrics is None:
                continue
            metrics["thin_sample"] = metrics["n"] < min_n
            results.append(
                {"cohort": cohort_name, "horizon": horizon, "metrics": metrics}
            )
            if not metrics["thin_sample"]:
                judged_any = True
                if metrics["ci_low"] > 0:
                    edge_somewhere = True
        if judged_any and not edge_somewhere:
            no_edge.append(cohort_name)
    return results, no_edge
