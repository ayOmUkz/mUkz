# Setup 01 — Liquidity Sweep Reversal

**Instruments:** ES, NQ (RTH primary; ETH only if Asia/London range
liquidity is well-defined)
**Execution timeframes:** 1m / 5m
**Context timeframes:** 15m / 1h
**Setup class:** Reversal / Failed Auction
**Regime validity:** `BALANCE`, `VOLATILITY_EXPANSION`
**Banned in:** `TREND` (clean), `NEWS_RISK`, `LOW_VOL_CHOP`

---

## 1. Context

The market runs a known liquidity pool — Prior Day High/Low (PDH/PDL),
Overnight High/Low (ONH/ONL), Initial Balance High/Low (IBH/IBL), or a
clear unfilled swing — triggering resting stops on the breakout side.
Initiative fails to materialize, the breakout traders are trapped, and
responsive flow reverses price back through the swept level.

The thesis is **auction rejection at a liquidity pool**: a probe that
fails to find acceptance is a directional signal in the opposite
direction. The setup is taken on the reclaim or first retest of the
swept level, confirmed by order flow.

---

## 2. Location (where the setup is valid)

The sweep must occur at one of:

- **PDH** or **PDL** (Prior Day High/Low)
- **ONH** or **ONL** (Overnight High/Low)
- **IBH** or **IBL** (Initial Balance High/Low — first 60 minutes RTH)
- **Prior-week High** or **Low**
- An **unmitigated swing high/low** > 5 bars old on 5m
- Edge of a recognized **HVN** acting as composite support/resistance

**Levels that do NOT qualify:**

- Intraday minor swings < 5 bars old.
- Levels already swept earlier the same session.
- Levels created during a news-event spike.

---

## 3. Trigger (sequential — all required, in order)

| # | Step | Rule |
|---|------|------|
| 1 | **Sweep** | Latest closed 5m bar's extreme exceeds the level by ≥ **2 ticks (ES)** or ≥ **4 ticks (NQ)** |
| 2 | **Reclaim** | Within ≤ **3 × 5m bars** (15 min), price closes back through the swept level in the opposite direction |
| 3 | **Order flow confirmation** | At least one signal from § 4 |
| 4 | **Structural break (1m)** | First 1m lower-high (short) / higher-low (long) after the reclaim |

All four steps must happen in order. If step 2 takes longer than 3 × 5m
bars, the trigger is **dead** — wait for a new sweep.

---

## 4. Confirmation (Order Flow)

Defined in `order_flow/order_flow_confirmation_engine.md`. At least one
required to qualify; two = STRONG_CONFIRM = eligible for A+.

| Signal | Definition |
|--------|-----------|
| **Delta divergence** | Sweep bar prints new price extreme but CVD does not (lower-high CVD on price higher-high, or vice versa) |
| **Absorption** | Sweep extreme bar volume ≥ **2× 20-bar avg** AND range ≤ **50% of 20-bar avg range** |
| **Footprint imbalance flip** | ≥ **3:1** sell-side imbalance on new-high bar (or 3:1 buy-side on new-low bar) |
| **Tape exhaustion** | Print rate drops > **40%** within 60s after the extreme |

**Classification:**

- 0 signals → `NO_TRADE`
- 1 signal  → `MIN_CONFIRM` (eligible for A or B grade)
- 2+ signals → `STRONG_CONFIRM` (eligible for A+)

---

## 5. Entry

- **Primary:** Limit entry on first retest of the reclaimed level.
  Tolerance: 1 tick (ES) / 2 ticks (NQ).
- **Backup:** Market entry on the close of the 1m structural-break bar
  if no retest occurs within 5 × 1m bars.
- **Skip:** If price exceeds the original sweep extreme again before
  entry fills → cancel and stand down.

---

## 6. Stop

- **Hard stop:** 2 ticks beyond the sweep extreme (ES) / 4 ticks beyond
  (NQ).
- **Time stop:** If trade has not reached +1R within 15 minutes → exit
  at market.

Stops are **bracket-attached**: the entry, stop, and T1 limit are
submitted atomically. No naked positions.

---

## 7. Target

| Leg | Target | Action |
|-----|--------|--------|
| **T1** | +1R (typically nearest HVN or prior balance edge) | Scale **50%**, move stop to entry |
| **T2** | Prior session VPOC or opposite VA edge | Scale **30%**, trail stop to last 5m swing |
| **Runner** | Opposite extreme of prior day's range | Trail with 5m swing structure |

**R:R floor:** projected R:R to T1 must be ≥ **2.0R**. If T1 < 2R from
entry distance, **skip the trade**.

---

## 8. Invalidation

The setup is invalidated (cancel order or exit at market) if **any**:

- Price prints a new high/low beyond the original sweep after entry.
- Reclaim fails to hold: price closes back through the swept level in
  the original sweep direction on **2 consecutive 5m bars**.
- 1h regime flips to `TREND` **against** the trade direction.
- Daily loss circuit breaker fires
  (`risk/daily_loss_protection.md`).
- HIGH-impact news event flagged within ±2 minutes of entry.

---

## 9. Risk Rule

| Mode | Per-trade risk | Max attempts/day | Position size formula |
|------|---------------:|-----------------:|-----------------------|
| Evaluation | 0.5% | 2 | `floor( (equity × 0.005) / (stop_ticks × tick_value) )` |
| Funded     | 0.75% | 2 | `floor( (equity × 0.0075) / (stop_ticks × tick_value) )` |
| Scaling    | 1.0% | 2 | `floor( (equity × 0.010) / (stop_ticks × tick_value) )` |

