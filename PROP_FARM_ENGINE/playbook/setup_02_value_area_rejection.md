# Setup 02 — Value Area Rejection

**Instruments:** ES, NQ
**Execution timeframes:** 1m / 5m
**Context timeframes:** 30m / 1h
**Setup class:** Responsive / Mean Reversion
**Regime validity:** `BALANCE`
**Banned in:** `TREND`, `VOLATILITY_EXPANSION`, `NEWS_RISK`, `LOW_VOL_CHOP`

---

## 1. Context

Price tests **VAH** or **VAL** from the inside of prior day's value
area. The auction probes outside value, fails to find acceptance, and
rotates back toward VPOC. This is a textbook responsive trade: fade the
extreme, target the mean.

The setup pays because in `BALANCE` regimes value is sticky — single
prints back into value tend to fill, and the opposite VA edge is a
reasonable second target.

---

## 2. Location

The setup is valid **only** at:

- **Prior-day VAH** (for short setup).
- **Prior-day VAL** (for long setup).

Tolerance: the first test of the level after RTH open. A "test" is
defined as price trading within 2 ticks of the level on a 1m bar.

**Levels that do NOT qualify:**

- 2nd or later test of VAH/VAL same session.
- VAH/VAL that has already been accepted outside (defined as 2
  consecutive 30m closes outside value).
- Composite VAH/VAL during news-impacted prior sessions.

---

## 3. Trigger (sequential — all required)

| # | Step | Rule |
|---|------|------|
| 1 | **Approach** | Price trades within 2 ticks of VAH (or VAL) on a 1m bar |
| 2 | **Rejection bar (5m)** | A 5m bar closes back inside value with body ≥ 50% of bar range AND wick beyond the level ≥ 30% of bar range |
| 3 | **Order flow** | Responsive flow signal (see § 4) |
| 4 | **No acceptance** | Price has not printed 2 consecutive 30m closes outside value at any point in the test |

---

## 4. Confirmation

Required: **MIN_CONFIRM**, prefer STRONG_CONFIRM for A+. Signals:

| Signal | Definition |
|--------|-----------|
| **Responsive delta** | On the rejection 5m bar, delta is opposite to the prior approach direction (negative delta on a high test, positive on a low test) |
| **CVD reversal** | CVD turns down (for short) / up (for long) within the rejection bar |
| **No acceptance candle pattern** | Long wick (≥ 60% of bar range) beyond the level with close back inside value |
| **Volume spike with no progress** | Rejection bar volume ≥ 1.5× 20-bar avg, range ≤ 70% of 20-bar avg |

---

## 5. Entry

- **Primary:** Limit on retest of VAH/VAL level after the rejection
  bar. Tolerance: 1 tick (ES) / 2 ticks (NQ).
- **Backup:** Market at close of rejection bar if no retest within
  3 × 5m bars.
- **Skip:** If price closes outside value on a 5m bar after the
  rejection trigger → cancel.

---

## 6. Stop

- **Hard stop:** 3 ticks beyond the rejection bar's extreme (ES) /
  5 ticks beyond (NQ).
- **Time stop:** If trade has not reached +0.7R within 20 minutes →
  exit at market.

---

## 7. Target

| Leg | Target | Action |
|-----|--------|--------|
| **T1** | Prior day **VPOC** | Scale **60%**, move stop to entry |
| **T2** | Opposite VA edge (VAL for short / VAH for long) | Scale **30%**, trail to last 5m swing |
| **Runner** | Beyond opposite VA edge by 1× ATR(5m, 20) | Trail with 5m swings |

**R:R floor:** ≥ 1.8R to T1 (lower than Setup 01 because the path to
VPOC is statistically reliable in `BALANCE`).

---

## 8. Invalidation

- 5m close outside value in the direction of the original approach
  after entry.
- 2 consecutive 30m closes outside value at any time.
- Regime flips from `BALANCE` to `TREND` or `VOLATILITY_EXPANSION`.
- Daily loss circuit breaker fires.

---

## 9. Risk Rule

| Mode | Per-trade risk | Max attempts/day |
|------|---------------:|-----------------:|
| Evaluation | 0.5% | 2 |
| Funded     | 0.75% | 2 |
| Scaling    | 1.0%  | 2 |

Sizing formula and tick values: see Setup 01 § 9.

---

## 10. A+ Grade Criteria

| Pt | Criterion |
|----|-----------|
| ☐ | First test of VAH/VAL in the session |
| ☐ | Overnight inventory **opposes** the test direction (long inventory → short the VAH test) |
| ☐ | STRONG_CONFIRM order flow (≥ 2 signals) |
| ☐ | Bias is `BALANCED` or aligned with the rejection direction |
| ☐ | Test occurs in 09:30–11:30 ET or 13:30–14:30 ET |

---

## 11. Automation Rule (IF / AND / THEN)

```
IF price within 2 ticks of {VAH | VAL} on a 1m bar
AND the latest closed 5m bar shows:
    close back inside value
    AND body_pct >= 0.50
    AND wick_beyond_level_pct >= 0.30
AND order_flow_confirmation(bar) ∈ {MIN_CONFIRM, STRONG_CONFIRM}
AND no_acceptance_outside_value(last 30m bars) == true
AND regime == BALANCE
AND time_of_day ∈ {09:30–11:30 ET, 13:30–14:30 ET}
AND risk_state == OPEN
AND attempts_today["02_value_area_rejection"] < 2
AND projected_R_to_VPOC >= 1.8
THEN emit signal {
    setup:  "02_value_area_rejection",
    side:   "SHORT" | "LONG",
    grade:  a_plus_grader(...),
    entry:  level (VAH or VAL),
    stop:   rejection_bar_extreme + buffer[symbol],
    t1:     prior_day_VPOC,
    t2:     opposite_VA_edge,
    payload: standard schema
}
```

---

## 12. When to Avoid

- **TREND days** — the level breaks, doesn't hold.
- **Wide-VA prior sessions** — VA wider than 1.5× 20-day avg suggests
  the prior session was already trending; rotation is unreliable.
- **News-impacted prior session** — VPOC is artificial.
- **2nd or later test** — first test is responsive, repeat tests are
  acceptance probes (continuation-prone).

---

## 13. Journal Fields

```
date, instrument, side, level_name (VAH|VAL), level_price,
rejection_bar_body_pct, rejection_bar_wick_pct,
confirmation_flags[], inventory_state, grade, entry, stop,
vpoc_target, vpoc_hit, exit_price, exit_reason,
R_realized, mfe_R, mae_R, notes_link
```
