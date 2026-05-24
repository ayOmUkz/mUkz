---
description: Markov-chain transition matrix trading signal for a stock ticker
argument-hint: <TICKER>
allowed-tools: Bash
---

Run a one-day Markov-chain transition-matrix analysis for ticker `$ARGUMENTS`.

If `$ARGUMENTS` is empty, ask the user for a ticker symbol and stop — do not proceed.

Otherwise, run exactly:

```
bash .claude/skills/markov-hedge-fund-method/run.sh $ARGUMENTS
```

The first invocation in a fresh session takes ~30 seconds because the script builds a
local `.venv/` and installs `yfinance`, `pandas`, and `numpy`. Subsequent invocations
in the same session reuse the venv and run in under a second. If pip or Yahoo Finance
is blocked by the network policy, the script will error — surface that error to the
user rather than fabricating output.

Print the script's stdout verbatim — it's a self-contained markdown report covering
the snapshot, transition matrix, next-day forecast, and LONG/FLAT/SHORT recommendation
with rationale. Do not re-summarize or rewrite it. You may add one short sentence above
the report if the user asked a follow-up question that needs answering separately.