- **Tick values:** ES = $12.50, NQ = $5.00.
- **Correlated exposure cap:** 1× ES + 1× NQ same direction same
  setup within 5 min → reduce the second leg by 40% (counts as 0.6×).
  Skip the second leg entirely if 30-day corr > 0.9.
- **Max attempts/day for this setup:** 2 (independent of grade).

See `risk/prop_firm_risk_rules.md` and `risk/risk_modes.md`.

---

## 10. A+ Grade Criteria (5-point check)

| Pt | Criterion |
|----|-----------|
| ☐ | Liquidity level is **multi-session confluence** (e.g., PDH + ONH, PDL + weekly low) |
| ☐ | Sweep occurs into an opposing **HVN** or **prior VPOC** |
| ☐ | Order flow = **STRONG_CONFIRM** (≥ 2 signals) |
| ☐ | Daily bias side matches reversal direction AND `bias_confidence ≥ 50` |
| ☐ | Setup fires in the **09:30–10:30 ET** prime window |

Grade map: 5/5 = A+, 4/5 = A, 3/5 = B (half size), ≤ 2 → skip.

---

## 11. Automation Rule (IF / AND / THEN)

```
IF a defined liquidity_level ∈ {PDH, PDL, ONH, ONL, IBH, IBL,
                                weekly_H, weekly_L,
                                prior_swing[age_bars_5m > 5]}
AND the latest closed 5m bar's high > level + sweep_buffer[symbol]
    (for short setup; mirror logic for long)
AND within next ≤ 3 × 5m bars, a 5m bar closes < level (reclaim)
AND order_flow_confirmation(latest_bar) ∈ {MIN_CONFIRM, STRONG_CONFIRM}
AND a 1m lower_high prints after the reclaim
AND regime ∈ {BALANCE, VOLATILITY_EXPANSION}
AND time_of_day ∈ {09:30–11:30 ET, 13:30–15:30 ET}
AND risk_state == OPEN
AND no HIGH-impact news within ±2 min
AND attempts_today["01_liquidity_sweep_reversal"] < 2
AND projected_R_to_T1 >= 2.0
THEN emit signal {
    setup:        "01_liquidity_sweep_reversal",
    side:         "SHORT" | "LONG",
    grade:        a_plus_grader(...),       // A+, A, B
    entry:        reclaimed_level,
    stop:         sweep_extreme + buffer[symbol],
    t1, t2, runner: per § 7,
    payload:      see § 12
}
```

### `sweep_buffer[symbol]` constants

| Symbol | Buffer |
|--------|--------|
| ES | 2 ticks (0.50 pt) |
| NQ | 4 ticks (1.00 pt) |

---

## 12. Alert / Signal Payload (consumed by execution engine)

```json
{
  "setup": "01_liquidity_sweep_reversal",
  "instrument": "ES",
  "side": "SHORT",
  "grade": "A+",
  "entry": 5212.50,
  "stop": 5215.75,
  "t1": 5208.75,
  "t2": 5203.50,
  "runner_target": 5198.25,
  "swept_level": { "name": "PDH", "price": 5214.00 },
  "confirmation": ["delta_divergence", "absorption"],
  "regime": "BALANCE",
  "bias": { "side": "SHORT", "confidence": 64 },
  "risk": {
    "mode": "FUNDED",
    "size_contracts": 2,
    "risk_$": 162.50,
    "risk_pct": 0.75
  },
  "timestamp_utc": "2026-05-13T13:42:00Z"
}
```

The execution engine validates this payload against
`automation/execution_safety_rules.md` before submitting any order.

---

## 13. Known Failure Modes (do not trade)

1. **News-driven sweeps** — sweep occurred during a HIGH-impact data
   release. Continuation is more likely. Blocked by news window.
2. **Trend-day sweeps** — in `TREND` regime, sweeps tend to continue.
   Filtered by regime gate.
3. **Thin overnight pools** — sweeps of low-volume ETH levels fail to
   reverse cleanly. Require ≥ 2 prior touches with rejection at the
   level as a proxy for resting size.
4. **Late-day sweeps (≥ 15:30 ET)** — closing imbalance distorts order
   flow. Filtered by time-of-day window.
5. **Re-sweep of an already-swept level** — second sweep of the same
   level same session is usually accepted (continuation). Skip.
6. **Sweep > 3× ATR(20) on 5m** — abnormal-magnitude sweeps are
   typically news-driven, not auction events. Skip.

---

## 14. Journal Fields (auto-logged per trade)

```
date, instrument, side, swept_level_name, swept_level_price,
sweep_excursion_ticks, reclaim_bars_to_close, confirmation_flags[],
grade, entry, stop, t1, t2, exit_price, exit_reason,
R_realized, mfe_R, mae_R, regime, bias_side, bias_confidence,
time_of_day, notes_link
```

See `journal/setup_review_template.md` for the per-trade review form.

---

## 15. Maintenance & Review

This setup's parameters (sweep buffer, reclaim window, R:R floor) are
reviewed weekly in `journal/weekly_performance_review.md`. Parameter
changes require ≥ 30 trades of statistical evidence and a documented
review. **No mid-week parameter changes.**
