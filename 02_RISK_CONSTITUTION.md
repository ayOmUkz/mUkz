# 02 · RISK CONSTITUTION
*Version: v0.1 · Last revised: 2026-05-13 · Owner: solo operator*

> This document is the most restrictive in the system. Where it conflicts with any other document, this one wins until it is itself amended in writing. The Risk Constitution is not aspirational. It is binding from the moment v0.1 is committed.

---

## §1 Why this document exists

The single largest cause of failure on funded prop evaluations is not bad setups. It is **rule breaks under emotional pressure**: oversizing after a loss, holding past a stop, taking a fourth trade after three reds, trading through news. The Risk Constitution exists so that those decisions are pre-made — in writing, when calm — and so that the agent (`CONSILIERE_RISK`, file 06) has an unambiguous reference to enforce them.

If a rule below feels too strict on a given day, that is the rule working. It is not evidence the rule is wrong.

---

## §2 Definitions

These terms are used throughout this document with the meanings below. They override colloquial usage.

| Term | Meaning |
|---|---|
| **Account high-water mark (HWM)** | The highest end-of-day balance the account has ever reached. Resets only on a new eval / new account. |
| **Buffer** | Current account balance minus the trailing drawdown threshold from Apex. Always positive while the account is live. |
| **R / R-multiple** | Dollar reward of a trade divided by its dollar risk. Computed against the **written** stop, not the realized stop. |
| **Per-trade risk** | Dollars at risk between entry and the written hard stop, position size included. Default $200 per file 01 §9. |
| **Daily loss limit** | The dollar loss across all trades on one calendar day at which the day ends. |
| **Weekly loss limit** | The dollar loss across all trades in a Monday-Friday window at which the week ends. |
| **Frequency cap** | The maximum number of trades the operator may take in a single session. |
| **Hard shutdown** | A condition that stops trading for a fixed period and triggers a review. |
| **Written stop** | The price level entered into the broker's stop order at the moment of fill. Not a "mental stop." |

---

## §3 Hard rules — loss limits

These are dollar amounts on the Apex $100K eval. If the account size changes, the values must be amended here before the new account is traded.

### §3.1 Per-trade

| Rule | Value |
|---|---|
| Default dollar risk per trade | **$200** |
| Maximum dollar risk per trade (any condition) | **$300** until trigger T2 (file 01 §9) is met |
| Permitted entry without a written stop | **Never.** No trade without a working stop order in the platform. |
| Permitted widening of a stop after fill | **Never.** Stops only move toward break-even or toward profit. |

### §3.2 Per-day

| Rule | Value |
|---|---|
| Daily loss limit (soft) | **−$400** → trade for the day ends, journal entry written, no further setups taken. |
| Daily loss limit (hard) | **−$600** → terminal. Platform closed. Day ends regardless of which routine step was active. |
| Maximum trades per session | **3** (frequency cap) |
| Maximum consecutive losses before stop-for-day | **2** |
| Permitted re-entry within 10 minutes of a stopped-out trade | **No.** Mandatory 10-minute cooldown, regardless of setup quality. |

### §3.3 Per-week

| Rule | Value |
|---|---|
| Weekly loss limit | **−$1,000** (5 × per-day soft) → week ends Friday early or at the moment hit. |
| Maximum red days in a 5-day week | **3** → fourth red day in the same week stops the week. |
| Maximum total trades in a 5-day week | **15** (5 sessions × 3 trades) |

### §3.4 Drawdown protection (buffer-aware sizing)

Per-trade risk is scaled down (never up) when buffer thins, regardless of the schedule in file 01 §9:

| Buffer remaining | Allowed per-trade risk |
|---|---|
| ≥ $2,000 | Full schedule per file 01 §9 |
| $1,000 – $1,999 | 50 % of schedule (e.g. $100 if schedule is $200) |
| $500 – $999 | 25 % of schedule (e.g. $50) |
| < $500 | **No trading.** Observation only. |

