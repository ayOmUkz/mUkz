# Setup 04 — LVN Rejection / Auction Failure

**Instruments:** ES, NQ
**Execution timeframes:** 1m / 5m
**Context timeframes:** 30m / 1h
**Setup class:** Reversal / Auction Failure
**Regime validity:** `BALANCE`, `VOLATILITY_EXPANSION`
**Banned in:** `TREND`, `NEWS_RISK`, `LOW_VOL_CHOP`

---

## 1. Context

A **Low Volume Node (LVN)** is a price level where the prior auction
spent minimal time — a "single print" or thin structure. LVNs are
auction skips: when price returns to them from the strong side and
fails to build acceptance, the rejection is sharp because there is no
prior inventory to defend the level.

The thesis: price tests an LVN, the auction **fails to accept**, and
trapped momentum reverses. The setup is taken on the failure plus
reclaim of the LVN edge from which the test came.

---

## 2. Location

The setup is valid at any LVN identified by the volume profile, with
these qualifiers:

- LVN volume per price ≤ **40%** of the session VPOC's volume per price.
- LVN must be **adjacent to an HVN** on the strong side (the
  composite is HVN → LVN gap → distant HVN; we test the LVN from the
  near HVN side).
- LVN must be at least **3 ticks wide** (ES) or **6 ticks wide** (NQ)
  to be tradable — narrower LVNs slip through.

**Sources for LVNs:**

- Prior day's volume profile.
- Composite weekly profile.
- IB-extension profile if the IB is fully formed.

---

## 3. Trigger (sequential — all required)

| # | Step | Rule |
|---|------|------|
| 1 | **Attack** | Price enters the LVN from the strong-side HVN (≥ 2 × 1m bars trading inside the LVN range) |
| 2 | **Failure to accept** | Within ≤ 3 × 5m bars, the LVN is **not** accepted: no 5m bar closes with > 70% of its body inside the LVN |
| 3 | **Rejection** | A 5m bar closes back at or beyond the strong-side HVN edge with body ≥ 50% of bar range |
| 4 | **Order flow** | Trapped-momentum signal (see § 4) |

---

## 4. Confirmation

Required: **MIN_CONFIRM**, STRONG_CONFIRM for A+.

| Signal | Definition |
|--------|-----------|
| **Delta reversal** | CVD makes higher-high (for upside attack) followed by lower-low within 5 × 1m bars — trapped longs |
| **Aggressive print failure** | ≥ 2 consecutive 1m bars with delta > 1.5× 20-bar avg followed by reversal print with opposite-side delta ≥ 1.5× 20-bar avg |
| **Absorption inside LVN** | Volume in LVN range ≥ 1.5× expected (based on time-spent × prior VPOC vol/price) but no closing acceptance |
| **Tape exhaustion** | Print rate drops > 40% within 60s after the LVN extreme is set |

---

## 5. Entry

- **Primary:** Limit at the strong-side HVN edge on retest after the
  rejection bar. Tolerance: 1 tick (ES) / 2 ticks (NQ).
- **Backup:** Market at close of the rejection bar if no retest within
  3 × 5m bars.
- **Skip:** If a 5m bar closes with > 70% of its body inside the LVN
  before entry fills → the auction has accepted, cancel.

---

## 6. Stop

- **Hard stop:** Beyond the deepest 1m wick into the LVN by 2 ticks
  (ES) / 4 ticks (NQ).
- **Time stop:** If +1R not reached within 15 minutes → exit at market.

---

## 7. Target

| Leg | Target | Action |
|-----|--------|--------|
| **T1** | Middle of the originating HVN | Scale **50%**, move stop to entry |
| **T2** | Far edge of the originating HVN OR prior session VPOC (whichever closer) | Scale **30%**, trail to last 5m swing |
| **Runner** | Next composite level beyond | Trail with 5m swings |

**R:R floor:** ≥ 2.0R to T1.

---

## 8. Invalidation

- 5m close with > 70% of body inside the LVN after entry (acceptance
  achieved against the trade).
- Price prints a new extreme beyond the original LVN penetration after
  entry.
- Regime flips to `TREND` against the trade.
- Daily loss circuit breaker fires.

---

## 9. Risk Rule

| Mode | Per-trade risk | Max attempts/day |
|------|---------------:|-----------------:|
| Evaluation | 0.5% | 2 |
| Funded     | 0.75% | 2 |
| Scaling    | 1.0%  | 2 |

LVN setups in ES and NQ on the same side within 5 min: apply the
universal correlation rule (40% reduction on second leg).

---

## 10. A+ Grade Criteria

| Pt | Criterion |
|----|-----------|
| ☐ | LVN is a confirmed **single print** on prior day's profile (multiple ticks with single TPO) |
| ☐ | The originating HVN has ≥ 2 prior touches with rejection (composite support/resistance) |
| ☐ | STRONG_CONFIRM order flow (≥ 2 signals) |
| ☐ | Test occurs in 09:30–11:30 ET prime window |
| ☐ | Bias side aligns with the rejection direction OR bias = `BALANCED` |

---

## 11. Automation Rule (IF / AND / THEN)

```
IF an LVN is identified where:
    lvn_volume_per_price <= 0.40 * session_vpoc_volume_per_price
    AND lvn_width_ticks >= min_lvn_width[symbol]
    AND lvn is adjacent to a strong-side HVN
AND price enters the LVN range from the strong side
    AND >= 2 × 1m bars trade inside the LVN
AND within next <= 3 × 5m bars, no 5m bar closes with body_inside_lvn_pct > 0.70
AND a 5m bar closes back at/beyond the strong-side HVN edge
    AND body_pct >= 0.50
AND order_flow_confirmation(bar) ∈ {MIN_CONFIRM, STRONG_CONFIRM}
AND regime ∈ {BALANCE, VOLATILITY_EXPANSION}
AND time_of_day ∈ {09:30–11:30 ET, 13:30–15:30 ET}
AND risk_state == OPEN
AND attempts_today["04_lvn_rejection"] < 2
AND projected_R_to_T1 >= 2.0
THEN emit signal {
    setup:  "04_lvn_rejection",
    side:   "LONG" | "SHORT",  (away from the LVN, toward the originating HVN)
    grade:  a_plus_grader(...),
    entry:  strong_side_HVN_edge,
    stop:   deepest_LVN_wick + buffer[symbol],
    t1:     mid_HVN,
    t2:     far_HVN_edge OR prior_VPOC (closer),
    payload: standard schema
}
```

### `min_lvn_width[symbol]`

| Symbol | Min width |
|--------|-----------|
| ES | 3 ticks |
| NQ | 6 ticks |

---

## 12. Failure Conditions

1. **Slow acceptance** — if the auction grinds into the LVN over many
   bars (≥ 5 × 5m bars trading inside), it's building new value, not
   skipping. Skip.
2. **News spike into LVN** — same as Setup 01: filter via news window.
3. **LVN too wide** — LVNs > 2× min_lvn_width are typically traversed,
   not rejected; require additional confluence (PDH/PDL, VAH/VAL) to
   trade.
4. **No strong-side HVN** — without a structural anchor to enter from,
   the entry has no clean stop placement. Skip.

---

## 13. Journal Fields

```
date, instrument, side, lvn_price, lvn_width_ticks,
lvn_volume_per_price_pct_of_vpoc, originating_hvn_price,
bars_inside_lvn, max_body_inside_lvn_pct, confirmation_flags[],
grade, entry, stop, t1, t2, exit_price, exit_reason,
R_realized, mfe_R, mae_R, notes_link
```
