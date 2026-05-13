# PROP FARM ENGINE

A rule-based, automation-ready prop firm futures trading framework focused
on **ES** and **NQ**.

This repository is the **specification** the future TradingView indicator
and execution engine will read from. Every rule is written to be
deterministic and machine-checkable.

---

## Mission

Build a repeatable, rule-based trading system that:

1. Identifies A+ setups in ES and NQ futures.
2. Filters out bad market conditions before risking capital.
3. Manages risk inside prop firm drawdown rules.
4. Eventually executes with strict, multi-layered controls.

The goal is **not** a reckless bot. The goal is a disciplined system that
survives evaluations, scales funded accounts, and only automates what is
proven manually first.

---

## Hierarchy of Goals (in order)

1. **Consistency** — same setup, same rules, every time.
2. **Risk survival** — never violate prop firm drawdown rules.
3. **Profitability** — positive expectancy over a 30-day window.
4. **Automation** — phased, only after manual proof.

---

## Repository Layout

```
PROP_FARM_ENGINE/
├── playbook/            A+ setup library (5 setups)
├── risk/                Prop firm risk rules, drawdown protection, scaling
├── market_context/      Daily bias, regime filter, ES vs NQ personality
├── order_flow/          Universal order flow confirmation engine
├── automation/          Roadmap, signal detection, pseudocode, TV indicator
├── checklists/          Premarket prep, A+ pre-trade gate
├── journal/             Daily, per-trade, weekly templates
└── roadmap/             30-day test plan, v1 build roadmap
```

---

## How to Read This Repository

Read in this order on day one:

1. `playbook/_playbook_overview.md` — what makes a setup A+.
2. `market_context/market_regime_filter.md` — when the system trades vs
   stands down.
3. `market_context/daily_bias_engine.md` — the top-down bias process.
4. `risk/prop_firm_risk_rules.md` and `risk/risk_modes.md` — the hard caps.
5. `playbook/setup_01_liquidity_sweep_reversal.md` — the first complete
   setup.
6. `order_flow/order_flow_confirmation_engine.md` — the universal
   confirmation logic.
7. `automation/automation_roadmap.md` — the phased path to automation.
8. `roadmap/v1_build_roadmap.md` — what to build next.

---

## Mandatory Setup Schema

Every setup file in `/playbook` follows this exact schema:

1. Context
2. Location
3. Trigger
4. Confirmation
5. Entry
6. Stop
7. Target
8. Invalidation
9. Risk Rule
10. Automation Rule

This guarantees every setup is convertible into code.

---

## Style Rules (binding on all files)

- No vague language ("looks strong", "feels right"). Numbers, levels,
  timeframes, and named conditions only.
- All thresholds are explicit (ticks, percent, bar counts, minutes).
- Every setup declares its **regime validity** and **banned regimes**.
- Every setup has an **invalidation** section — if you cannot define how
  the setup fails, you cannot trade it.
- Every setup has an **automation rule** in IF / AND / THEN form.

---

## Versioning

- **v0.1 (this commit):** Markdown specification only. No code.
- **v0.2:** TradingView Pine indicator implementing levels + signal markers.
- **v0.3:** External scanner / alerter (webhook → notifier).
- **v0.4:** Semi-auto execution (human-in-the-loop).
- **v1.0:** Controlled auto-execution of A+ setups only, with full risk
  gating and lockouts.

See `automation/automation_roadmap.md` and `roadmap/v1_build_roadmap.md`.

---

## Status

`v0.1` — specification only. **No live trading. No code execution.**
