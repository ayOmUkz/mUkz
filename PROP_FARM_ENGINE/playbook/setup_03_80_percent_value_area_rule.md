# Setup 03 — 80% Value Area Rule

**Instruments:** ES, NQ
**Execution timeframes:** 5m / 15m
**Context timeframes:** 30m / 1h
**Setup class:** Auction Rotation
**Regime validity:** `BALANCE`
**Banned in:** `TREND`, `NEWS_RISK`, `LOW_VOL_CHOP`

---

## 1. Context

The classic Steidlmayer 80% rule: when price opens **outside** prior
day's value area, re-enters value, and **holds** inside value for a
defined acceptance period, the auction has 80%+ historical probability
of trading to the opposite value extreme.

The setup pays because the prior session's value area represents fair
price; once price accepts back into that range from an extreme open,
the auction tends to rotate the full range to re-test the opposite
edge.

---

## 2. Location

The setup is valid only when:

- RTH opens **outside** prior day's value area (above VAH OR below VAL).
- Price subsequently **re-enters** value within the first 60 minutes
  RTH.
- Re-entry confirmed by closing a 30m bar inside value.

The directional bias is fixed by geometry:

- **Open above VAH, re-enter** → bias SHORT, target = VAL.
- **Open below VAL, re-enter** → bias LONG, target = VAH.

---

## 3. Trigger (sequential — all required)

| # | Step | Rule |
|---|------|------|
| 1 | **Open outside value** | RTH 09:30 ET print > prior VAH OR < prior VAL |
| 2 | **Re-entry** | Price trades back inside [VAL, VAH] within 60 min of RTH open |
| 3 | **Acceptance** | A 30m bar **closes** inside value (this is the acceptance bar) |
| 4 | **Holding** | The next 30m bar **also closes** inside value AND does not exceed the acceptance bar's near-value extreme by more than 25% of the bar's range |

---

## 4. Confirmation

Required: **MIN_CONFIRM**. Signals:

| Signal | Definition |
|--------|-----------|
| **Initiative delta into value** | CVD trends in the rotation direction during steps 2–3 |
| **Range expansion** | The acceptance bar's range ≥ 1.2× 20-bar avg |
| **Failed return to the open side** | After acceptance, no 5m close back outside value in the original open's direction |

---

## 5. Entry

- **Primary:** Limit entry on first pullback to the **edge of value**
  the auction came from (near-side VAH or VAL) after the holding bar
  closes. Tolerance: 2 ticks (ES) / 4 ticks (NQ).
- **Backup:** Market entry at close of the holding bar if no pullback
  within 2 × 30m bars.
- **Skip:** If price closes outside value in the original open
  direction after acceptance → cancel.

---

## 6. Stop

- **Hard stop:** 4 ticks beyond the open-side VA edge (ES) / 8 ticks
  beyond (NQ), or 2 ticks beyond the post-open extreme — whichever is
  **closer**.
- **Time stop:** If trade has not progressed 50% to VPOC within 60
  minutes after entry → exit at market.

---

## 7. Target

| Leg | Target | Action |
|-----|--------|--------|
| **T1** | Prior day **VPOC** | Scale **40%**, move stop to entry |
| **T2** | Opposite VA edge (VAL if short / VAH if long) | Scale **40%**, trail to last 30m swing |
| **Runner** | 1× IB beyond opposite VA edge | Trail with 30m swing structure |

**R:R floor:** ≥ 2.5R to T2 (the opposite VA edge). The 80% rule's edge
is the full rotation, not the half-rotation; if the geometry doesn't
pay 2.5R to the opposite edge, the rotation isn't worth taking.

---

## 8. Invalidation

- 5m close back outside value on the original open's direction after
  entry (the rule has failed; this is the 20%).
- **VPOC rejection mid-traversal:** price reaches VPOC, then closes 3
  consecutive 5m bars back toward the open-side VA edge → exit
  remainder, the rotation has stalled.
- Regime flips to `TREND`.
- Daily loss circuit breaker fires.

---

## 9. Risk Rule

| Mode | Per-trade risk | Max attempts/day |
|------|---------------:|-----------------:|
| Evaluation | 0.5% | 1 |
| Funded     | 0.75% | 1 |
| Scaling    | 1.0%  | 1 |

This setup fires at most **once per day** (the open-outside-value
condition is a once-per-session event).

---

## 10. A+ Grade Criteria

| Pt | Criterion |
|----|-----------|
| ☐ | Gap distance from VAH/VAL ≤ 0.75× prior VA width (large gaps fade less reliably) |
| ☐ | Re-entry occurs within **30 min** of RTH open (faster = stronger) |
| ☐ | Acceptance bar's range ≥ 1.5× 20-bar avg (range expansion confirms initiative) |
| ☐ | Bias engine output is `MEAN_REVERSION_LIKELY` or aligned with the rotation |
| ☐ | No HIGH-impact news scheduled before the projected VPOC time-of-arrival |

---

## 11. Automation Rule (IF / AND / THEN)

```
IF rth_open_price > prior_VAH OR rth_open_price < prior_VAL
AND within 60 min of RTH open, price re-enters [prior_VAL, prior_VAH]
AND a 30m bar closes inside [prior_VAL, prior_VAH]
AND the next 30m bar closes inside value
    AND does not exceed acceptance_bar's near-value extreme by > 25% of bar range
AND order_flow_confirmation(latest_bar) >= MIN_CONFIRM
AND regime == BALANCE
AND projected_R_to_opposite_VA >= 2.5
AND risk_state == OPEN
AND attempts_today["03_80_percent_value_area"] < 1
THEN emit signal {
    setup:  "03_80_percent_value_area",
    side:   "SHORT" if opened_above_VAH else "LONG",
    grade:  a_plus_grader(...),
    entry:  open_side_VA_edge,
    stop:   open_side_VA_edge + buffer[symbol] OR post_open_extreme + 2 ticks (whichever closer),
    t1:     prior_day_VPOC,
    t2:     opposite_VA_edge,
    payload: standard schema
}
```

---

## 12. Failure Conditions

1. **No acceptance** — re-entry without 30m close inside value;
   this is just a wick through value, not the 80% setup.
2. **Range collapse after acceptance** — if the next 30m bar's range
   is < 60% of the acceptance bar, the auction has stalled; skip the
   pullback entry.
3. **News-driven gap** — gaps from overnight news headlines are less
   likely to fade. Filter via news calendar before the open.
4. **Wide-gap day** — gap > 1× prior VA width is a structural break,
   not a fadeable extreme; skip.

---

## 13. Journal Fields

```
date, instrument, side, gap_direction, gap_distance_ticks,
prior_VAH, prior_VAL, prior_VPOC,
reentry_minutes_after_open, acceptance_bar_range_x_avg,
holding_bar_close_inside, confirmation_flags[], grade,
entry, stop, t1_hit, t2_hit, exit_price, exit_reason,
R_realized, mfe_R, mae_R, notes_link
```
