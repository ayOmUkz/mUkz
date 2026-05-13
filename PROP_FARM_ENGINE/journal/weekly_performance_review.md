# Weekly Performance Review — Template

Run every Sunday evening (or Friday after close). The review is
**mandatory** — it is the only place where playbook parameter changes
are debated and decided.

File location: `journal/weekly/YYYY-WW.md` (ISO week).

---

## 1. Period Header

| Field | Value |
|-------|-------|
| Week | YYYY-WW |
| Sessions traded | ____ |
| Locked sessions | ____ |
| Stand-down days | ____ |
| Mode active | Evaluation / Funded / Scaling |
| Starting equity (Mon open) | $____ |
| Ending equity (Fri close) | $____ |
| Weekly P/L $ | $____ |
| Weekly P/L % | ____ % |
| Highest DD from peak this week | ____ % |

---

## 2. Trade Stats

| Metric | Value |
|--------|-------|
| Trades taken | ____ |
| Wins | ____ |
| Losses | ____ |
| Breakeven | ____ |
| Win rate | ____ % |
| Expectancy (R/trade) | ____ R |
| Avg winner (R) | ____ |
| Avg loser (R) | ____ |
| Profit factor | ____ |
| Largest winner (R) | ____ |
| Largest loser (R) | ____ |
| Avg hold time (min) | ____ |
| Max consecutive losses | ____ |
| Max consecutive wins | ____ |
| Rejections by gate (count) | ____ |

---

## 3. Setup-by-Setup Breakdown

| Setup | Signals | Taken | Win % | Expectancy | Avg MFE | Avg MAE | Notes |
|-------|--------:|------:|------:|----------:|--------:|--------:|-------|
| 01 Liquidity Sweep | | | | | | | |
| 02 VA Rejection | | | | | | | |
| 03 80% VA Rule | | | | | | | |
| 04 LVN Rejection | | | | | | | |
| 05 Initiative Breakout | | | | | | | |

**Underperformers (expectancy < 0R over rolling 30 trades):**
__________________________

**Top performer this week:** __________________________

---

## 4. Regime Breakdown

| Regime | Trades | Win % | Expectancy | Notes |
|--------|-------:|------:|-----------:|-------|
| TREND | | | | |
| BALANCE | | | | |
| VOL_EXP | | | | |
| LOW_VOL_CHOP (no trade expected) | | | | |
| NEWS_RISK (no trade expected) | | | | |

If trades occurred in `LOW_VOL_CHOP` or `NEWS_RISK`, document the rule
violation: __________________________

---

## 5. Daily State Tracking

| Day | Highest state | Tier-down? | Locked? | Behavioral lock? | Rule violations |
|-----|--------------|-----------|---------|------------------|----------------:|
| Mon | | | | | |
| Tue | | | | | |
| Wed | | | | | |
| Thu | | | | | |
| Fri | | | | | |

---

## 6. Bias & Regime Accuracy

| Day | Bias classification | Actual day type | Match? |
|-----|---------------------|-----------------|:------:|
| Mon | | | Y / N |
| Tue | | | Y / N |
| Wed | | | Y / N |
| Thu | | | Y / N |
| Fri | | | Y / N |

**Bias accuracy this week:** ____ / 5 (target ≥ 3/5).

**Regime stability:** total regime transitions across the week: ____.

---

## 7. Rule Violations & Behavioral Issues

| # | Day | Setup | Type (oversize / off-playbook / revenge / FOMO / override) | Description |
|---|-----|-------|-----------------------------------------------------------|-------------|
| | | | | |

Each violation requires a **written corrective action**:

- Violation 1 → corrective: __________________________
- Violation 2 → corrective: __________________________

**Cumulative violations in rolling 4-week window:** ____  (≥ 3 →
mandatory tier-down for next week).

---

## 8. Rolling 20-Trade Statistics (gate inputs)

| Metric | Value | Move-up gate (Funded → Scaling) | Pass? |
|--------|-------|--------------------------------|:----:|
| Expectancy (R) | ____ | ≥ +0.5 | |
| Profit factor | ____ | ≥ 1.8 | |
| Max DD (R) | ____ | ≤ 3 | |
| Locked sessions (rolling 10) | ____ | 0 | |
| Win rate | ____ | ≥ 45% | |
| Trade count | ____ | ≥ 40 | |

**Scaling recommendation:** PROMOTE / STAY / TIER-DOWN

---

## 9. Playbook Parameter Review

For each setup, evaluate whether parameters need adjustment **only**
if the setup has ≥ 30 trades in its rolling window and expectancy is
< 0R:

| Setup | Trades (rolling 30) | Expectancy | Proposed change | Decision |
|-------|--------------------:|-----------:|-----------------|----------|
| 01 | | | | |
| 02 | | | | |
| 03 | | | | |
| 04 | | | | |
| 05 | | | | |

**Proposed parameter changes apply NEXT week, not this week.**
Document the rationale in detail; no mid-week changes.

---

## 10. Lessons & Themes

**Top 3 patterns observed this week:**

1. __________________________
2. __________________________
3. __________________________

**Setup hierarchy quality (gut sense + data):**

- Most reliable setup this week: ____ — why?
- Least reliable setup this week: ____ — why?

**Operator state across the week:**

- Average focus (1–5): ____
- Days with poor focus: ____ → did they correlate with rule
  violations or losses? __________________________

---

## 11. Next-Week Adjustments

**Trading plan adjustments (operator-controlled):**

- Time-window restriction: __________________________
- Setup priority for the week: __________________________
- Size adjustments: __________________________
- Mandatory stand-down conditions: __________________________

**System adjustments (parameter changes, queued for paper validation):**

- __________________________

---

## 12. Promotion / Tier-Down Decision

**Current mode:** ____________
**Recommended next-week mode:** ____________

**Justification (1 paragraph):**

> __________________________________________________________________

If tier-down is triggered automatically, the engine has already
applied it. The weekly review **does not override** an automatic
tier-down.

---

## 13. Machine-Readable Block (engine appends)

```json
{
  "week": "YYYY-WW",
  "sessions": 5, "locked_sessions": 0, "stand_down_days": 0,
  "weekly_pnl_pct": 0.0,
  "trades_count": 0,
  "win_rate": 0.0,
  "expectancy_R": 0.0,
  "profit_factor": 0.0,
  "max_dd_R": 0.0,
  "rule_violations": 0,
  "setup_expectancy": {
    "01": 0.0, "02": 0.0, "03": 0.0, "04": 0.0, "05": 0.0
  },
  "regime_distribution": {
    "TREND": 0, "BALANCE": 0, "VOL_EXP": 0, "LOW_VOL_CHOP": 0, "NEWS_RISK": 0
  },
  "scaling_recommendation": "STAY"
}
```
