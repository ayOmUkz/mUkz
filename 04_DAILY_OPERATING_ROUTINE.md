# 04 · DAILY OPERATING ROUTINE
*Version: v0.1 · Last revised: 2026-05-13 · Owner: solo operator*

> Trading without a routine is not trading; it is reacting. The seven routines below convert the static rules (files 01–03) and the static templates (file 05) into a moving, repeatable daily process. The routines are sequenced; skipping one breaks the chain, and a broken chain defaults the next session to **observation only**.

All times are US Eastern (ET).

---

## §1 Overview — the seven routines

| # | Routine | Window | Output |
|---|---|---|---|
| 1 | Pre-market prep | 08:30 – 09:25 | Plan block in `journal_YYYY-MM-DD.md` |
| 2 | Opening assessment | 09:25 – 09:45 | Day-type note in journal |
| 3 | Trade execution | 09:45 – 15:30 | Per-trade entries; 12-item checklist passed; agent APPROVED |
| 4 | Mid-session review | 12:00 – 12:15 | Brief checkpoint note |
| 5 | Session close & daily summary | 15:30 – 16:30 | Daily summary block in journal |
| 6 | Routine-break check | End of day | Confirmation routines 1–5 ran cleanly, or escalation logged |
| 7 | Weekly review | Sunday 19:00 – 20:00 | `weekly_YYYY-MM-DD.md` written; optional v-bump proposals |

Routines 1, 2, 3, 5 happen every trading day. Routine 4 is fixed midday. Routine 6 happens once at end of day. Routine 7 is weekly.

If any of 1, 2, 5, 6 is skipped, the **next** trading day is observation-only (no trades) until the routine chain has resumed for one clean day.

---

## §2 Routine 1 — Pre-market prep (08:30 – 09:25)

**Purpose:** Build the day's plan. Identify named levels. Decide what would qualify as a setup *before* the market opens, so identification at the chart is recognition, not invention.

**Reads:** files 02 (rules), 03 (playbook).
**Writes:** the plan block of today's journal entry (file 05 §2).

### Checklist (in order)

1. **Open the journal file for today.**
   `journal/journal_YYYY-MM-DD.md` — create from the template if it does not exist.
2. **Load the chart layout.**
   - Volume Profile: prior session (RTH only) — display VAH, POC, VAL.
   - Volume Profile: composite of last 10 RTH sessions — identify HVNs/LVNs.
   - EMAs on 5-minute: 9, 21, 50.
   - Volume MA: 20-bar.
   - Cumulative delta on the execution timeframe (1-min).
   - Order-flow footprint loaded but minimized.
   - Economic calendar widget visible.
3. **Mark named levels** in the journal plan block:
   - PD VAH, PD POC, PD VAL.
   - ON High, ON Low.
   - Prior swing high(s) / low(s) within visible chart range.
   - Weekly VAH/VAL.
   - Any visible LVN on the composite profile.
4. **Identify expected day type** based on:
   - Overnight inventory location (above PD VA, inside, below).
   - Overnight range relative to ATR.
   - Open relative to PD POC.
   Day type is **provisional** until Routine 2 finalizes it after the open.
5. **List the news events** on the calendar today and their times. Cross-reference file 02 §6 for blackout windows. Pre-fill the `news_blackouts` field of the journal entry.
6. **Compute buffer** from the live Apex dashboard. Write it in the journal entry. Apply file 02 §3.4 to determine today's allowed per-trade risk.
7. **Pre-declare the setups in play.** For each of the three setups (file 03), write a one-line "what would have to happen today for this setup to fire" — e.g., "Setup A long: ES drops below PD VAL by 09:50, reclaims by 10:00 with sell-side wick." If none of the setups have a plausible path, the day is acknowledged as a **likely no-trade day** in writing.
8. **Confirm physical / mental state.** Three questions in the journal:
   - Slept ≥ 6 hours? (Y/N)
   - Free of significant external stress today? (Y/N)
   - Mentally available for the full session? (Y/N)
   Any "N" → reduce frequency cap (file 02 §3.2) from 3 to 1 trade for the day, or default to observation-only.
9. **Set platform safeguards.**
   - Daily loss limit: $400 soft / $600 hard set in the platform if available.
   - Max contracts: as required by buffer-aware sizing.
   - One-cancels-other (OCO) brackets configured.
10. **Time stamp the close of Routine 1.**
    Write `routine_1_completed_at: HH:MM` in the journal entry. If not completed by 09:25, **default to observation-only** for the day.

### Conditions that make Routine 1 fail

- Platform indicators not loaded.
- Buffer cannot be read (Apex dashboard down).
- Calendar reveals FOMC / CPI / NFP / PCE / PPI release time within 30 minutes of 09:30 → no first-trade in first 30 min, possibly observation-only for the day.

A failed Routine 1 is **not** retried later in the day; the day is observation-only.

---

## §3 Routine 2 — Opening assessment (09:25 – 09:45)

**Purpose:** Lock in the day type. The first 15 minutes after the open is the most important market-information window of the day for context determination.

