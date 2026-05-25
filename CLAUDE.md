# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A single Claude Code skill: `markov-hedge-fund-method`. It fits an empirical 5×5 Markov transition matrix to ~5 years of daily log returns for a ticker, conditions on today's state, and emits a Markdown report with a LONG/FLAT/SHORT recommendation. There is no application, library, or test suite — the deliverable is the skill itself.

## Running the skill

```
bash .claude/skills/markov-hedge-fund-method/run.sh <TICKER>
```

`run.sh` bootstraps `.venv/` inside the skill directory on first invocation and `pip install`s `yfinance`, `pandas`, `numpy` (~30s). Subsequent runs reuse the venv (<1s). The venv is gitignored.

The user-facing entry point is the slash command `/markov-hedge-fund-method <TICKER>`, defined in `.claude/commands/markov-hedge-fund-method.md`, which calls the same `run.sh`.

## Architecture

Three files do all the work:

- `.claude/commands/markov-hedge-fund-method.md` — slash-command frontmatter + instructions to the agent. Thin wrapper around `run.sh`.
- `.claude/skills/markov-hedge-fund-method/SKILL.md` — skill manifest (auto-loaded when the skill is invoked). Describes the method and the output contract.
- `.claude/skills/markov-hedge-fund-method/markov.py` — the actual computation. Pure stdout; no flags, no config files.

`run.sh` is the bootstrap layer between them. Keep this separation: the slash command shouldn't reach into `markov.py` directly, and `markov.py` shouldn't know about Claude Code.

## Output contract (important)

`markov.py` writes a self-contained Markdown report to stdout. Both the slash command and `SKILL.md` instruct the agent to **print it verbatim** — no summarizing, no rewriting, no extracting "the recommendation." The Recommendation section already contains the rationale. If you change the script's output format, update both `.claude/commands/markov-hedge-fund-method.md` and `.claude/skills/markov-hedge-fund-method/SKILL.md` to match.

## Method (mirrors SKILL.md, kept here so edits stay in sync)

1. Fetch 5y daily adjusted closes via `yfinance` (`auto_adjust=True`).
2. Compute daily log returns; σ = realized stdev.
3. Bucket into 5 states using σ-scaled thresholds: `down-big` (<−1.5σ), `down`, `flat` (±0.5σ), `up`, `up-big` (≥+1.5σ).
4. Estimate empirical 5×5 transition matrix `P` by counting consecutive-state pairs; row-normalize (zero rows kept zero via `row_sums[row_sums == 0] = 1.0`).
5. Multiply today's state row by `P` → next-day distribution.
6. E[r] = next-day distribution · midpoints (−2σ, −σ, 0, +σ, +2σ).
7. Position rule: LONG if E[r] > +0.25σ; SHORT if < −0.25σ; else FLAT.

Any change to the state grid, thresholds, or position rule needs to be reflected in the `## State definitions` table the script prints, plus `SKILL.md`'s Method section.

## Network requirements

The skill needs outbound access to PyPI (first run) and Yahoo Finance (every run). If either is blocked by the session's network policy, the script fails loudly — surface the error rather than fabricating output.
