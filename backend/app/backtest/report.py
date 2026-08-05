"""The written backtest report (plan §16): what was tested, under which
config, what worked, and — explicitly — what did not."""

from __future__ import annotations

from typing import Any


def _pct(value: float | None) -> str:
    return f"{value * 100:+.2f}%" if value is not None else "n/a"


def render_backtest_report(run: dict[str, Any]) -> str:
    summary = run["summary"]
    lines = [
        "# Backtest report",
        "",
        f"Config hash: `{run['config_hash']}` — identical config + data "
        "reproduces identical numbers (seeded bootstrap).",
        "",
        "## Sample",
        f"- Events: {summary['events_total']} directional signals",
        f"- Headline (non-overlapping, measurable): {summary['events_headline']}",
        f"- Overlapping (excluded from headline, reported here): "
        f"{summary['events_overlapping']}",
        f"- Unmeasurable (no entry session yet): {summary['events_unmeasurable']}",
        "",
        "## Cohorts",
        "",
        "| cohort | horizon | n | hit rate | mean | 95% CI | mkt-adj | "
        "MFE | MAE | FP rate |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in run["results"]:
        metrics = row["metrics"]
        thin = " ⚠︎thin" if metrics.get("thin_sample") else ""
        lines.append(
            f"| {row['cohort']}{thin} | {row['horizon']}d | {metrics['n']} "
            f"| {metrics['hit_rate'] * 100:.0f}% "
            f"| {_pct(metrics['mean_return'])} "
            f"| [{_pct(metrics['ci_low'])}, {_pct(metrics['ci_high'])}] "
            f"| {_pct(metrics['mean_market_adj'])} "
            f"| {_pct(metrics['mean_mfe'])} | {_pct(metrics['mean_mae'])} "
            f"| {metrics['false_positive_rate'] * 100:.0f}% |"
        )
    lines += ["", "## No demonstrated edge"]
    if summary["no_edge_cohorts"]:
        lines.append(
            "These cohorts had enough data to judge and their confidence "
            "intervals do NOT exclude zero — treat their signals as "
            "unproven:"
        )
        lines += [f"- {name}" for name in summary["no_edge_cohorts"]]
    else:
        lines.append(
            "No cohort met the sample-size bar for a null verdict yet — "
            "which is itself a statement about sample size, not about edge."
        )
    lines += ["", "## Disclosures"]
    lines += [f"- {note}" for note in summary["notes"]]
    lines += ["", "_Probabilities, not promises._", ""]
    return "\n".join(lines)
