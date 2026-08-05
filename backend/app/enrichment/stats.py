"""Per-symbol dark-print size distributions (robust statistics).

A whale print in a sleepy utility is a minnow print in NVDA, so every
symbol is measured against its *own* history. Print sizes are heavy-tailed,
which is why the summary uses median/MAD and high percentiles instead of
mean/standard deviation (plan §7).
"""

from __future__ import annotations

from statistics import median
from typing import Any


def percentile(sorted_values: list[float], pct: float) -> float:
    """Linear-interpolated percentile (pct in [0, 100]) of a sorted sample."""
    if not sorted_values:
        raise ValueError("empty sample")
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (pct / 100.0) * (len(sorted_values) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = rank - lower
    return sorted_values[lower] * (1 - fraction) + sorted_values[upper] * fraction


def size_distribution(sizes: list[int]) -> dict[str, Any]:
    """Summarize a sample of print sizes for the ``symbol_stats`` table."""
    if not sizes:
        return {"sample_size": 0, "p50": None, "p90": None, "p99": None, "p999": None,
                "mad": None}
    ordered = sorted(float(s) for s in sizes)
    p50 = percentile(ordered, 50)
    absolute_deviations = sorted(abs(value - p50) for value in ordered)
    return {
        "sample_size": len(ordered),
        "p50": p50,
        "p90": percentile(ordered, 90),
        "p99": percentile(ordered, 99),
        "p999": percentile(ordered, 99.9),
        "mad": median(absolute_deviations),
    }


def approx_percentile_of(size: float, stats: dict[str, Any]) -> float | None:
    """Rough percentile estimate of ``size`` from stored breakpoints.

    Piecewise-linear between (p50, 50) → (p90, 90) → (p99, 99) →
    (p999, 99.9). An estimate for display/scoring context — classification
    itself compares directly against the breakpoints.
    """
    breakpoints = [(stats.get("p50"), 50.0), (stats.get("p90"), 90.0),
                   (stats.get("p99"), 99.0), (stats.get("p999"), 99.9)]
    if any(value is None for value, _ in breakpoints):
        return None
    p50v = breakpoints[0][0]
    if size <= p50v:
        return round(50.0 * (size / p50v), 2) if p50v > 0 else None
    previous_value, previous_pct = breakpoints[0]
    for value, pct in breakpoints[1:]:
        if size <= value:
            span = value - previous_value
            if span <= 0:
                return round(pct, 2)
            fraction = (size - previous_value) / span
            return round(previous_pct + fraction * (pct - previous_pct), 2)
        previous_value, previous_pct = value, pct
    return 99.9
