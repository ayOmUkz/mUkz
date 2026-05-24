---
description: Markov regime detection (Bull/Sideways/Bear) for any asset — transition matrix, stationary mix, no-lookahead walk-forward, optional HMM cross-check
argument-hint: <ticker-or-csv> [extra flags]
allowed-tools: Bash
---

Run the Markov regime detection method on the asset described in `$ARGUMENTS`.

Step 1 — pick the right invocation:
- If `$ARGUMENTS` looks like a path or ends in `.csv`, run with `--csv`.
- Otherwise treat the first token as a yfinance ticker (e.g. `PLTR`, `ES=F`, `BTC-USD`) and run with `--ticker`.
- Pass any additional tokens through verbatim (e.g. `--window 10 --threshold 0.02 --no-hmm`).

Step 2 — execute (pretty output, then JSON for structured fields):

```bash
uv run scripts/markov_hedge_fund_method.py --ticker <TICKER> [extra flags]
# or
uv run scripts/markov_hedge_fund_method.py --csv <PATH> [extra flags]
```

Run once without `--json` so the user sees the on-camera matrix, then once with `--json` if you need the structured numbers to reason from.

Step 3 — interpret using the framework's three composition patterns, in this order:

1. **Current regime + signal**: state the current regime, `signal = bull_prob − bear_prob`, and what the next-step probabilities are. Call out signal magnitude (>0.5 strong, 0.1–0.5 mild, <0.1 noise).
2. **Stickiness**: read the persistence diagonal. Note any structurally impossible transitions (e.g. Bear → Bull in one step is often 0%).
3. **Stationary mix**: long-run baseline shares. Flag if `bear_baseline > 0.30` — that asset is structurally tail-heavy and any sizing layer should haircut.
4. **Walk-forward sanity check**: Sharpe + max drawdown + trade count from the no-lookahead backtest. Be honest if the standalone strategy isn't tradeable — this method is usually a gate, not a signal.
5. **HMM cross-check**: if `hmm.available`, report the three mean daily returns. If the latent means collapse (Bear ≈ Sideways), say so — the rule-based labels still hold but the HMM isn't adding info.

Step 4 — close with the practical takeaway across the three composition patterns:
- **(a) Confirmation** on an existing strategy: does the regime agree?
- **(b) Sizing**: `base * (1 − bear_baseline)`
- **(c) Standalone**: only if walk-forward Sharpe and DD are acceptable.

Framework: Roan (@RohOnChain). Backtests are historical, not forward-looking.