**Reads:** the open print and the first 15-minute range.
**Writes:** day-type note in journal.

### Checklist

1. **At 09:30** (open bell): note the open print. Compare to PD POC, PD VAH, PD VAL, ON H/L.
2. **By 09:45**: classify the day type using the framework below.

| Day type | Signature in first 15 min | Setups permitted |
|---|---|---|
| **Open-drive** | One-sided move that holds; price away from open with no rotation. | C (Initiative Breakout LVN) primarily. A/B disqualified intraday in the direction of the drive. |
| **Open-rejection** | Move out of open quickly fades back through open; range fills. | A, B (both fade structures). C only if a clean LVN displacement occurs after the rejection. |
| **Trend day** | Looks like open-drive but with extension; one-sided through the session. | C only; A/B forbidden. |
| **Balance day** | Range-bound around PD POC or open; rotations both sides. | A primarily. B if a clean named-level sweep occurs. C only on a confirmed break of the balance late in the session. |
| **Failed-auction** | New high or low printed, then reversed; sentiment shift. | B (the failed auction *is* the sweep + reclaim). |

3. **Write `day_type:` in the journal** with one of the five labels and one sentence justifying it.
4. **If unsure between two types:** default to the more restrictive — i.e., the day type that permits fewer setups.
5. **If today is unclassifiable at 09:45** (still no signal): wait. No trade until the day type clarifies. Many days do not clarify until 10:30 — that is acceptable.

### Time stamp

Write `routine_2_completed_at: HH:MM` and the chosen `day_type` in the journal entry.

---

## §4 Routine 3 — Trade execution (09:45 – 15:30)

**Purpose:** Take only setups that fit the playbook on a permitted day type, sized per the rules, journaled per the template, agent-approved.

**Reads:** files 02, 03, 06.
**Writes:** a per-trade entry (file 05 §3) for every trade and every skipped setup.

### Per-trade sub-routine

For every potential trade, execute these steps in order. **The order is not optional.**

