# Daily Trade Journal — Template

Fill one of these per session. Copy this file to
`journal/sessions/YYYY-MM-DD.md` at the start of each day.

---

## Header

| Field | Value |
|-------|-------|
| Date | YYYY-MM-DD |
| Day of week | __________ |
| Session start equity | $__________ |
| Active mode | Evaluation / Funded / Scaling |
| Trailing DD buffer at open | ____ % |
| Operator state (1–5) | ____  (5 = fully present, 1 = unfocused) |

---

## Section 1 — Pre-Session Prep (from `premarket_checklist.md`)

| Item | Value |
|------|-------|
| Bias classification | __________ |
| Bias confidence (0–100) | __________ |
| Pre-open regime guess | __________ |
| Allowed setups today | __________ |
| Banned setups today | __________ |
| News windows (ET) | __________ |
| A+ plan (setup + level) | __________ |
| Stand-down? | Yes / No |

**Key levels card:**

```
PDH:    ______      PDL:    ______
ONH:    ______      ONL:    ______
VAH:    ______      VAL:    ______
VPOC:   ______
Wk H:   ______      Wk L:   ______
IBH:    ______ (post-10:30)    IBL: ______ (post-10:30)
Unrun pools: __________
```

---

## Section 2 — Bias Log (during session)

Update at 10:30 ET (post-IB) and 12:00 ET (mid-session):

| Time | Regime | Bias confidence | Notes |
|------|--------|-----------------|-------|
| 09:30 | ______ | ______ | open-type observed: ______ |
| 10:30 | ______ | ______ | IB shape: wide / narrow / median |
| 12:00 | ______ | ______ | morning summary |
| 14:00 | ______ | ______ | afternoon read |
| 16:00 | ______ | ______ | close summary |

---

## Section 3 — Trade Log

Add one row per trade taken (or attempted and rejected by gate):

| # | Time ET | Instr | Setup | Side | Grade | Entry | Stop | T1 | T2 | Size | Risk $ | Risk % | Exit | R | MFE | MAE | Reason / Notes |
|---|---------|-------|-------|------|-------|------:|-----:|---:|---:|-----:|-------:|-------:|------|--:|----:|----:|---------------|
| 1 | | | | | | | | | | | | | | | | | |
| 2 | | | | | | | | | | | | | | | | | |
| 3 | | | | | | | | | | | | | | | | | |
| 4 | | | | | | | | | | | | | | | | | |

For each trade, link to the per-trade review (`setup_review_template.md`).

### Rejected Signals (by pre-trade gate)

| # | Time ET | Instr | Setup | Grade | Reason code | Notes |
|---|---------|-------|-------|-------|-------------|-------|
| | | | | | | |

---

## Section 4 — Daily State Tracking

| Event | Time | Notes |
|-------|------|-------|
| Highest daily state reached | ______ | (CAUTION / A_PLUS_ONLY / LOCKED / GREEN_PROTECT / STOP_FOR_DAY) |
| Tier-down applied? | Y / N | trigger: ______ |
| Behavioral lock fired? | Y / N | reason: ______ |
| News blackout windows entered | ______ | count |
| Kill switch fires | ______ | which, why |

---

## Section 5 — Daily P/L Summary

| Metric | Value |
|--------|-------|
| Realized R (sum) | ______ |
| Realized $ | $______ |
| Realized % of equity | ______ % |
| Win count | ______ |
| Loss count | ______ |
| Breakeven count | ______ |
| Largest R win | ______ |
| Largest R loss | ______ |
| Expectancy this session | ______ R/trade |
| End-of-session equity | $______ |
| Daily DD from session peak | ______ % |

---

## Section 6 — Setup Performance Today

| Setup | Signals | Taken | Wins | Losses | Realized R |
|-------|--------:|------:|-----:|-------:|-----------:|
| 01 Liquidity Sweep | | | | | |
| 02 VA Rejection | | | | | |
| 03 80% VA Rule | | | | | |
| 04 LVN Rejection | | | | | |
| 05 Initiative Breakout | | | | | |

---

## Section 7 — Post-Session Review

**What worked today (rule-based observations):**

- __________
- __________

**What did not work:**

- __________
- __________

**Rule violations attempted or made:**

- __________

**Bias accuracy:** Match / Partial / Miss
**Regime accuracy:** Match / Partial / Miss
**Did the system surface the A+ plan?** Yes / No

**One thing to adjust tomorrow:**

- __________

**Carry-over notes for next session:**

- __________

---

## Section 8 — Auto-Generated Fields (for engine to fill)

```json
{
  "date": "YYYY-MM-DD",
  "session_realized_R": 0.0,
  "session_realized_pct": 0.0,
  "trades_count": 0,
  "wins": 0,
  "losses": 0,
  "rejections": 0,
  "highest_daily_state": "OPEN",
  "tier_down_applied": false,
  "kill_switch_fires": [],
  "rolling_20_expectancy_R": 0.0,
  "rolling_20_profit_factor": 0.0,
  "trailing_dd_buffer_pct_close": 0.0
}
```
