# 05 · TRADE JOURNAL TEMPLATE
*Version: v0.1 · Last revised: 2026-05-13 · Owner: solo operator*

> The journal is the truth. Memory is biased; the journal is not. Where memory and journal disagree, the journal wins. This file is the **template** — actual entries live under `/journal/`.

---

## §1 File layout

Three kinds of files live under `/journal/`:

| Filename | Cadence | Purpose |
|---|---|---|
| `journal_YYYY-MM-DD.md` | One per trading day | Plan block + per-trade entries + daily summary for that day |
| `weekly_YYYY-MM-DD.md` | One per Sunday | Weekly summary, audit, amendments-proposed |
| `notes_YYYY-MM-DD.md` | Ad hoc | Follow-up notes; never edit old entries (file 00 README "Versioning rules") |

Screenshots are stored under `/screenshots/`, filenames per file 03 §11 of each setup.

---

## §2 Daily plan block (Routine 1 output)

Pasted at the top of each `journal_YYYY-MM-DD.md`. Filled in pre-market (08:30–09:25 ET).

```markdown
# Daily Journal — {YYYY-MM-DD}

## Plan block (pre-market)

- **Date:** {YYYY-MM-DD}
- **Day of week:** {Mon/Tue/Wed/Thu/Fri}
- **Operator state:** sleep ≥ 6h: {Y/N} · low external stress: {Y/N} · mentally available full session: {Y/N}
- **Routine 1 completed at:** {HH:MM ET}

### Account
- **Account balance (opening):** ${...}
- **Trailing drawdown threshold:** ${...}
- **Buffer (opening):** ${...}
- **Per-trade risk allowed today:** ${...}  ← per file 01 §9 schedule and file 02 §3.4 buffer adjustment
- **Frequency cap today:** {1 or 3 trades}  ← reduced to 1 if any operator-state "N"

### Levels (named, in points or ticks)
- **ES:** PD VAH={...} · PD POC={...} · PD VAL={...} · ON H={...} · ON L={...} · Composite LVNs={...} · Other={...}
- **NQ:** PD VAH={...} · PD POC={...} · PD VAL={...} · ON H={...} · ON L={...} · Composite LVNs={...} · Other={...}

### News calendar
- {HH:MM} {Event} — blackout: {HH:MM}–{HH:MM}
- ...
- **First-trade restriction (any 08:30 release):** {Y/N — first 30 min no entry}

### Day type (provisional)
- **ES:** {open-drive / open-rejection / trend / balance / failed-auction / undetermined}
- **NQ:** {...}

### Setups in play
- **Setup A (Value Edge Reversal):** {what would need to happen today}
- **Setup B (Liquidity Sweep Reclaim):** {what would need to happen today}
- **Setup C (Initiative Breakout LVN):** {what would need to happen today}
- **Likely no-trade day?** {Y/N — explain in one sentence}

### Platform safeguards
- Daily soft loss limit set: {Y/N}
- Daily hard loss limit set: {Y/N}
- OCO brackets configured: {Y/N}
- Max contracts per order: {N}

### Intent for the day (one sentence)
> {...}

---
```

---

## §3 Per-trade entry (17 fields)

One block per trade taken. Also one block per **skipped setup** (with status `skipped`).

