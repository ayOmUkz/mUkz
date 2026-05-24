# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "yfinance>=0.2.40",
#     "pandas>=2.0",
#     "numpy>=1.26",
#     "hmmlearn>=0.3",
# ]
# ///
"""
Markov regime detection for any asset.

Framework: Roan (@RohOnChain). Refactored into a skill by Lewis Jackson.
Backtests are historical, not forward-looking.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

STATES = ["Bear", "Sideways", "Bull"]
BEAR, SIDEWAYS, BULL = 0, 1, 2
TRADING_DAYS = 252


def load_prices_from_ticker(ticker: str, years: int) -> pd.Series:
    import yfinance as yf

    end = datetime.utcnow()
    start = end - timedelta(days=int(years * 365.25) + 7)
    df = yf.download(
        ticker,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        auto_adjust=True,
        progress=False,
        threads=False,
    )
    if df is None or df.empty:
        raise RuntimeError(f"yfinance returned no data for {ticker!r}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    if "Close" not in df.columns:
        raise RuntimeError(f"no Close column in yfinance response for {ticker!r}")
    s = df["Close"].dropna().astype(float)
    s.index = pd.to_datetime(s.index)
    s.name = "close"
    return s


def load_prices_from_csv(path: str) -> pd.Series:
    df = pd.read_csv(path)
    if df.empty:
        raise RuntimeError(f"CSV {path!r} is empty")

    lower = {c.lower(): c for c in df.columns}
    date_aliases = ["date", "time", "timestamp", "datetime"]
    close_aliases = ["close", "adj close", "adjusted close", "price", "last"]

    date_col = next((lower[a] for a in date_aliases if a in lower), None)
    close_col = next((lower[a] for a in close_aliases if a in lower), None)

    if close_col is None:
        numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if len(numeric) == 1:
            close_col = numeric[0]
        else:
            raise RuntimeError(
                f"CSV {path!r}: could not find a close column; tried {close_aliases}"
            )

    if date_col is not None:
        idx = pd.to_datetime(df[date_col], errors="coerce")
    else:
        idx = pd.RangeIndex(len(df))

    s = pd.Series(df[close_col].astype(float).values, index=idx, name="close").dropna()
    if isinstance(s.index, pd.DatetimeIndex):
        s = s.sort_index()
    if s.empty:
        raise RuntimeError(f"CSV {path!r}: no usable rows after cleaning")
    return s


def label_states(prices: pd.Series, window: int, threshold: float) -> np.ndarray:
    """
    Trailing rolling return classifier:
        r_t = price_t / price_{t-window} - 1
        state = Bear if r < -thr, Bull if r > thr, else Sideways
    Bars with t < window get -1 (unlabelled).
    """
    p = prices.values.astype(float)
    n = len(p)
    states = np.full(n, -1, dtype=int)
    if n <= window:
        return states
    r = p[window:] / p[:-window] - 1.0
    s = np.full_like(r, SIDEWAYS, dtype=int)
    s[r > threshold] = BULL
    s[r < -threshold] = BEAR
    states[window:] = s
    return states


def transition_matrix(states: np.ndarray, k: int = 3) -> np.ndarray:
    """Row-stochastic 3x3 transition matrix from a labelled state sequence."""
    valid = states[states >= 0]
    M = np.zeros((k, k), dtype=float)
    if len(valid) < 2:
        return _row_normalise(M)
    a = valid[:-1]
    b = valid[1:]
    np.add.at(M, (a, b), 1.0)
    return _row_normalise(M)


def _row_normalise(M: np.ndarray) -> np.ndarray:
    out = M.copy()
    sums = out.sum(axis=1, keepdims=True)
    zero = (sums == 0).flatten()
    out[~zero] = out[~zero] / sums[~zero]
    out[zero] = 1.0 / out.shape[1]
    return out


def stationary_distribution(M: np.ndarray) -> np.ndarray:
    """Left eigenvector of M with eigenvalue 1, normalised to sum to 1."""
    vals, vecs = np.linalg.eig(M.T)
    idx = int(np.argmin(np.abs(vals - 1.0)))
    v = np.real(vecs[:, idx])
    v = np.abs(v)
    s = v.sum()
    if s == 0 or not np.isfinite(s):
        return np.full(M.shape[0], 1.0 / M.shape[0])
    return v / s


def walk_forward(
    prices: pd.Series, states: np.ndarray, min_train: int
) -> dict:
    """
    No-lookahead walk-forward.

    At each step t we use only states[:t] to fit the transition matrix, look up
    the current state s = states[t-1], take position = sign(P(bull|s) - P(bear|s)),
    then realise the return from t-1 -> t.

    Incremental count update keeps this O(n).
    """
    p = prices.values.astype(float)
    n = len(p)
    rets = np.zeros(n, dtype=float)
    rets[1:] = p[1:] / p[:-1] - 1.0

    counts = np.zeros((3, 3), dtype=float)
    # Seed counts with transitions inside [0, min_train).
    valid_idx = np.where(states[:min_train] >= 0)[0]
    if len(valid_idx) >= 2:
        seq = states[valid_idx]
        consec = (np.diff(valid_idx) == 1)
        a = seq[:-1][consec]
        b = seq[1:][consec]
        np.add.at(counts, (a, b), 1.0)

    pnl: list[float] = []
    trades = 0
    last_pos = 0
    last_valid_state = states[min_train - 1] if min_train > 0 else -1

    for t in range(min_train, n):
        # Use only info up to t-1.
        prev = states[t - 1]
        prev_prev = states[t - 2] if t >= 2 else -1
        if prev >= 0 and prev_prev >= 0:
            counts[prev_prev, prev] += 1.0

        if prev < 0:
            pos = 0
        else:
            row = counts[prev]
            s = row.sum()
            if s == 0:
                pos = 0
            else:
                probs = row / s
                signal = probs[BULL] - probs[BEAR]
                pos = 1 if signal > 0 else (-1 if signal < 0 else 0)

        pnl.append(pos * rets[t])
        if pos != last_pos:
            trades += 1
            last_pos = pos
        if prev >= 0:
            last_valid_state = prev

    pnl_arr = np.array(pnl, dtype=float)
    sharpe = float("nan")
    if pnl_arr.size > 1 and pnl_arr.std(ddof=1) > 0:
        sharpe = float(pnl_arr.mean() / pnl_arr.std(ddof=1) * math.sqrt(TRADING_DAYS))

    max_dd = float("nan")
    if pnl_arr.size > 0:
        equity = np.cumprod(1.0 + pnl_arr)
        peak = np.maximum.accumulate(equity)
        dd = equity / peak - 1.0
        max_dd = float(dd.min())

    return {
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "n_trades": int(trades),
    }


def hmm_block(prices: pd.Series, use_hmm: bool) -> dict:
    if not use_hmm:
        return {"available": False, "reason": "disabled with --no-hmm"}
    try:
        from hmmlearn.hmm import GaussianHMM
    except Exception as e:  # noqa: BLE001
        return {"available": False, "reason": f"hmmlearn unavailable: {e.__class__.__name__}: {e}"}

    rets = (prices.pct_change().dropna().values).reshape(-1, 1)
    if len(rets) < 50:
        return {"available": False, "reason": f"only {len(rets)} returns, need >=50"}
    try:
        model = GaussianHMM(n_components=3, covariance_type="full", n_iter=200, random_state=0)
        model.fit(rets)
    except Exception as e:  # noqa: BLE001
        return {"available": False, "reason": f"HMM fit failed: {e.__class__.__name__}: {e}"}

    means = model.means_.flatten()
    order = np.argsort(means)  # ascending mean return
    labels = ["Bear", "Sideways", "Bull"]
    regimes = []
    for label, latent in zip(labels, order):
        regimes.append({
            "label": label,
            "latent_state": int(latent),
            "mean_daily_return": float(means[latent]),
        })
    return {
        "available": True,
        "regimes": regimes,
        "caveat": (
            "HMM states are labelled by ascending mean return; a positive 'Bear' mean "
            "just means the worst latent state was still net-positive over this window."
        ),
    }


@dataclass
class Result:
    data: dict


def analyse(
    prices: pd.Series,
    source: str,
    window: int,
    threshold: float,
    min_train: int,
    use_hmm: bool,
) -> dict:
    if len(prices) < window + 5:
        raise RuntimeError(
            f"need at least window+5 = {window + 5} bars, got {len(prices)}"
        )

    states = label_states(prices, window=window, threshold=threshold)
    M = transition_matrix(states)
    pi = stationary_distribution(M)

    current = int(states[-1])
    if current < 0:
        # Fall back to the most recent labelled bar.
        labelled = np.where(states >= 0)[0]
        current = int(states[labelled[-1]]) if len(labelled) else SIDEWAYS

    row = M[current]
    signal = float(row[BULL] - row[BEAR])

    wf = walk_forward(prices, states, min_train=max(min_train, window + 2))

    out = {
        "source": source,
        "rows": int(len(prices)),
        "date_start": (
            prices.index[0].strftime("%Y-%m-%d")
            if isinstance(prices.index, pd.DatetimeIndex)
            else str(prices.index[0])
        ),
        "date_end": (
            prices.index[-1].strftime("%Y-%m-%d")
            if isinstance(prices.index, pd.DatetimeIndex)
            else str(prices.index[-1])
        ),
        "params": {
            "window": int(window),
            "threshold": float(threshold),
            "min_train": int(min_train),
        },
        "states": STATES,
        "current_regime": STATES[current],
        "next_state_probabilities": {
            "bear": float(row[BEAR]),
            "sideways": float(row[SIDEWAYS]),
            "bull": float(row[BULL]),
        },
        "signal": signal,
        "transition_matrix": [[float(x) for x in r] for r in M],
        "persistence_diagonal": {
            "bear": float(M[BEAR, BEAR]),
            "sideways": float(M[SIDEWAYS, SIDEWAYS]),
            "bull": float(M[BULL, BULL]),
        },
        "stationary_distribution": {
            "bear": float(pi[BEAR]),
            "sideways": float(pi[SIDEWAYS]),
            "bull": float(pi[BULL]),
        },
        "walk_forward": wf,
        "hmm": hmm_block(prices, use_hmm=use_hmm),
        "framework": "Roan (@RohOnChain)",
        "disclaimer": "Backtests are historical, not forward-looking.",
    }
    return out


def pretty_print(r: dict) -> None:
    print(f"\nRegime — {r['source']}  ({r['date_start']} → {r['date_end']}, {r['rows']} rows)")
    print(f"  window={r['params']['window']}  threshold=±{r['params']['threshold']:.2%}  "
          f"min_train={r['params']['min_train']}")
    print(f"\n  Current regime : {r['current_regime']}")
    nsp = r["next_state_probabilities"]
    print(f"  P(next | now)  : Bear {nsp['bear']:.2%}   "
          f"Sideways {nsp['sideways']:.2%}   Bull {nsp['bull']:.2%}")
    print(f"  Signal (bull−bear): {r['signal']:+.3f}")

    print("\n  Transition matrix  (rows = from, cols = to)")
    print(f"            {'Bear':>8} {'Sideways':>10} {'Bull':>8}")
    for i, name in enumerate(STATES):
        row = r["transition_matrix"][i]
        print(f"    {name:<8}  {row[0]:>7.2%}  {row[1]:>9.2%}  {row[2]:>7.2%}")

    pd_ = r["persistence_diagonal"]
    print(f"\n  Persistence diag  : Bear {pd_['bear']:.2%}   "
          f"Sideways {pd_['sideways']:.2%}   Bull {pd_['bull']:.2%}")

    sd = r["stationary_distribution"]
    print(f"  Stationary mix    : Bear {sd['bear']:.2%}   "
          f"Sideways {sd['sideways']:.2%}   Bull {sd['bull']:.2%}")

    wf = r["walk_forward"]
    sh = wf["sharpe"]
    dd = wf["max_drawdown"]
    sh_s = f"{sh:+.2f}" if isinstance(sh, float) and not math.isnan(sh) else "NaN"
    dd_s = f"{dd:.2%}" if isinstance(dd, float) and not math.isnan(dd) else "NaN"
    print(f"\n  Walk-forward      : Sharpe {sh_s}   MaxDD {dd_s}   trades {wf['n_trades']}")

    hmm = r["hmm"]
    if hmm.get("available"):
        parts = [f"{x['label']}={x['mean_daily_return']*100:+.3f}%/d" for x in hmm["regimes"]]
        print(f"  HMM (3-state)     : {'  '.join(parts)}")
    else:
        print(f"  HMM (3-state)     : unavailable ({hmm.get('reason','')})")

    print(f"\n  Framework: {r['framework']}")
    print(f"  {r['disclaimer']}\n")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Markov regime detection for any asset.")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--ticker", type=str, help="yfinance ticker, e.g. BTC-USD, PLTR, SPY")
    src.add_argument("--csv", type=str, help="CSV with date + close columns")
    p.add_argument("--window", type=int, default=20)
    p.add_argument("--threshold", type=float, default=0.05)
    p.add_argument("--years", type=int, default=10)
    p.add_argument("--min-train", dest="min_train", type=int, default=252)
    p.add_argument("--no-hmm", dest="use_hmm", action="store_false")
    p.add_argument("--json", dest="as_json", action="store_true")
    args = p.parse_args(argv)

    try:
        if args.ticker:
            prices = load_prices_from_ticker(args.ticker, years=args.years)
            source = args.ticker
        else:
            prices = load_prices_from_csv(args.csv)
            source = str(Path(args.csv).resolve())

        result = analyse(
            prices=prices,
            source=source,
            window=args.window,
            threshold=args.threshold,
            min_train=args.min_train,
            use_hmm=args.use_hmm,
        )
    except Exception as e:  # noqa: BLE001
        msg = {"error": f"{e.__class__.__name__}: {e}"}
        print(json.dumps(msg))
        return 1

    if args.as_json:
        print(json.dumps(result))
    else:
        pretty_print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
