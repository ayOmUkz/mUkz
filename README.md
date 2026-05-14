# PROP_FARM_LAB
**A personal prop trading business system.**
Internal trading operation. Not public. Solo operator.
> *The chart doesn't owe you a trade. Your edge is in waiting for the fingerprint — and walking away from everything else.*
---
## What this is
PROP_FARM_LAB is the written operating system for running a one-person prop trading business on leased capital from Apex Trader Funding. It exists so that every decision — what to trade, what not to trade, when, how much, and what to learn afterward — is governed by documents and checklists, not by feel.
The system is built around three principles:
1. **Capital is preserved before profit is pursued.** Risk rules override every other consideration.
2. **Only documented setups are tradeable.** If a trade doesn't fit the playbook, it doesn't exist.
3. **Every trade is logged and graded.** No exceptions. The journal is the truth.
**Account:** Apex Trader Funding $100K Evaluation
**Instruments:** ES, NQ (futures, RTH only)
**Methodology:** Wyckoff · Auction Market Theory · Volume Profile · Order Flow · Liquidity Sweeps
**Status:** Pre-evaluation, internal v0.1
---
## File index
| # | File | Purpose | Read time |
|---|---|---|---|
| 01 | [Business Charter](01_BUSINESS_CHARTER.md) | Mission, scope, 90-day goals, what the business does and does not do | 5 min |
| 02 | [Risk Constitution](02_RISK_CONSTITUTION.md) | Hard rules — daily/weekly loss limits, frequency caps, drawdown protection, shutdown conditions, the 12-item approval checklist | 10 min |
| 03 | [A+ Setup Playbook](03_A_PLUS_SETUP_PLAYBOOK.md) | The only three setups that may be traded — Value Edge Reversal, Liquidity Sweep Reclaim, Initiative Breakout Through LVN | 15 min |
| 04 | [Daily Operating Routine](04_DAILY_OPERATING_ROUTINE.md) | The seven routines that run every trading day, from pre-market to weekly review | 10 min |
| 05 | [Trade Journal Template](05_TRADE_JOURNAL_TEMPLATE.md) + [.csv](05_TRADE_JOURNAL_TEMPLATE.csv) | The 17-field per-trade entry, daily summary block, weekly summary block, and Google Sheets mirror | 5 min |
| 06 | [Agent Roles](06_AGENT_ROLES.md) | `CONSILIERE_RISK` definition (mission, responsibilities, output format, worked examples) and placeholder roles for future agents | 10 min |
---
## Reading order
**First time:** read top to bottom, 01 → 06. Everything builds on what came before.
**Every trading day:** consult 04 (routine), 02 (rules), and 03 (playbook). Write to 05 (journal).
**Every Sunday:** read 05 (week's entries), then 01 (charter), then propose edits to 03 (playbook) if warranted.
**When in doubt:** the most restrictive document wins. 02 (Risk Constitution) overrides everything.
---
## How the documents connect
```
                  ┌─────────────────────────────┐
                  │  01 CHARTER                 │
                  │  (mission, scope, goals)    │
                  └──────────────┬──────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        ▼                        ▼                        ▼
┌───────────────┐       ┌───────────────┐       ┌────────────────┐
│ 02 RULES      │◄─────►│ 03 PLAYBOOK   │◄─────►│ 05 JOURNAL     │
│ (don'ts)      │       │ (how to trade)│       │ (what happened)│
└───────┬───────┘       └───────┬───────┘       └────────┬───────┘
        │                       │                        │
        └───────────┬───────────┴────────────┬───────────┘
                    ▼                        ▼
            ┌───────────────┐       ┌───────────────────┐
            │ 04 ROUTINE    │◄─────►│ 06 AGENT ROLES    │
            │ (when/how)    │       │ (CONSILIERE_RISK) │
            └───────────────┘       └───────────────────┘
                ↑                           ↑
                └───── reads & enforces ────┘
```
- **01 Charter** is the root — what the business exists to do.
- **02 Rules**, **03 Playbook**, and **05 Journal** are the operational triangle — what to avoid, what to take, what happened.
- **04 Routine** sequences all three into a daily process.
- **06 Agent Roles** defines `CONSILIERE_RISK`, the enforcement layer that reads 02–05 and approves or blocks every trade.
---
## Daily lifecycle
Which documents are touched, in what order, on a single trading day:
| Time (ET) | Step | Reads | Writes |
|---|---|---|---|
| 08:30–09:25 | Pre-market | 02, 03 | 05 (plan block) |
| 09:25–09:45 | Open | 04 | 05 (day-type note) |
| Mid-session | Each trade | 02, 03 | 05 (per-trade entry) — 06 approves or blocks first |
| 16:00–16:45 | Close | 05 | 05 (daily summary) |
| Sunday eve | Weekly | 05 | 05 (weekly summary), possibly 03 (revisions for v0.2) |
If any step is skipped, the next trading day defaults to **observation only — no trades.** Routine 6 in file 04 lists the full set of conditions that break the routine.
---
## Single source of truth
Every fact in this system lives in exactly one place. Don't duplicate.
| If you need to know... | Look in... |
|---|---|
| What the business is | 01 Charter |
| What is allowed to be traded | 03 Playbook |
| What is forbidden | 02 Risk Constitution |
| When to do what during the day | 04 Routine |
| What happened on a given day | 05 Journal — `journal_YYYY-MM-DD.md` |
| What happened over a given week | 05 Journal — `weekly_YYYY-MM-DD.md` |
| How a rejection was decided | 06 Agent Roles + the journal entry that logged it |
| The current account state | Apex dashboard (live) + most recent journal daily summary |
---
## Versioning rules
These documents are amended in writing only. Verbal exceptions do not exist.
- Every file has a **version field** at the top (currently `v0.1`).
- Rule changes (02), playbook changes (03), and routine changes (04) require a **version bump** before they take effect.
- The agent (`CONSILIERE_RISK`) reads whatever version is committed. It does not negotiate against unwritten changes.
- Edits to past journal entries (05) are **forbidden.** New information goes in a follow-up note dated today.
- The weekly review (Routine 7 in file 04) is the only scheduled time for proposing rule or playbook revisions.
---
## Status
| Item | State |
|---|---|
| System version | 0.1 — all six core documents drafted |
| Apex evaluation | Not yet started |
| First trade taken under this system | Not yet |
| Active agents | None — `CONSILIERE_RISK` defined but not yet automated |
| Journal entries | 0 |
| Open scaling triggers met | 0 of 6 (see 01 §9) |
---
## Next steps
1. Verify the Apex $100K eval terms in file 01 §4 against the current Apex dashboard.
2. Set up the trading platform with the indicators required in 04 Routine 1 (Volume Profile, 9/21/50 EMA, Volume MA).
3. Create the `/journal/` and `/screenshots/` folders.
4. Add four representative screenshots per setup into `/screenshots/`, named per Field 11 of each setup in file 03.
5. Run one paper-trading day fully through Routines 1–6 to stress-test the system before risking the eval.
6. Begin the evaluation.
---
## Glossary (one-screen reference)
| Term | Meaning |
|---|---|
| **VAH / POC / VAL** | Top / middle / bottom of the prior session's value area on the volume profile |
| **LVN** | Low Volume Node — a thin price zone the market traveled through fast |
| **ON High / ON Low** | Overnight high / low |
| **PD VAH** | Prior-Day Value Area High |
| **Displacement** | A single bar that travels much further than the recent average |
| **Sweep** | Price runs past a known swing high/low (where stops sit) |
| **Reclaim** | After a sweep, price closes back inside the broken level |
| **Spring (Wyckoff)** | A failed breakdown — sweep below support that immediately reverses |
| **UTAD (Wyckoff)** | Upthrust After Distribution — failed breakout above resistance |
| **SOS / SOW** | Sign of Strength / Sign of Weakness — wide, high-volume bar in the breakout direction |
| **Initiative** | A move that *leaves* value to find new value |
| **Delta** | Buy aggressors minus sell aggressors — confirms or denies what price is doing |
| **Buffer** | Current account balance minus the trailing drawdown threshold |
| **R / R-multiple** | Trade reward divided by trade risk |
| **Apex eval** | The funded-account evaluation phase from Apex Trader Funding |
---
*PROP_FARM_LAB v0.1 · 2026-05-13 · Internal trading operation · Solo operator*
