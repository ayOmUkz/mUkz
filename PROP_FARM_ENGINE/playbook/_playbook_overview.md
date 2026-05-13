# Playbook Overview

The playbook defines the **A+ Setup Library** for ES and NQ. Every setup
file in this folder follows the same mandatory schema so the entire
playbook can be consumed by the indicator and the execution engine.

---

## A+ Grading Rubric (universal)

A setup grade is determined by five binary criteria. Each criterion is
worth one point.

| # | Criterion | Pass condition |
|---|-----------|----------------|
| 1 | Regime alignment | Current regime is in setup's `allowed_regimes` list AND not in `banned_regimes` |
| 2 | Bias alignment | Daily bias side == setup side AND bias_confidence ≥ 50 |
| 3 | Level confluence | Entry level overlaps ≥ 2 of: PDH/PDL, ONH/ONL, IBH/IBL, VAH/VAL, VPOC, weekly H/L, HVN edge |
| 4 | Order flow | STRONG_CONFIRM (≥ 2 OF signals) per `order_flow/order_flow_confirmation_engine.md` |
| 5 | Time-of-day | Inside prime windows: 09:30–11:30 ET or 13:30–15:30 ET |

### Grade Map

| Score | Grade | Action |
|-------|-------|--------|
| 5 / 5 | **A+** | Take full size (within risk mode caps) |
| 4 / 5 | **A**  | Take full size |
| 3 / 5 | **B**  | Take **half size** |
| ≤ 2   | skip  | Stand down |

### R:R Floor (overrides grade)

Even an A+ trade is **skipped** if the projected R:R to T1 is < 2.0R.
The market does not pay enough for the risk. No exceptions.

---

## Setup Index

| # | File | Class | Regime |
|---|------|-------|--------|
| 01 | `setup_01_liquidity_sweep_reversal.md` | Reversal / Failed Auction | BALANCE, VOLATILITY_EXPANSION |
| 02 | `setup_02_value_area_rejection.md`     | Responsive / Mean Reversion | BALANCE |
| 03 | `setup_03_80_percent_value_area_rule.md` | Auction Rotation | BALANCE |
| 04 | `setup_04_lvn_rejection.md`            | Reversal / Auction Failure | BALANCE, VOLATILITY_EXPANSION |
| 05 | `setup_05_initiative_breakout.md`      | Initiative / Continuation | TREND, VOLATILITY_EXPANSION |

---

## Mandatory File Schema (binding)

Every setup file must contain these sections in this order:

1. **Header** — instruments, timeframes, setup class, regime validity,
   banned regimes.
2. **Context** — the thesis in 2–4 sentences.
3. **Location** — the levels at which the setup is valid.
4. **Trigger** — sequential, numbered conditions, all required.
5. **Confirmation** — order flow signals required (MIN vs STRONG).
6. **Entry** — primary, backup, skip rules.
7. **Stop** — hard stop in ticks, time stop in minutes.
8. **Target** — T1, T2, runner with explicit scale-out actions.
9. **Invalidation** — explicit failure conditions.
10. **Risk Rule** — per-trade risk %, sizing formula, correlation cap,
    max attempts/day for this setup.
11. **Automation Rule** — IF / AND / THEN logic + alert payload schema.

Optional but recommended:

12. A+ Grade Criteria (5-point breakdown specific to the setup).
13. Known Failure Modes.
14. Journal Fields.

---

## Time-of-Day Filter (universal)

| Window (ET) | Status |
|-------------|--------|
| 09:30 – 10:30 | **PRIME** — all setups allowed, A+ window |
| 10:30 – 11:30 | OPEN — all setups allowed |
| 11:30 – 13:30 | **LUNCH CHOP** — only initiative breakouts allowed, half size |
| 13:30 – 15:30 | OPEN — all setups allowed |
| 15:30 – 16:00 | CLOSING — no new entries; manage existing only |

---

## Correlation Rule (universal)

If ES and NQ both fire the same setup on the same side within 5 minutes:

- Take the **first** signal at full size.
- Reduce the second by 40% (counts as 0.6× exposure).
- If 30-day correlation > 0.9, skip the second leg entirely.

See `market_context/es_vs_nq_personality.md`.

---

## Skip Conditions (override any grade)

The setup is skipped, regardless of grade, if:

- Daily loss circuit breaker is firing
  (see `risk/daily_loss_protection.md`).
- News window is active (±2 min around HIGH-impact event).
- Data freshness check fails (last tick > 5s old).
- Regime classifier returns NEWS_RISK or LOW_VOL_CHOP (setup-banned).
- Account has already taken 2 attempts of this setup today.

---

## Versioning Setups

A setup parameter (e.g., sweep buffer in ticks, R:R floor) is changed
**only** after ≥ 30 trades of statistical evidence and a documented
review in `journal/weekly_performance_review.md`. No mid-week parameter
changes.
