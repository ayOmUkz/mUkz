# 01 · BUSINESS CHARTER
*Version: v0.1 · Last revised: 2026-05-13 · Owner: solo operator*

> The charter is the root document. Every rule, setup, and routine that follows must serve the mission stated here. If a downstream document contradicts the charter, the charter wins until the charter itself is amended.

---

## §1 Mission

To operate a small, disciplined prop trading business that produces consistent monthly income by trading **a small number of high-quality setups on US index futures**, on leased capital from Apex Trader Funding, with capital preservation prioritized over profit at every decision point.

The business is not a hobby, a learning project, or a side activity. It is a sole-operator commercial operation with documented rules, recurring routines, and a written record of every decision.

---

## §2 What the business does

1. Trades the **regular trading hours (RTH)** session of the CME US equity index futures, specifically **ES** (E-mini S&P 500) and **NQ** (E-mini Nasdaq 100).
2. Takes only **three documented A+ setups** (see file 03):
   - Value Edge Reversal
   - Liquidity Sweep Reclaim
   - Initiative Breakout Through LVN
3. Sizes every position according to **fixed-fraction risk** measured in dollars against a written stop, never measured in points or ticks alone.
4. Logs **every trade and every skipped trade** in the journal (file 05).
5. Performs a **weekly review** every Sunday evening that grades adherence, not just outcomes.

---

## §3 What the business does not do

The business explicitly does **not**:

- Trade overnight or in the Globex session.
- Trade options, crypto, FX, single-name equities, ETFs, or commodities.
- Hold positions through scheduled high-impact news (FOMC, CPI, NFP, PCE).
- Use averaging-down, martingale, or grid strategies.
- "Recover" red days by increasing size or frequency.
- Take any trade that does not match one of the three playbook setups, regardless of how attractive the chart appears.
- Operate without the journal. If the journal is not being written, the business is closed for the day.
- Trade on a calendar day where any rule in file 02 has been broken in the prior session, until the failure is reviewed and logged.

---

## §4 Account & instruments

**Capital provider:** Apex Trader Funding.
**Account type:** $100,000 Evaluation.
**Phase:** Pre-evaluation (the eval has not been started as of v0.1).

| Spec | Value |
|---|---|
| Account size | $100,000 |
| Profit target (eval) | $3,000 |
| Trailing drawdown (eval) | $3,000 |
| Trailing type | End-of-day, trails until balance reaches starting + profit target |
| Daily loss limit | None mandated by Apex on the eval, **but $1,000 is mandated by this charter** (see file 02) |
| Min trading days | Per current Apex policy |
| Permitted instruments | All Apex-allowed; this business uses only **ES, NQ** |
| Permitted hours | 9:30–16:00 ET (RTH only) |
| News blackout | 2 min before to 2 min after FOMC, CPI, NFP, PCE, PPI |
| Max contracts (eval) | Per Apex consistency rule — the business will trade well below |

> **Action item:** Before the first eval trade, the operator must verify each row of this table against the current Apex Trader Funding dashboard and rulebook. Apex terms change. The charter is wrong if the dashboard says otherwise; the dashboard always wins on facts about the account, and the charter must be amended within one calendar day.

---

## §5 Operating principles

These four principles are the substrate beneath every rule:

1. **Capital before profit.** A drawdown of 1 % of the account is a worse outcome than missing a 10 R move. The eval is not won by the biggest day; it is won by surviving the worst.
2. **One business, one process.** The same checklist runs every day, regardless of P/L, mood, news, or market regime. Variations are written into the documents in advance, not improvised at the chart.
3. **Setups, not predictions.** The operator's job is to **recognize** a setup the playbook already describes, not to forecast where price is going. If recognition is uncertain, the trade does not happen.
4. **The journal is the truth.** Memory is biased; the journal is not. Disagreements between memory and the journal are resolved in favor of the journal.

---

## §6 90-day goals

These goals run from the date of the first live trade under this system (not from v0.1 of these documents).

| # | Goal | Measurable as |
|---|---|---|
| G1 | Pass the Apex $100K evaluation | Apex account flagged "passed" in the dashboard |
| G2 | Take ≤ 2 trades per session on average across the 90-day window | Mean of `trades_taken` field in file 05 daily summaries |
| G3 | Maintain a checklist compliance rate ≥ 95 % | Trades with all 12 checklist boxes ticked / total trades, computed weekly |
| G4 | Keep the largest single-day loss ≤ 1.0 % of account high-water mark | Min of `daily_pnl_pct` across the 90 days |
| G5 | Produce a complete daily journal entry on every trading day | Days with a `journal_YYYY-MM-DD.md` file / trading days in window |
| G6 | Complete every Sunday weekly review on time | Weekly review files present for each Sunday in window |