Buffer is recomputed at the start of every session from the actual Apex dashboard, not from memory.

---

## §4 Hard shutdown conditions

Any one of the following stops the business immediately for the specified period. The operator may not trade — including on a separate account, including paper — during the shutdown.

| # | Condition | Shutdown |
|---|---|---|
| S1 | Hard daily loss (−$600) hit | Rest of day + next trading day |
| S2 | Weekly loss (−$1,000) hit | Rest of week + the following week |
| S3 | Apex trailing drawdown breached | Eval over; cooling period 7 calendar days before any new eval |
| S4 | Stop placed mentally, not written, on any trade | 1 trading day |
| S5 | Position averaged down | 5 trading days + mandatory rule re-read in journal |
| S6 | Trade taken during news blackout | 2 trading days |
| S7 | Two consecutive trading days with no journal entry | Until journal resumes for 5 paper-trade days |
| S8 | Trade taken that did not match any of the three setups | 2 trading days |
| S9 | Override of `CONSILIERE_RISK` recommendation more than once in a 5-trading-day window | 5 trading days |
| S10 | Operator unable to follow routine due to schedule/illness | Pause until routine can be honored; no trading "on the side" |

Shutdowns are not negotiable. They begin at the moment the condition is logged, not the moment the operator decides to honor them.

---

## §5 Frequency, sizing, and the "no second chance" rule

### §5.1 Frequency

- **Max 3 trades per session.** Counted from the first fill, regardless of outcome.
- **2 losers → stop.** Even if only one trade has been taken so far, two losing trades in any sequence in one session ends the session.
- **2 winners → stop is encouraged but not required.** If both winners hit full target, the operator may stop voluntarily; if not, one final trade is allowed.

### §5.2 Sizing

- Sizing is determined **only** by dollar risk and stop distance. The formula is:
  `contracts = floor( per-trade-dollar-risk / (stop distance in ticks × $ per tick) )`
- If the computed contract count is `0`, the trade does not happen. The platform's size is not "rounded up."
- The contract count is computed **before** the order is sent. Sizing in the head after the order is filled is forbidden.

### §5.3 No second chance

If the operator's first stop on a trade is hit, that exact setup on that exact instrument is **finished for the session**. The market may go on to do exactly what the playbook predicted. That is acceptable. The same level is not re-entered.

---

## §6 News and event blackouts

| Event | Blackout |
|---|---|
| FOMC rate decision | 09:30 ET through close on FOMC day. No trading. |
| FOMC presser | Already in FOMC blackout. |
| CPI release | 2 min before through 5 min after 08:30 ET; further: no first-trade in first 30 min of RTH. |
| NFP release | 2 min before through 5 min after 08:30 ET; further: no first-trade in first 30 min of RTH. |
| PCE release | 2 min before through 5 min after 08:30 ET. |
| PPI release | 2 min before through 5 min after 08:30 ET. |
| Treasury auction (mid-session 13:00) | 5 min before through 5 min after. |
| Anything else flagged "high" on the economic calendar | 2 min before through 5 min after. |

If an open position is held when a high-impact event begins, the position is closed flat **before** the event prints. No exceptions.

---

## §7 The 12-item approval checklist

Every trade — without exception — must satisfy all 12 items below **before** the order is sent. The journal entry (file 05) requires each item to be ticked. `CONSILIERE_RISK` (file 06) checks the same 12 items and replies APPROVED or BLOCKED.

If any single item fails, the trade does not happen. There is no "10 out of 12 is good enough."