1. **Identify** the setup forming. Speak its name aloud (or type it).
2. **Wait for the trigger condition** (file 03 §4 for the chosen setup). Do not anticipate.
3. **Pull up the 12-item checklist** (file 02 §7) in a sidebar or printed sheet.
4. **Tick each item** out loud as it passes. If any fails, the trade does not happen; log it as a skipped setup with the failing item noted.
5. **Submit to `CONSILIERE_RISK`** (file 06): the proposed trade details (setup, instrument, side, entry, stop, target, sizing, current buffer, today's trade count, news state).
6. **Receive APPROVED or BLOCKED.** If BLOCKED, log the blocking reason; do not retry the same trade.
7. **Submit the order** with bracket (stop + TP1 + TP2) attached. Verify the working stop appears in the platform within 3 seconds of fill.
8. **Manage per file 02 §8 and file 03 setup-specific §8.** Do not deviate.
9. **At exit**, record fill prices, R-multiple, and notes in the per-trade journal entry.
10. **Cooldown**: minimum 10 minutes before considering the next trade, regardless of outcome (file 02 §3.2).

### Hard guardrails during Routine 3

- **3 trades max** for the day (frequency cap).
- **2 losers → stop** for the day.
- **−$400 soft / −$600 hard** daily loss → stop.
- News blackout: stop. Close open positions before the event prints.
- A trade taken without going through this sub-routine is a rule break (S8 candidate, file 02 §4).

---

## §5 Routine 4 — Mid-session review (12:00 – 12:15)

**Purpose:** A short check-in to prevent silent drift in the afternoon. Most rule breaks happen between 12:00 and 14:00, when energy is low and fatigue is high.

### Checklist

1. **State out loud (or write) where the day stands:**
   - Trades taken so far: N.
   - W/L count: w-l.
   - Day P/L vs daily soft limit.
   - Open positions: yes/no.
2. **Pause for 5 minutes** away from the chart, off-screen. Walk; drink water.
3. **Re-read** file 02 §3 (loss limits) and §7 (12-item checklist) — yes, every day.
4. **Decide explicitly**: continue, observe, or stop.
   - If at 2 trades already and at break-even or worse: strong default is **stop**.
   - If green for the day and at 2 trades: consider **stop**.
   - If 0 or 1 trade and the day has more setups likely: continue.
5. **Time-stamp** the decision in the journal entry.

A missed Routine 4 does not by itself break the chain (only routines 1, 2, 5, 6 do), but two missed Routine 4s in a week is flagged in the Sunday review.

---

## §6 Routine 5 — Session close & daily summary (15:30 – 16:30)

**Purpose:** Close the day in writing. Convert lived experience into a journal record before details fade.

**Reads:** the day's per-trade entries.
**Writes:** daily summary block (file 05 §4).

### Checklist

1. **No new entries after 15:30.** First half-hour before the bell is wind-down; positions held into close must be exited by 15:55 unless explicitly held to RTH close.
2. **Flatten the account** at or before 16:00. No overnight holds (file 01 §3).
3. **Complete the per-trade entries** for every trade taken today. Attach screenshots to `/screenshots/` named per the playbook §4 filename pattern.
4. **Fill the daily summary** in the journal (file 05 §4):
   - Date.
   - Account balance opening / closing.
   - Buffer opening / closing.
   - Trades taken; trades skipped (with reasons).
   - W/L; total $; total R.
   - Checklist compliance: trades with all 12 items ticked / total trades.
   - Rule breaks (if any) and shutdowns triggered (if any).
   - One-line lesson of the day.
   - Tomorrow's intention (one sentence, not a prediction).
5. **Update the README §Status table** if any scaling trigger moved (file 01 §9).
6. **File the journal entry**: commit to git if used; otherwise save and back up.
7. **Time-stamp** `routine_5_completed_at: HH:MM`.

If Routine 5 is not completed by 16:30, **the next trading day is observation-only.** No exceptions.

---

## §7 Routine 6 — End-of-day routine-break check

**Purpose:** Audit whether the routine chain ran cleanly. This is a 2-minute self-check that gates tomorrow.

### Checklist

1. Did Routine 1 produce a plan block by 09:25? (Y/N)
2. Did Routine 2 produce a day-type note by 09:45? (Y/N)
3. Did every trade go through the per-trade sub-routine in Routine 3? (Y/N)
4. Did Routine 4 produce a mid-session decision? (Y/N) — soft
5. Did Routine 5 produce a daily summary by 16:30? (Y/N)
6. Are all rule breaks (if any) logged with rule number, time, and corrective action? (Y/N)

If any of 1, 2, 3, 5, 6 is "N": next trading day is **observation-only**. Write the breaking condition in tomorrow's pre-market plan as the first item.

### Conditions that break the routine

| # | Condition | Effect |
|---|---|---|
| B1 | Routine 1 incomplete by 09:25 | Today observation-only |
| B2 | Routine 2 incomplete by 09:45 (and no setup in play yet) | Today observation-only |
| B3 | Trade taken without the per-trade sub-routine | Rule break logged (S8 candidate) |
| B4 | Routine 5 incomplete by 16:30 | Tomorrow observation-only |
| B5 | Rule break (file 02) not logged | Logged on discovery + shutdown applies retroactively |
| B6 | Two consecutive days with any B-condition | Trigger the file 01 §11 termination check |

---

## §8 Routine 7 — Weekly review (Sunday 19:00 – 20:00)

**Purpose:** The single most important routine. The weekly review is the only scheduled time when rules and the playbook may be amended.

**Reads:** all `journal_YYYY-MM-DD.md` entries from the week and the prior `weekly_YYYY-MM-DD.md`.
**Writes:** `weekly_YYYY-MM-DD.md` (for the Sunday's date).

### Checklist (60 minutes; do not rush)

1. **Re-read every per-trade entry from the week.** Mark which were "A+ executions" (all 12 items, clean management, regardless of outcome) and which had defects.
2. **Compute weekly stats** and write them in the weekly summary block (file 05 §5):
   - Trades taken (target: ≤ 10).
   - Win rate.
   - Average R / total R.
   - Checklist compliance %.
   - Rule breaks (count and list).
   - Shutdowns (count and list).
   - Worst execution defect (one line).
   - Best execution moment (one line).
3. **Audit setup-level performance**: per-setup win rate, average R, count.
4. **Decide on amendments**:
   - File 03 (playbook): is any setup underperforming the §7 thresholds? Is a watchlist setup ready to promote per §6?
   - File 02 (rules): is any rule cutting valid trades systematically? (Need ≥ 20 logged examples to consider.)
   - File 01 (charter): are 90-day goals on track?
5. **Update scaling triggers** in the README §Status table.
6. **Set the week's intent** in one sentence in the weekly review file.
7. **Plan the next week**: holidays, scheduled news, anticipated themes.

### Routine 7 is mandatory

If a Sunday review is skipped, the following Monday is observation-only. If two consecutive Sunday reviews are skipped, the file 01 §11 termination check is triggered.

---

## §9 Failure cascades

This table maps a missed routine to its consequence. Read it before the day begins; do not negotiate at the time of failure.

| Missed | Effect |
|---|---|
| Routine 1 | Today observation-only |
| Routine 2 | Today observation-only (if no setup yet); restrict to fewer setups otherwise |
| Routine 3 sub-routine | Trade is a rule break; agent should have blocked |
| Routine 4 | Soft; flagged on Sunday |
| Routine 5 | Tomorrow observation-only |
| Routine 6 | Tomorrow observation-only |
| Routine 7 | Next Monday observation-only; second miss → §11 review |

---

## §10 Time discipline

The routines are time-bounded for a reason. The most common excuse for routine drift is "I'll do it later." There is no later in this system.

- **08:30 — 16:30 ET** is the protected operating window on every trading day.
- **Sundays 19:00 – 20:00** is the protected weekly review window.
- No external meetings, errands, or phone calls inside these windows. Notifications muted. Doors closed.
- If the time cannot be honored on a given day, the day is observation-only and explicitly logged as such; the routine is not "shortened."

---

*End of file 04.*
