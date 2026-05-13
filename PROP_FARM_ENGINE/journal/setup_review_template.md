# Setup Review — Per-Trade Template

One review per trade. Fill within 30 minutes of position close while
the context is fresh. Link from the row in
`daily_trade_journal.md` § 3.

File location: `journal/trades/YYYY-MM-DD/HHmm-{setup}-{side}.md`.

---

## 1. Trade Card

| Field | Value |
|-------|-------|
| Date | YYYY-MM-DD |
| Entry time (ET) | HH:MM:SS |
| Instrument | ES / NQ |
| Setup | 01 / 02 / 03 / 04 / 05 |
| Side | LONG / SHORT |
| Grade | A+ / A / B |
| Size (contracts) | ____ |
| Entry price | ____ |
| Stop price | ____ |
| T1 price | ____ |
| T2 price | ____ |
| Runner target | ____ |
| Stop ticks | ____ |
| Tick value | $____ (ES $12.50 / NQ $5.00) |
| Risk $ | $____ |
| Risk % | ____ % |
| Projected R to T1 | ____ R |

---

## 2. Context at Entry

- **Regime:** TREND / BALANCE / VOL_EXP / LOW_VOL_CHOP / NEWS_RISK
- **Daily bias:** LONG / SHORT / BALANCED / … (confidence: ____)
- **Daily P/L state at entry:** OPEN / CAUTION / A_PLUS_ONLY / …
- **News window?** Yes / No  (next event: ____)
- **VIX context:** ____ vs 20d MA ____
- **Time of day:** PRIME / OPEN / LUNCH / CLOSING

---

## 3. Trigger Verification

For each step in the setup's § 3 (Trigger), confirm it was satisfied:

- [ ] Step 1: ___________________________  (observed value: ____)
- [ ] Step 2: ___________________________  (observed value: ____)
- [ ] Step 3: ___________________________  (observed value: ____)
- [ ] Step 4: ___________________________  (observed value: ____)

If any step was skipped or forced → **rule violation**, log in § 8.

---

## 4. Confirmation Verification

| Signal | Fired? | Notes |
|--------|:------:|-------|
| Delta divergence | Y / N | |
| CVD reversal | Y / N | |
| Absorption | Y / N | |
| Trapped aggression | Y / N | |
| Footprint imbalance flip | Y / N | |
| Tape exhaustion | Y / N | |
| Failed continuation | Y / N | |
| Volume expansion | Y / N | |

**Classification:** STRONG_CONFIRM / MIN_CONFIRM / NO_CONFIRM / WARNING

**Counter-signals observed:** ____________________

---

## 5. A+ Grade Audit

Per setup file § 10 (re-check all 5 points):

- [ ] Point 1: ___________________________
- [ ] Point 2: ___________________________
- [ ] Point 3: ___________________________
- [ ] Point 4: ___________________________
- [ ] Point 5: ___________________________

**Score:** ____ / 5  →  Grade taken: ____  Grade earned: ____

If grade taken ≠ grade earned, document the discrepancy.

---

## 6. Management Timeline

| Time ET | Event | Decision | Notes |
|---------|-------|----------|-------|
| HH:MM | Entry filled at ____ | — | |
| HH:MM | Price reached +____R | T1 scale 50% / hold | |
| HH:MM | Stop moved to ____ | per setup § 7 | |
| HH:MM | T2 reached | scale ____% / trail | |
| HH:MM | Stop hit / Target hit / Exit decision | exited at ____ | reason: ____ |

---

## 7. Outcome

| Metric | Value |
|--------|-------|
| Exit price | ____ |
| Exit reason | T1 / T2 / Stop / Time stop / Invalidation / Manual |
| R realized | ____ |
| $ realized | $____ |
| MFE (Max Favorable Excursion in R) | ____ |
| MAE (Max Adverse Excursion in R) | ____ |
| Hold time (min) | ____ |
| Slippage entry (ticks) | ____ |
| Slippage exit (ticks) | ____ |

---

## 8. Lessons & Discipline

**Did this trade follow the playbook?** Yes / No

If No, describe the deviation: ___________________________

**Did the operator follow the management plan?** Yes / No

If No, describe: ___________________________

**Behavioral check:**

- [ ] No revenge entry
- [ ] No FOMO
- [ ] Size matched the formula
- [ ] Stop placement was structural (not arbitrary)
- [ ] Targets were predefined, not reached for

**Rule violations (any):** ___________________________

---

## 9. Screenshots (placeholders)

- [ ] Pre-entry: ![pre-entry](./img/HHmm-pre.png)
- [ ] Entry: ![entry](./img/HHmm-entry.png)
- [ ] Mid-trade: ![mid](./img/HHmm-mid.png)
- [ ] Exit: ![exit](./img/HHmm-exit.png)

Annotate: level, sweep extreme (if applicable), reclaim bar, entry,
stop, T1, T2, OF signals on the bar.

---

## 10. One-Line Lesson

> ___________________________________________________________________

This single line feeds the weekly review.

---

## 11. Machine-Readable Block (engine appends)

```json
{
  "trade_id": "YYYYMMDD-HHmm-{setup}-{side}",
  "date": "YYYY-MM-DD",
  "instrument": "ES",
  "setup": "01",
  "side": "SHORT",
  "grade_taken": "A+",
  "grade_earned": "A+",
  "entry": 0.00, "stop": 0.00, "t1": 0.00, "t2": 0.00,
  "size_contracts": 0,
  "risk_$": 0.00, "risk_pct": 0.0,
  "exit_price": 0.00, "exit_reason": "T1",
  "R_realized": 0.0, "mfe_R": 0.0, "mae_R": 0.0,
  "confirmation": ["DELTA_DIVERGENCE", "ABSORPTION"],
  "regime": "BALANCE", "bias": {"side": "SHORT", "confidence": 64},
  "rule_violations": []
}
```