| # | Item | Pass condition |
|---|---|---|
| 1 | **Setup ID** | The trade matches one of the three setups in file 03 by name. Operator can state which one. |
| 2 | **Context check** | Volume profile, prior-day levels, and overnight high/low are loaded and visible on the chart. |
| 3 | **Day type** | The day type (trend / balance / open-drive / open-rejection / failed-auction) has been identified and noted, and the setup is permitted on this day type per file 03. |
| 4 | **Entry trigger present** | The specific trigger condition listed for the setup in file 03 (sweep + reclaim, displacement through LVN, etc.) has actually occurred — not "is forming." |
| 5 | **Written stop** | The stop price is identified, written into the journal, and a working stop order is placed in the platform within 3 seconds of fill. |
| 6 | **Stop distance reasonable** | Stop distance is within the per-setup range in file 03; not "tightened for size." |
| 7 | **Dollar risk within schedule** | Position size × (stop distance × $/tick) ≤ allowed per-trade risk per file 01 §9 and file 02 §3.4. |
| 8 | **Target levels identified** | TP1 and TP2 are specific price levels (HVN, prior VAH/VAL, opposite extreme), not "I'll see how it goes." |
| 9 | **R/R ≥ 1.5 to TP1** | First take-profit gives at least 1.5 R after fees. If less, the trade does not happen. |
| 10 | **No news / blackout** | No high-impact event window per §6 is active or within 5 min of becoming active. |
| 11 | **Frequency cap respected** | Counting this trade, ≤ 3 trades for the session and ≤ 2 losing trades so far. |
| 12 | **Buffer OK** | Buffer per §3.4 is at the level required for the chosen per-trade risk. |

A trade that has all 12 boxes ticked may still lose. That is normal. A trade missing any box is not a trade — it is a violation, regardless of outcome.

---

## §8 Position management after entry

Once filled, the trade is managed mechanically:

1. **Stop on**: working stop order placed within 3 seconds of fill at the written stop. No mental stops.
2. **No stop widening, ever.** Stop may only move toward break-even or toward profit. If price moves against the stop, the stop is honored. Do not "give it room."
3. **TP1 partial**: at TP1, half (or specified fraction in file 03) of the position is taken off. The remaining stop is moved to break-even.
4. **Runner**: the remaining portion targets TP2 with the trailing rule in file 03 for that setup.
5. **Time stop**: if the trade has not made meaningful progress within the setup's time-in-trade limit (file 03), exit at market.
6. **No averaging in or down.** Adding to a losing position is an automatic S5 shutdown.

---

## §9 Drawdown protection — daily and rolling

Beyond the loss limits in §3:

- After a **single −$400 soft daily** day, next session opens at **half-size sizing** until one green day closes.
- After a **two-red-day streak**, the operator opens the next session **observation-only** (no trades) regardless of buffer. Sizing returns to schedule after one green day.
- After a week ended by §3.3 weekly loss limit, the following week starts at **half-size sizing** for its entirety.

These reductions stack with the buffer-based reductions in §3.4. If both apply, the **smaller** of the two allowed sizes is used.

---

## §10 Conflicts with file 03 (playbook) and file 01 (charter)

If the playbook describes a setup that, when sized normally, would breach any §3 or §3.4 limit:

- The trade does not happen.
- The setup is flagged in the weekly review for possible revision.
- The rule in this file is not bent to make the playbook work.

If the charter (file 01) sets a per-trade risk schedule that conflicts with §3.4 (buffer-aware sizing):

- The smaller permitted amount wins.

---

## §11 Logging breaches

Every breach of this document — whether caught before the trade or after — must be logged with:

- The rule number broken.
- The time it occurred.
- What the operator was doing/thinking at the moment.
- The shutdown triggered (if any).
- The corrective action.

Breaches are logged in the daily journal entry under a dedicated `Breaches:` section. A breach that is not logged becomes, on discovery, a second breach: the original, plus the logging failure.

---

## §12 Amendment process

This document is amended only:

1. After a 90-day cycle of full process-goal compliance (file 01 §6 G2–G6).
2. After a six-month review with evidence in the journal that a specific rule is producing perverse outcomes (e.g. cutting valid trades systematically) — backed by ≥ 20 logged examples.
3. After an Apex contract change that mandates different limits than this file.

Amendments are never made on the day of a loss. They are never made after a single missed trade. They are never made because "today felt different."

The version field at the top of this file is incremented on every amendment. Past versions remain in git history.

---

*End of file 02.*
