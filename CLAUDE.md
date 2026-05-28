# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Slash Command

**`/markov-hedge-fund-method <TICKER>`** — runs a one-day Markov-chain transition-matrix analysis on the given equity symbol.

The command lives in `.claude/commands/markov-hedge-fund-method.md` and delegates to `.claude/skills/markov-hedge-fund-method/run.sh`, which:

1. Creates a local `.venv/` on first run (installs `yfinance`, `pandas`, `numpy`; ~30 s).
2. Fetches 5 years of daily adjusted closes via yfinance.
3. Discretizes daily log returns into 5 σ-scaled states and fits a 5×5 empirical transition matrix.
4. Conditions on today's state → next-day distribution → E[r] → LONG / FLAT / SHORT signal.

Print the script's stdout verbatim (self-contained Markdown report). Do not re-summarize it. If Yahoo Finance or pip is blocked by the network policy, surface the error rather than fabricating output.

---

## Coding Behavioral Guidelines

Tradeoff: These guidelines bias toward caution over speed. For trivial tasks, use judgment.

### 1. Think Before Coding

Don't assume. Don't hide confusion. Surface tradeoffs.

Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

Minimum code that solves the problem. Nothing speculative.

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes

Touch only what you must. Clean up only your own mess.

When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:

- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution

Define success criteria. Loop until verified.

Transform tasks into verifiable goals:

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.
