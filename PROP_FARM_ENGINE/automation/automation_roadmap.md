# Automation Roadmap

A phased path from **manual playbook** to **controlled auto-execution**.
The roadmap is conservative on purpose. Each phase has a graduation
gate. A phase is **not skipped**.

The hierarchy of goals (from `README.md`) is binding:

1. Consistency  →  2. Risk survival  →  3. Profitability  →  4. Automation.

Automation comes last because the cost of a misconfigured bot in a
prop firm account is **rule violation + loss of the account**.

---

## Phase 1 — Manual Playbook

**Goal:** Prove the discipline on paper.

| Component | Status |
|-----------|--------|
| Checklist (`checklists/`) | Required |
| Setup definitions (`playbook/`) | Required |
| Screenshot template (in `journal/`) | Required |
| Trade journal | Required (daily, per-trade, weekly) |
| Manual statistics tracking | Required |
| Live trading | **NO** — paper or sim only |

**Graduation gate (Phase 1 → 2):**

- 30 trades logged.
- Expectancy ≥ +0.3R.
- No off-playbook trades.
- All trades have grade assigned + journal entry.
- 5 consecutive sessions with no rule violations.

---

## Phase 2 — Signal Scanner (Alerts Only)

**Goal:** Detect setups automatically and surface them as alerts.
**No auto-execution. No size calculation. Just detection.**

| Component | Status |
|-----------|--------|
| TradingView Pine indicator (per `tradingview_indicator_logic.md`) | Required |
| Webhook alerts to Discord / Telegram / phone | Required |
| Detection covers: PDH/PDL/ONH/ONL/IBH/IBL/VAH/VAL/VPOC | Required |
| Detection covers: Setup 01 (priority), then 02–05 | Sequential |
| Order flow data displayed on chart | Required |
| Live trading | Allowed on **paper or eval account only** |

**Graduation gate (Phase 2 → 3):**

- 30 alerts logged with operator action (taken / skipped + reason).
- Alert precision ≥ 60% (taken alerts result in valid trades).
- 2 weeks of paper trading with the scanner.
- Operator can articulate why each alert was actionable.

---

## Phase 3 — Semi-Automation (Human-in-the-Loop)

**Goal:** System proposes the **full trade plan** (entry, stop, target,
size), human approves with a single click. Risk caps enforced by the
system.

| Component | Status |
|-----------|--------|
| External scanner reads chart data + emits signals | Required |
| Signal includes: side, entry, stop, T1, T2, grade, size_contracts, risk_$ | Required |
| Pre-trade gate (per `execution_safety_rules.md`) runs before surfacing | Required |
| Human approves via UI; order is bracket-submitted on approval | Required |
| All rejections logged with reason code | Required |
| Live trading | Allowed on **funded account** only after gate |

**Graduation gate (Phase 3 → 4):**

- 60 signals processed.
- Operator approval rate matches the system's grade calibration
  (operator approves ≥ 80% of A+, ≤ 40% of B).
- 0 rule violations in last 10 sessions.
- 20-trade rolling expectancy ≥ +0.4R.
- Phase 3 has run for ≥ 4 weeks of live RTH sessions.

---

## Phase 4 — Controlled Execution (A+ Only)

**Goal:** Engine auto-executes **A+ only** signals, with hard risk
gates and lockouts. Lower grades still require human approval.

| Component | Status |
|-----------|--------|
| Auto-execution restricted to grade `A+` | Hard constraint |
| Auto-execution disabled in `VOLATILITY_EXPANSION`, `NEWS_RISK`, `LOW_VOL_CHOP` regimes | Required |
| Daily P/L circuit breakers (per `daily_loss_protection.md`) | Required |
| News blackout enforcement | Required |
| Position management (T1 scale, T2 trail) auto-managed | Required |
| Manual kill switch always available | Required |
| All decisions audit-logged | Required |

**Graduation gate (Phase 4 → 5):**

- 60 days of Phase 4 live trading.
- 0 rule violations.
- 0 unintended overrides (the kill switch was used only when
  warranted).
- Expectancy ≥ +0.5R over the 60-day window.

---

## Phase 5 — Full Prop Farm Engine

**Goal:** Multi-account, multi-strategy, dashboard, lockouts, daily
reports.

| Component | Status |
|-----------|--------|
| Multi-account state tracking | Required |
| Risk dashboard (per-account daily P/L, DD buffer, mode) | Required |
| Strategy performance tracker (per-setup expectancy, win rate) | Required |
| Account health monitor (consecutive loss counter, DD buffer, lockouts) | Required |
| Automated lockout enforcement across accounts | Required |
| Daily report generator (auto-emailed end-of-session) | Required |
| Weekly performance review auto-populated | Required |
| Multiple risk modes per account independently | Required |

**Graduation gate (Phase 5 → ongoing operation):**

- 30 days of Phase 5 stable operation.
- No outages causing missed exits.
- Operator can prove the system enforces every rule in
  `risk/prop_firm_risk_rules.md` programmatically.

---

## Automation Risk Ladder (binding)

| Phase | Live $ at risk per session | Max instruments | Max accounts |
|-------|---------------------------:|----------------:|-------------:|
| 1 | $0 (paper only) | 1 | 1 |
| 2 | Eval account only | 1 (ES OR NQ) | 1 |
| 3 | Funded, single account | 2 (ES + NQ) | 1 |
| 4 | Funded, single account | 2 | 1 |
| 5 | Multi-account | 2 | 5+ |

---

## What Can Be Automated Now (Phase 1 → Phase 2)

Order of conversion (start at the top):

1. **Level detection** — PDH/PDL/ONH/ONL/IBH/IBL/VAH/VAL/VPOC/HVN/LVN.
   These are mechanical. (TradingView indicator.)
2. **Setup 01 trigger detection** — sweep + reclaim is mechanical.
   First setup to automate.
3. **Setup 02 trigger detection** — VAH/VAL approach + rejection bar.
4. **Setup 03 trigger detection** — open outside + re-entry + holding.
5. **Order flow tier classification** — once footprint feed is wired.
6. **Bias engine inputs** — overnight inventory, gap, VA migration.
7. **Regime classification** — ADX, ATR, VIX rules.

Setup 04 (LVN rejection) and Setup 05 (Initiative breakout) require
more nuanced LVN identification and are automated **after** Setups
01–03 are proven.

---

## What Stays Manual (always)

- **Pre-session bias check** — the operator runs through
  `checklists/premarket_checklist.md` daily even when Phase 5 is live.
- **Weekly performance review** — narrative + parameter judgment.
- **Setup additions/removals** — never automated; require human
  review and 30-trade paper validation.
- **Kill-switch decisions** — always operator-initiated.

---

## Rollback Protocol

Any phase that fails its graduation gate **rolls back** to the prior
phase for 2 weeks. The rollback decision is **not optional**.

Example: Phase 4 with > 1 rule violation in a session → drop back to
Phase 3 for 2 weeks of human-in-the-loop validation before re-attempting.

---

## Maintenance

Phase definitions are reviewed quarterly. New setups added to the
playbook re-enter at Phase 1 and progress through the gates
independently of the system's overall phase.
