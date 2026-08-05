"""Backtesting: an event study over the immutable signals table (plan §16)."""

from app.backtest.engine import collect_events, measure_event, run_backtest
from app.backtest.report import render_backtest_report
from app.backtest.stats import aggregate_cohorts, cohort_metrics

__all__ = [
    "aggregate_cohorts",
    "cohort_metrics",
    "collect_events",
    "measure_event",
    "render_backtest_report",
    "run_backtest",
]
