---
name: markov-hedge-fund-method
description: Run a Markov-chain transition-matrix analysis on a stock ticker. Discretizes daily log returns into 5 states (down-big/down/flat/up/up-big), fits an empirical 5×5 transition matrix from ~5 years of daily data, conditions on today's state to produce a next-day probability distribution, and outputs a LONG/FLAT/SHORT recommendation with expected return and conditional Sharpe. Invoke when the user types `/markov-hedge-fund-method <TICKER>` or asks for a Markov-chain trading signal on a single equity symbol (e.g. AAPL, TSLA, SPY).
---

# Markov Hedge Fund Method

## When to use

The user typed `/markov-hedge-fund-method <TICKER>` or asked for a one-day Markov-chain
signal on a specific ticker. The ticker comes from the arguments after the slash command
(uppercase it before passing to the script).

If no ticker was provided, ask for one before running.

## How to run

The skill is invoked as:

```
bash <SKILL_DIR>/run.sh <TICKER>
```

where `<SKILL_DIR>` is the value printed at the top of the skill launch message as
`Base directory for this skill: ...`. Use that absolute path verbatim — when loaded as
a project skill the directory is `<repo>/.claude/skills/markov-hedge-fund-method/`, not
`~/.claude/skills/...`.

The first invocation creates `.venv/` inside the skill directory and installs `yfinance`,
`pandas`, and `numpy`. Subsequent calls reuse the venv. If the network policy blocks pip
or Yahoo Finance, the script will fail loudly — surface the error to the user rather than
fabricating output.

## Architecture

Three files cooperate:

- `.claude/commands/markov-hedge-fund-method.md` — slash-command wrapper around `run.sh`. The user-facing entry point.
- `SKILL.md` (this file) — auto-loaded when the skill is invoked. Describes when to use it, how to run it, and the output contract.
- `markov.py` — pure computation. No flags, no config, stdout only. Does not know about Claude Code.

`run.sh` is the bootstrap layer between them. Keep this separation when editing: the
slash command shouldn't reach into `markov.py` directly, and `markov.py` shouldn't
reference the skill or Claude Code.

## Presenting the result

The script emits a self-contained Markdown report on stdout. **Print it directly to the
user without re-summarizing or rewriting.** The Recommendation section already contains
the rationale. Do add a one-line acknowledgement above the report if the user asked a
follow-up question.

## Method (reference)

1. Fetch 5 years of daily adjusted closes via yfinance.
2. Compute daily log returns; let σ be their realized standard deviation.
3. Bucket each return into one of 5 states using σ-scaled thresholds:
   - `down-big`: r < −1.5σ
   - `down`:    −1.5σ ≤ r < −0.5σ
   - `flat`:    −0.5σ ≤ r < +0.5σ
   - `up`:      +0.5σ ≤ r < +1.5σ
   - `up-big`:  r ≥ +1.5σ
4. Estimate the empirical 5×5 transition matrix `P(s_{t+1} | s_t)` by counting.
5. Take today's state, multiply by P → next-day state distribution.
6. Compute E[r_{t+1}] using state midpoints (−2σ, −σ, 0, +σ, +2σ).
7. Position rule: LONG if E[r] > +0.25σ; SHORT if E[r] < −0.25σ; else FLAT.

If you change the state grid, thresholds, or position rule, also update the
`## State definitions` table the script prints in `markov.py` so the report stays
consistent with this section.

## Limitations (already disclosed in the report)

- Assumes stationarity of the transition matrix.
- Ignores volatility clustering, news, microstructure, overnight gaps, and execution.
- 5-state discretization is coarse by design — this is a tape-reading sanity check,
  not a standalone strategy.
