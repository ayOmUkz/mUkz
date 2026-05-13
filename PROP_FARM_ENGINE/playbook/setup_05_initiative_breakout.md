# Setup 05 — Initiative Breakout Through LVN

**Instruments:** ES, NQ
**Execution timeframes:** 1m / 5m
**Context timeframes:** 30m / 1h
**Setup class:** Initiative / Continuation
**Regime validity:** `TREND`, `VOLATILITY_EXPANSION`
**Banned in:** `BALANCE`, `NEWS_RISK`, `LOW_VOL_CHOP`

---

## 1. Context

The mirror image of Setup 04. Price coils against a Low Volume Node
edge, builds energy, and breaks through the LVN with **strong delta**,
**volume expansion**, and post-breakout acceptance. The setup pays
because the LVN is auction skip-zone: once initiative breaks the edge,
price tends to traverse the LVN quickly toward the next HVN.

The trade is taken on the pullback that **holds** the breakout zone —
not on the break itself.

---

## 2. Location

The setup is valid at any LVN identified by the volume profile, with:

- LVN volume per price ≤ **40%** of session VPOC's volume per price.
- LVN width: 3 ticks ES / 6 ticks NQ minimum, **up to 2× min** maximum.
  Wider LVNs require additional confluence (Setup 04 § 12).
- A clear **HVN target** on the far side of the LVN (the next zone of
  acceptance).

---

## 3. Trigger (sequential — all required)

| # | Step | Rule |
|---|------|------|
| 1 | **Coiling** | ≥ 6 × 5m bars trade within 1× ATR(5m, 20) of the LVN's near edge |
| 2 | **Breakout bar (5m)** | A 5m bar closes through the LVN with: body ≥ 60% of bar range AND range ≥ 1.5× 20-bar avg |
| 3 | **Delta confirm** | Breakout bar delta ≥ 1.5× 20-bar avg, in the breakout direction |
| 4 | **Pullback hold** | After breakout, the first pullback retraces ≤ 50% of the breakout bar AND does not close back inside the LVN |
| 5 | **Acceptance** | A 5m bar closes beyond the LVN's far edge after the pullback |

---

## 4. Confirmation

Required: **MIN_CONFIRM**, STRONG_CONFIRM for A+.

| Signal | Definition |
|--------|-----------|
| **CVD breakout** | CVD makes a new 60-min high (for long) / low (for short) on the breakout bar |
| **Volume expansion** | Breakout bar volume ≥ 1.5× 20-bar avg AND ≥ 2× the average of the prior coiling bars |
| **No counter-imbalance** | Pullback bars show no opposite-side 3:1 footprint imbalance |
| **Tape acceleration** | Print rate during breakout bar ≥ 1.5× 60-min average |

---

## 5. Entry

- **Primary:** Limit at the LVN's **near edge** (the breakout origin)
  on the pullback. Tolerance: 1 tick (ES) / 2 ticks (NQ).
- **Backup:** Market at close of the acceptance bar (step 5) if the
  pullback overshoots the near edge but the acceptance prints.
- **Skip:** If pullback closes back inside the LVN on a 5m bar → the
  breakout has failed, cancel.

---

## 6. Stop

- **Hard stop:** 2 ticks beyond the deepest pullback wick (ES) /
  4 ticks beyond (NQ), AND must be inside or beyond the LVN's near
  edge — whichever stop is **tighter**.
- **Time stop:** If +1R not reached within 20 minutes → exit at
  market.

---

## 7. Target

| Leg | Target | Action |
|-----|--------|--------|
| **T1** | Mid-point between LVN and far HVN | Scale **40%**, move stop to entry |
| **T2** | Near edge of far HVN | Scale **40%**, trail to last 5m swing |
| **Runner** | Far HVN VPOC | Trail with 5m swing structure |

**R:R floor:** ≥ 2.0R to T1.

---

## 8. Invalidation

- 5m close back inside the LVN after entry (breakout failed).
- Pullback wick exceeds the breakout bar's open in the original
  coiling direction.
- Regime flips to `BALANCE` and price stalls > 6 × 5m bars without
  progressing toward T1.
- Daily loss circuit breaker fires.

---

## 9. Risk Rule

| Mode | Per-trade risk | Max attempts/day |
|------|---------------:|-----------------:|
| Evaluation | 0.5% | 2 |
| Funded     | 0.75% | 2 |
| Scaling    | 1.0%  | 2 |

In `VOLATILITY_EXPANSION`, half-size on entries (volatility cap; see
`market_context/market_regime_filter.md`).

---

## 10. A+ Grade Criteria

| Pt | Criterion |
|----|-----------|
| ☐ | Regime is `TREND` and bias side matches the breakout direction |
| ☐ | Coiling phase had ≥ 8 × 5m bars (more energy buildup = stronger break) |
| ☐ | Breakout bar volume ≥ **2×** 20-bar avg (vs the 1.5× minimum) |
| ☐ | STRONG_CONFIRM order flow (≥ 2 signals) |
| ☐ | Setup fires in 09:30–11:30 ET or 13:30–15:00 ET |

---

## 11. Automation Rule (IF / AND / THEN)

```
IF an LVN is identified (per Setup 04 § 11 LVN definition, capped at 2× min width)
AND >= 6 × 5m bars trade within ATR(5m, 20) of the LVN's near edge
AND a 5m bar closes through the LVN with:
    body_pct >= 0.60
    AND range >= 1.5 * avg_range_20
    AND delta >= 1.5 * avg_delta_20 (in breakout direction)
AND the next pullback:
    retraces <= 50% of the breakout bar
    AND does NOT close back inside the LVN on a 5m basis
AND a subsequent 5m bar closes beyond the LVN's far edge
AND order_flow_confirmation(bar) ∈ {MIN_CONFIRM, STRONG_CONFIRM}
AND regime ∈ {TREND, VOLATILITY_EXPANSION}
AND bias.side matches breakout direction (for TREND grade A+ requirement)
AND time_of_day ∈ {09:30–11:30 ET, 13:30–15:00 ET}
AND risk_state == OPEN
AND attempts_today["05_initiative_breakout"] < 2
AND projected_R_to_T1 >= 2.0
THEN emit signal {
    setup:  "05_initiative_breakout",
    side:   "LONG" | "SHORT",
    grade:  a_plus_grader(...),
    entry:  LVN_near_edge,
    stop:   pullback_wick + buffer[symbol] OR LVN_near_edge ± buffer (tighter),
    t1:     mid(LVN, far_HVN),
    t2:     far_HVN_near_edge,
    runner: far_HVN_VPOC,
    payload: standard schema
}
```

---

## 12. Failure Conditions

1. **No pullback** — straight-line breakouts without a controlled
   pullback often exhaust at the far HVN edge with no entry chance.
   Skip; do not chase.
2. **Pullback closes inside the LVN** — false breakout, the auction is
   not accepting beyond.
3. **Volume divergence** — breakout bar with range expansion but
   volume **below** 20-bar avg means the move is mechanical (algo
   sweep), not initiative. Skip.
4. **Regime mismatch** — if regime is `BALANCE`, the breakout almost
   always fails back into value. Use Setup 04 (LVN Rejection) instead.

---

## 13. Journal Fields

```
date, instrument, side, lvn_price, lvn_width_ticks,
coiling_bars_count, breakout_bar_body_pct, breakout_bar_range_x_avg,
breakout_bar_delta_x_avg, pullback_retracement_pct,
confirmation_flags[], grade, entry, stop, t1, t2,
exit_price, exit_reason, R_realized, mfe_R, mae_R, notes_link
```