G2–G6 are **process goals**. They are graded independently of G1. It is possible (and acceptable) to fail G1 in a given 90-day cycle while passing G2–G6 — that outcome means the process is sound and the operator continues into the next eval. The reverse (passing G1 while failing process goals) is **not** acceptable and triggers a mandatory two-week review pause before any further trading.

---

## §7 What success looks like at 12 months

The 12-month horizon, conditional on G1 being achieved within the first 90 days:

- One funded performance account at Apex, scaled per Apex rules.
- Monthly withdrawal cadence established and consistent.
- The playbook (file 03) has been revised at most twice and at minimum once, based on weekly-review evidence.
- The journal contains ≥ 200 complete trade entries with attached screenshots.
- One additional setup has been promoted from the "watchlist" appendix of file 03 to the live-trade section, having met the promotion criteria in file 03 §6.
- The operator has not increased per-trade dollar risk beyond the schedule in §9.

---

## §8 Roles

The business has one human operator and one (currently undeployed) advisory agent.

| Role | Held by | Responsibilities |
|---|---|---|
| Trader / Operator | Solo human | All execution, all journaling, all reviews. Final authority on every trade. |
| Risk advisor | `CONSILIERE_RISK` (file 06) | Reads the rules (02), the playbook (03), and the day's plan, and approves or blocks each proposed trade against the 12-item checklist. Does not place orders. |
| Future roles | TBD | Placeholder: e.g. `JOURNAL_SCRIBE`, `BIAS_AUDITOR`, `REPLAY_TUTOR`. Not active in v0.1. |

The operator may overrule `CONSILIERE_RISK` only by **writing the override into the journal entry**, with the specific rule overridden and the reason. The Sunday review will count any override as a process-goal miss for that day.

---

## §9 Scaling triggers

Per-trade dollar risk is fixed. It does not move except by satisfying one of the triggers below. The default starting risk on a fresh eval is **$200 per trade**.

| Trigger # | Condition | Action |
|---|---|---|
| T1 | 20 consecutive trading days with zero rule breaks in file 02 | Risk allowed to move to $250 |
| T2 | 90-day rolling checklist compliance ≥ 95 % | Risk allowed to move to $300 |
| T3 | Funded account passed (G1 achieved) | Risk reset to $200 on the funded account; new triggers start fresh |
| T4 | One full calendar month at the funded account with daily-loss-limit unbroken | Risk allowed to move to $250 on funded |
| T5 | Apex scaling rule reached (per Apex contract terms) | Contract count may scale per Apex; dollar risk per trade stays governed by this table |
| T6 | Sixth-month review with all six 90-day goals met | Risk allowed to move to $400 |

All triggers are **upward-only and one-way**. Once moved up, risk does not come back down voluntarily. Risk is moved **down** only by the conditions in file 02 (drawdown protection, shutdown rules). Status of each trigger is tracked in the README §Status table and re-evaluated every Sunday.

---

## §10 Calendar & cadence

| Cadence | Activity | Document |
|---|---|---|
| Every trading day | Pre-market, open, intraday, close routines | File 04 |
| Every trading day | Trade journal entry + daily summary | File 05 |
| Every Sunday | Weekly review (1 hour, no exceptions) | File 04 §7, file 05 |
| Every month | Goal-vs-actual check against §6 | This file §6 |
| Every quarter | Charter re-read; minor amendments if any | This file |
| Every six months | Full system review; scaling-trigger re-evaluation | All files |
| Once per year | Tax + ops review (accountant, legal, Apex contract terms) | External, out of scope of this repo |

---

## §11 Termination conditions

This business is wound down — either temporarily paused or permanently shut — if any of the following occur:

1. Two consecutive failed Apex evals while paying for the same account size. → Pause 30 days, full review, drop one account size.
2. Three months of paying eval fees without a funded account. → Pause 60 days, full review.
3. A single rule break in file 02 §"Hard shutdown conditions". → Immediate stop, see file 02.
4. The operator stops journaling for **two consecutive trading days**. → Stop until journaling resumes for five consecutive days on paper trades only.
5. The operator can no longer commit the daily routine time (1.5 h pre-market, full session, 45 min close, weekly review). → Pause until the schedule can be reliably honored.

Termination is not a failure of the business; **operating without these triggers is the failure**.

---

## §12 Amendments to this charter

The charter is amended only at scheduled reviews:

- **Weekly review (Sunday)**: minor wording clarifications.
- **Quarterly review**: scope, instruments, goals.
- **Six-month review**: scaling triggers, risk schedule.

Every amendment increments the version field at the top of this file and is summarized in the journal entry of the day it is committed. Past versions remain in git history. Edits to the charter are never made silently.

---

*End of file 01.*