```markdown
## Trade {n} — {HH:MM ET}

- **F1 · Setup name:** {Value Edge Reversal / Liquidity Sweep Reclaim / Initiative Breakout LVN}
- **F2 · Instrument:** {ES / NQ}
- **F3 · Side:** {Long / Short}
- **F4 · Day type at entry:** {open-drive / open-rejection / trend / balance / failed-auction}
- **F5 · Context:** {1–3 sentences: where price is in profile, named level it's reacting to}
- **F6 · Entry trigger fired at:** {HH:MM:SS — describe what bar/event triggered}
- **F7 · Entry price:** {price}
- **F8 · Written stop:** {price}  · **Stop distance (ticks):** {N}
- **F9 · TP1:** {price} · **TP2:** {price}
- **F10 · Position size (contracts):** {N}  ← computed: floor( {risk$} / ({stop_ticks} × {$/tick}) )
- **F11 · Dollar risk on this trade:** ${...}  ← {must ≤ allowed in plan block}
- **F12 · 12-item checklist:** [✓/✗] 1 · [✓/✗] 2 · [✓/✗] 3 · [✓/✗] 4 · [✓/✗] 5 · [✓/✗] 6 · [✓/✗] 7 · [✓/✗] 8 · [✓/✗] 9 · [✓/✗] 10 · [✓/✗] 11 · [✓/✗] 12  ← all must be ✓ to enter
- **F13 · Agent verdict (`CONSILIERE_RISK`):** {APPROVED / BLOCKED} — reason: {...}
- **F14 · Exit(s):** {HH:MM:SS @ price for each fill — TP1 partial, BE move, runner exit, time stop, manual flat}
- **F15 · P/L $ realized:** ${...}  · **R-multiple realized:** {...} R
- **F16 · Screenshot filename:** {/screenshots/{setup}_{date}_{instrument}_{L|S}_{TF}.png}
- **F17 · Notes:** {1–4 sentences: what went right/wrong in execution, was the trade itself good independent of outcome, any rule slippage}

---
```

### Field-by-field notes

| Field | Notes |
|---|---|
| F1 | Must exactly match a setup name in file 03. "Looked like A" is not a setup name. |
| F4 | Re-confirm the day type at entry. It may have evolved since Routine 2. |
| F8 | Written stop = the price the working stop order was set at, not where it eventually filled if slipped. |
| F11 | Must be ≤ the allowed-per-trade-risk in the plan block. Greater = rule break (file 02). |
| F12 | All 12 checkboxes are independent; partial ticks are not allowed. |
| F13 | If BLOCKED, the trade did not happen — convert this entry's status to `skipped` and record the blocking reason. |
| F15 | R = (exit P/L $ before fees) / (F11 dollar risk). Compute, do not estimate. |
| F16 | Filename per file 03 §11; if no screenshot was saved, this is a process miss and must be flagged in F17. |

### Status options

A per-trade entry block has one of these statuses (in the heading):

- `## Trade {n}` — taken trade.
- `## Skipped setup {n} — {HH:MM}` — setup formed but did not pass the checklist or agent. Fields F1–F8 still filled; F12 shows the failing item(s); F14–F15 N/A.

---

## §4 Daily summary (Routine 5 output)

Pasted at the bottom of `journal_YYYY-MM-DD.md`. Filled 15:30–16:30 ET.

```markdown
## Daily summary

- **Routine 5 completed at:** {HH:MM ET}
- **Account balance (closing):** ${...}
- **Buffer (closing):** ${...}
- **Trades taken:** {N}
- **Setups skipped:** {N}
- **W / L / BE:** {w} / {l} / {b}
- **Total P/L $:** ${...}
- **Total R:** {...} R
- **Checklist compliance:** {ticked/total} trades fully ticked = {%}
- **Day type final classification (ES):** {...}  · **(NQ):** {...}
- **Rule breaks (file 02):** {none / list with rule numbers}
- **Shutdowns triggered:** {none / S{N}}
- **Routines 1–6 status:** R1: {Y/N at {HH:MM}} · R2: {Y/N at {HH:MM}} · R3: clean? {Y/N} · R4: {Y/N} · R5: {Y/N at {HH:MM}} · R6: {Y/N}
- **Lesson of the day (one sentence):** {...}
- **Tomorrow's intent (one sentence, not a prediction):** {...}
- **Tomorrow observation-only?** {Y/N — explain}

---
```

---

## §5 Weekly summary (Routine 7 output)

