# Account Scaling Model

This file defines the rules for **moving up** between risk modes
(Evaluation → Funded → Scaling) and **moving down** (tier-down).
Scaling is driven by **statistical evidence**, not feelings or
absolute account size.

---

## 1. Scaling Inputs (computed nightly)

The engine computes these metrics after each session close (18:00 ET):

| Metric | Window | Formula |
|--------|--------|---------|
| **Win rate** | rolling 20 trades | `wins / total_trades` |
| **Expectancy (R)** | rolling 20 trades | `mean(R_realized)` |
| **Avg winner (R)** | rolling 20 trades | `mean(R_realized | R > 0)` |
| **Avg loser (R)**  | rolling 20 trades | `mean(R_realized | R <= 0)` |
| **Profit factor** | rolling 20 trades | `sum(R>0) / abs(sum(R<=0))` |
| **Max DD (R)** | rolling 20 trades | worst peak-to-trough in R-multiples |
| **Sessions traded** | rolling 5 sessions | count |
| **Locked sessions** | rolling 5 sessions | sessions where `LOCKED` was hit |

---

## 2. Mode Definitions (links)

Mode-specific contract caps, per-trade risk, and daily limits are in
`risk_modes.md`. This file governs only the **transitions** between
modes.

---

## 3. Move-Up Gates

| Move | Gate (ALL conditions must hold) |
|------|--------------------------------|
| Evaluation → Funded | (a) 20-trade expectancy ≥ **+0.4R** AND (b) profit factor ≥ **1.5** AND (c) max DD ≤ **3R** AND (d) **0** locked sessions in last 5 AND (e) **0** rule-violation attempts in last 5 sessions |
| Funded → Scaling | (a) 20-trade expectancy ≥ **+0.5R** AND (b) profit factor ≥ **1.8** AND (c) max DD ≤ **3R** AND (d) **0** locked sessions in last 10 AND (e) win rate ≥ **45%** AND (f) ≥ **40 trades** in the rolling window |

If a move-up gate is satisfied, the engine **does not auto-promote**
— it surfaces a recommendation in the daily report. The trader makes
the call after a weekly review.

---

## 4. Tier-Down Gates (automatic, no override)

| Move | Trigger (ANY one) |
|------|-------------------|
| Scaling → Funded | (a) 20-trade expectancy < **0R** OR (b) profit factor < **1.0** OR (c) max DD ≥ **5R** OR (d) **≥ 2 locked sessions** in last 5 OR (e) **2 consecutive losses** in current session |
| Funded → Evaluation | (a) 20-trade expectancy < **–0.2R** OR (b) **2 consecutive losses** in current session OR (c) **≥ 2 locked sessions** in last 5 |
| Evaluation → Stand-down (paper only) | 20-trade expectancy < **–0.4R** OR ≥ 3 locked sessions in last 5 |

Tier-down is applied **immediately** when the trigger fires. To return
to the prior mode requires re-satisfying the move-up gate.

---

## 5. Contract Progression Reference Table

| Mode | Account tier | Max contracts | Per-trade risk | Notes |
|------|--------------|--------------:|---------------:|-------|
| Evaluation | $25k – $150k eval | **1** | 0.5% | One setup, one contract; survive the eval |
| Funded     | $50k – $300k funded | **2** | 0.75% | Add second contract only after move-up gate |
| Scaling    | $300k+ funded equiv | **4 – 8** | 1.0% | Scale by tier (see § 6) |

---

## 6. Scaling-Mode Sub-Tiers

Within Scaling mode, contracts scale by account equity AND rolling
expectancy:

| Equity band | 20-trade expectancy | Max contracts |
|-------------|--------------------:|--------------:|
| $300k – $500k | ≥ +0.5R | 4 |
| $500k – $1M | ≥ +0.5R | 6 |
| $1M+ | ≥ +0.6R | 8 |
| Any | < +0.5R | **drop to prior tier's max** until expectancy recovers |

---

## 7. Per-Setup Performance Gating

If a specific setup's rolling 30-trade expectancy is **< 0R**, that
setup is **paused** until:

1. 10 paper trades on the setup, OR
2. A weekly review documents a clear parameter adjustment.

The setup can be re-enabled when paper-trade expectancy ≥ +0.3R over
the 10 paper trades.

---

## 8. Drawdown Recovery Protocol

If the account experiences a **5R drawdown** from the rolling 20-trade
peak:

1. **Halve all position sizes** for the next 10 trades.
2. **A or A+ only** — no B grades.
3. **Mandatory weekly review** at the end of the recovery period.
4. **No new setups** added to the playbook during recovery.

Sizes return to normal after 10 trades if expectancy is ≥ +0.3R.

---

## 9. Move-Up Recommendation Report (auto-generated)

The daily report includes a `scaling_recommendation` field:

```json
{
  "current_mode": "FUNDED",
  "candidate_mode": "SCALING",
  "gate_status": {
    "expectancy_R": { "value": 0.52, "threshold": 0.50, "pass": true },
    "profit_factor": { "value": 1.84, "threshold": 1.80, "pass": true },
    "max_DD_R": { "value": 2.6, "threshold": 3.0, "pass": true },
    "locked_sessions_5": { "value": 0, "threshold": 0, "pass": true },
    "win_rate": { "value": 0.47, "threshold": 0.45, "pass": true },
    "trade_count": { "value": 42, "threshold": 40, "pass": true }
  },
  "recommendation": "ELIGIBLE_TO_PROMOTE",
  "recommended_action": "review_at_weekly_meeting"
}
```

---

## 10. Versioning

The thresholds in this file are reviewed quarterly. Changes require:

1. A 60-day backtest demonstrating improvement on the rolling-20
   expectancy curve.
2. Documented review in `journal/weekly_performance_review.md`.

No live changes mid-quarter.
