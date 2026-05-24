#!/usr/bin/env python3
"""Markov-chain transition-matrix analysis for a single ticker."""
from __future__ import annotations

import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import yfinance as yf

STATE_LABELS = ["down-big", "down", "flat", "up", "up-big"]
N_STATES = 5


def classify_returns(returns: np.ndarray, sigma: float) -> np.ndarray:
    thresholds = np.array([-1.5, -0.5, 0.5, 1.5]) * sigma
    return np.digitize(returns, thresholds)


def state_midpoints(sigma: float) -> np.ndarray:
    return np.array([-2.0, -1.0, 0.0, 1.0, 2.0]) * sigma


def transition_matrix(states: np.ndarray, n: int = N_STATES) -> np.ndarray:
    M = np.zeros((n, n))
    for a, b in zip(states[:-1], states[1:]):
        M[a, b] += 1
    row_sums = M.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0
    return M / row_sums


def fmt_pct(x: float) -> str:
    return f"{x * 100:+.2f}%"


def fmt_pct_abs(x: float) -> str:
    return f"{x * 100:.2f}%"


def fmt_prob(x: float) -> str:
    return f"{x * 100:.1f}%"


def main(ticker: str) -> int:
    ticker = ticker.upper()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"# Markov Hedge Fund Method — {ticker}")
    print(f"_Generated {now}_\n")

    df = yf.download(ticker, period="5y", interval="1d", progress=False, auto_adjust=True)
    if df is None or df.empty:
        print(f"**Error:** No data returned for `{ticker}`. Check the symbol.")
        return 1

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    close = df["Close"].dropna()
    if len(close) < 100:
        print(f"**Error:** Only {len(close)} trading days of data — need at least 100.")
        return 1

    log_returns = np.log(close / close.shift(1)).dropna().to_numpy()
    sigma = float(log_returns.std())
    mean = float(log_returns.mean())

    states = classify_returns(log_returns, sigma)
    M = transition_matrix(states)
    current_state = int(states[-1])
    next_dist = M[current_state]
    midpoints = state_midpoints(sigma)
    expected_next = float(next_dist @ midpoints)
    variance_next = float(next_dist @ (midpoints - expected_next) ** 2)
    std_next = float(np.sqrt(variance_next))

    last_date = close.index[-1].date()
    last_price = float(close.iloc[-1])
    last_return = float(log_returns[-1])
    n_years = len(log_returns) / 252.0

    print("## Snapshot")
    print(f"- **Latest close ({last_date}):** ${last_price:,.2f}")
    print(f"- **Last log return:** {fmt_pct(last_return)}")
    print(f"- **Sample:** {len(log_returns):,} daily returns (~{n_years:.1f} years)")
    print(f"- **Realized daily σ:** {fmt_pct_abs(sigma)}  |  **Mean daily return:** {fmt_pct(mean)}")
    print(f"- **Current state:** **{STATE_LABELS[current_state]}**\n")

    print("## State definitions")
    print(f"States bucket daily log returns relative to realized σ = {fmt_pct_abs(sigma)}:\n")
    thr_labels = [
        f"r < {fmt_pct(-1.5 * sigma)}",
        f"{fmt_pct(-1.5 * sigma)} ≤ r < {fmt_pct(-0.5 * sigma)}",
        f"{fmt_pct(-0.5 * sigma)} ≤ r < {fmt_pct(0.5 * sigma)}",
        f"{fmt_pct(0.5 * sigma)} ≤ r < {fmt_pct(1.5 * sigma)}",
        f"r ≥ {fmt_pct(1.5 * sigma)}",
    ]
    print("| State | Threshold | Midpoint |")
    print("|---|---|---|")
    for label, thr, mid in zip(STATE_LABELS, thr_labels, midpoints):
        print(f"| {label} | {thr} | {fmt_pct(mid)} |")
    print()

    print("## Transition matrix P(next | current)\n")
    header = "| from \\ to | " + " | ".join(STATE_LABELS) + " |"
    sep = "|---|" + "|".join(["---"] * N_STATES) + "|"
    print(header)
    print(sep)
    for i, label in enumerate(STATE_LABELS):
        row = "| " + label + " | " + " | ".join(fmt_prob(M[i, j]) for j in range(N_STATES)) + " |"
        print(row)
    print()

    state_counts = np.bincount(states, minlength=N_STATES)
    print("## State occupancy (unconditional)\n")
    print("| State | Days | Frequency |")
    print("|---|---|---|")
    total = int(state_counts.sum())
    for label, cnt in zip(STATE_LABELS, state_counts):
        print(f"| {label} | {int(cnt):,} | {fmt_prob(cnt / total)} |")
    print()

    print(f"## Next-day forecast (conditional on **{STATE_LABELS[current_state]}**)\n")
    print("| State | Probability |")
    print("|---|---|")
    for j, label in enumerate(STATE_LABELS):
        print(f"| {label} | {fmt_prob(next_dist[j])} |")
    print()
    print(f"- **Expected next-day log return:** {fmt_pct(expected_next)}")
    print(f"- **Conditional σ:** {fmt_pct_abs(std_next)}")

    threshold = 0.25 * sigma
    if expected_next > threshold:
        position = "LONG"
        sharpe = expected_next / std_next if std_next > 0 else 0.0
        rationale = (
            f"E[r] of {fmt_pct(expected_next)} exceeds the +0.25σ entry threshold "
            f"({fmt_pct(threshold)}). Conditional one-day Sharpe ≈ {sharpe:.2f}. "
            f"From the `{STATE_LABELS[current_state]}` state, the transition matrix "
            f"weights the next-day distribution toward positive outcomes."
        )
    elif expected_next < -threshold:
        position = "SHORT"
        sharpe = -expected_next / std_next if std_next > 0 else 0.0
        rationale = (
            f"E[r] of {fmt_pct(expected_next)} is below the −0.25σ entry threshold "
            f"({fmt_pct(-threshold)}). Conditional one-day Sharpe ≈ {sharpe:.2f}. "
            f"From the `{STATE_LABELS[current_state]}` state, the transition matrix "
            f"weights the next-day distribution toward negative outcomes."
        )
    else:
        position = "FLAT"
        rationale = (
            f"|E[r]| of {fmt_pct_abs(expected_next)} is within ±0.25σ "
            f"({fmt_pct_abs(threshold)}) of zero. No edge worth a position after "
            f"transaction costs and slippage."
        )

    print()
    print(f"## Recommendation: **{position}**\n")
    print(f"{rationale}\n")

    print("---")
    print(
        "_Disclaimer: an empirical 1-day Markov chain assumes stationarity and ignores "
        "vol clustering, news, microstructure, gaps, and execution. Educational tool, "
        "not investment advice._"
    )
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: markov.py <TICKER>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