Written every Sunday into `weekly_YYYY-MM-DD.md` (where YYYY-MM-DD is the Sunday's date).

```markdown
# Weekly Review — week ending {YYYY-MM-DD}

## Stats

- **Trading days this week:** {N}
- **Observation-only days:** {N}
- **Total trades:** {N}
- **Setups skipped (counted):** {N}
- **Win rate:** {%}
- **Total R:** {...} R · **Average R per trade:** {...} R
- **Total $ P/L:** ${...}
- **Worst day $:** ${...}  · **Best day $:** ${...}
- **Account high-water mark this week:** ${...}
- **Checklist compliance rate:** {%}  ← G3 target: ≥ 95 %
- **Rule breaks (file 02):** {count and list}
- **Shutdowns:** {count and list}

## Per-setup breakdown

| Setup | Trades | Wins | Win rate | Avg R | Total R |
|---|---|---|---|---|---|
| A — Value Edge Reversal | {N} | {N} | {%} | {...} | {...} |
| B — Liquidity Sweep Reclaim | {N} | {N} | {%} | {...} | {...} |
| C — Initiative Breakout LVN | {N} | {N} | {%} | {...} | {...} |

## Routine audit

- Routines 1, 2, 5, 6 clean every day? {Y/N — list misses}
- Routine 7 done previous week on time? {Y/N}

## Execution defects (one line each)

- ...

## Execution wins (one line each)

- ...

## Proposed amendments

- **File 02 (rules):** {none / specific proposal with evidence count}
- **File 03 (playbook):** {none / specific proposal with evidence count}
- **File 04 (routine):** {none / specific proposal}
- **File 01 (charter):** {none / specific proposal}

## Scaling-trigger status (file 01 §9)

| Trigger | Status | Evidence |
|---|---|---|
| T1 | {met/not-met} | {N consecutive clean days so far} |
| T2 | {met/not-met} | {90-day compliance %} |
| T3 | {met/not-met} | {funded? Y/N} |
| T4 | {met/not-met} | {funded month status} |
| T5 | {met/not-met} | {Apex scaling status} |
| T6 | {met/not-met} | {6-month check pending} |

## Goals progress (file 01 §6)

- **G1 — Pass Apex eval:** {on-track / behind / done}
- **G2 — ≤ 2 trades/session avg:** {avg this 90-day window: {...}}
- **G3 — checklist compliance ≥ 95 %:** {current rolling %}
- **G4 — largest single-day loss ≤ 1 %:** {current worst %}
- **G5 — daily journals complete:** {N/N}
- **G6 — weekly reviews complete:** {N/N}

## Week's intent (one sentence)

> {...}

## Next week — planned

- Holidays / market closes: {...}
- Scheduled high-impact news: {list with times}
- Anticipated themes (no predictions, just calendar): {...}

---
```

---

## §6 The 17-field per-trade entry as a CSV

For long-run analytics, the same 17 fields are mirrored into a single CSV under `/journal/` named `trades.csv` (one row per trade) and produced/updated **manually after each daily close**.

The companion file `05_TRADE_JOURNAL_TEMPLATE.csv` contains the column header row only.

### Columns

`trade_id, date, time, setup, instrument, side, day_type, context, trigger_time, entry_price, stop_price, stop_ticks, tp1_price, tp2_price, contracts, dollar_risk, dollar_pnl, r_multiple, checklist_pass, agent_verdict, screenshot, notes`

### Conventions

- `trade_id`: `{YYYY-MM-DD}-{seq}` where `seq` is 01, 02, 03 in entry order (also used for skipped setups: `{YYYY-MM-DD}-S{seq}`).
- `time`: entry time in 24-hour `HH:MM:SS`.
- `setup`: one of `value_edge_reversal`, `liquidity_sweep_reclaim`, `initiative_breakout_lvn`, or `skipped`.
- `side`: `L` / `S` / `-` for skipped.
- `day_type`: `open_drive` / `open_rejection` / `trend` / `balance` / `failed_auction`.
- `checklist_pass`: `1` if all 12 items ticked, else `0`.
- `agent_verdict`: `APPROVED` / `BLOCKED`.
- `r_multiple`: signed, 2 decimals; for skipped, `0.00`.
- `notes`: free-form, no commas; replace with `;` if needed.

The CSV is the source for the Google Sheets mirror; do not type into the sheet, only into the CSV, then sync.

---

## §7 Rules about the journal itself

1. **One entry per day, every trading day.** Days with no trades still get a `journal_YYYY-MM-DD.md` containing the plan block, an "Observation only" note where Routine 3 would have been, and the daily summary.
2. **No back-dating.** If a day is missed entirely, write the next day's first note: "Missed journal for {YYYY-MM-DD} — observation-only for {today}." See file 02 §4 S7 for the shutdown.
3. **No edits to past entries.** New information goes in `notes_YYYY-MM-DD.md` for **today**.
4. **Screenshots are mandatory** for every taken trade. A missed screenshot is a process miss, flagged in F17, and counted against checklist compliance G3.
5. **Backups**: at minimum, the `/journal/` folder is committed to git daily after Routine 5. A second backup mechanism is left to the operator.
6. **Sensitive information**: this is an internal operation — keep account numbers, payment details, and identification out of the journal. Use balance figures only.

---

## §8 Quick-fill example (illustrative; not a real trade)

```markdown
# Daily Journal — 2026-05-13

## Plan block (pre-market)

- **Date:** 2026-05-13
- **Day of week:** Wed
- **Operator state:** sleep ≥ 6h: Y · low external stress: Y · mentally available full session: Y
- **Routine 1 completed at:** 09:18

### Account
- **Account balance (opening):** $102,100
- **Trailing drawdown threshold:** $99,300
- **Buffer (opening):** $2,800
- **Per-trade risk allowed today:** $200
- **Frequency cap today:** 3

... (levels, news, day type, setups in play) ...

## Trade 1 — 10:14

- **F1 · Setup name:** Value Edge Reversal
- **F2 · Instrument:** ES
- **F3 · Side:** Short
- **F4 · Day type at entry:** balance
- **F5 · Context:** ES traded 6 ticks above PD VAH on weak volume, ON High unbroken. Composite LVN above 5320.
- **F6 · Entry trigger fired at:** 10:14:22 — reclaim bar closed 4 ticks back inside PD VAH with sell-delta 78 % of bar range.
- **F7 · Entry price:** 5319.25
- **F8 · Written stop:** 5320.75  · **Stop distance (ticks):** 6
- **F9 · TP1:** 5314.00 (PD POC)  · **TP2:** 5308.50 (PD VAL)
- **F10 · Position size (contracts):** 2  ← floor( 200 / (6 × $12.50) ) = floor(200/75) = 2
- **F11 · Dollar risk on this trade:** $150
- **F12 · 12-item checklist:** [✓] 1 [✓] 2 [✓] 3 [✓] 4 [✓] 5 [✓] 6 [✓] 7 [✓] 8 [✓] 9 [✓] 10 [✓] 11 [✓] 12
- **F13 · Agent verdict:** APPROVED — reason: setup matched, all 12 items pass, buffer $2,800 > $2,000 threshold.
- **F14 · Exit(s):** 10:21:01 1c @ 5314.00 (TP1 partial). 10:29:33 BE move on remainder. 10:41:12 1c @ 5310.25 (manual flat — runner stalled, 20-min time stop approaching).
- **F15 · P/L $ realized:** +$178  · **R-multiple realized:** +1.19 R
- **F16 · Screenshot filename:** /screenshots/value_edge_reversal_2026-05-13_ES_S_1m.png
- **F17 · Notes:** Clean trigger. TP1 hit fast. Runner stalled — should have honored time stop sooner (exited at 10:41 vs 20-min mark 10:34). Process miss flagged.

---

## Daily summary

- **Routine 5 completed at:** 16:18
- **Account balance (closing):** $102,278
- ... (rest of summary)
```

---

*End of file 05.*
