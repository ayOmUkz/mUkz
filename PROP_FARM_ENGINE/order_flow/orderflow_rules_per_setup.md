# Order Flow Rules — Per Setup

Per-setup confirmation requirements. The signal definitions are in
`order_flow_confirmation_engine.md`. This file specifies, **for each
setup**:

- Minimum confirmation required to enter.
- Strong confirmation required for A+ grade.
- Specific counter-signals that force `WARNING` (reject).
- The invalidation order-flow signal (used to exit early).

---

## Setup 01 — Liquidity Sweep Reversal

| Tier | Required (any of) |
|------|-------------------|
| `MIN_CONFIRM` | 1 of: `DELTA_DIVERGENCE`, `ABSORPTION`, `FOOTPRINT_FLIP`, `TAPE_EXHAUSTION` |
| `STRONG_CONFIRM` | 2+ of the above |
| `WARNING` (reject) | `TREND_DELTA` in the continuation direction OR `CONTINUATION_FOOTPRINT` (3:1 in breakout direction on the sweep bar) |
| **Invalidation OF** | `VOLUME_EXPANSION` in the original sweep direction within 2 × 5m bars post-reclaim — exit early |

---

## Setup 02 — Value Area Rejection

| Tier | Required (any of) |
|------|-------------------|
| `MIN_CONFIRM` | 1 of: `CVD_REVERSAL`, `ABSORPTION`, volume-spike-no-progress (volume ≥ 1.5× avg, range ≤ 0.7× avg) |
| `STRONG_CONFIRM` | 2+ of the above |
| `WARNING` (reject) | Trend delta through the VAH/VAL for ≥ 6 prior bars OR continuation footprint on the rejection bar |
| **Invalidation OF** | CVD makes new local extreme **through** the VA edge after entry — exit immediately |

---

## Setup 03 — 80% Value Area Rule

| Tier | Required (any of) |
|------|-------------------|
| `MIN_CONFIRM` | 1 of: `VOLUME_EXPANSION` into value, `FAILED_CONTINUATION` on the open-side of value, initiative delta in the rotation direction |
| `STRONG_CONFIRM` | 2+ of the above |
| `WARNING` (reject) | Repeated failed acceptance: ≥ 2 × 30m bars closing back outside value before the second acceptance bar fires |
| **Invalidation OF** | Strong delta + volume in the **original gap direction** after the acceptance bar — exit |

---

## Setup 04 — LVN Rejection / Auction Failure

| Tier | Required (any of) |
|------|-------------------|
| `MIN_CONFIRM` | 1 of: `CVD_REVERSAL`, `TRAPPED_AGGRESSION`, `ABSORPTION` inside the LVN, `TAPE_EXHAUSTION` |
| `STRONG_CONFIRM` | 2+ of the above |
| `WARNING` (reject) | Slow acceptance: ≥ 5 bars trading inside the LVN with no clear rejection bar OR continuation footprint inside LVN |
| **Invalidation OF** | A 5m bar closes with body_inside_lvn_pct > 0.70 after entry — exit |

---

## Setup 05 — Initiative Breakout Through LVN

| Tier | Required (any of) |
|------|-------------------|
| `MIN_CONFIRM` | 1 of: `VOLUME_EXPANSION` on breakout bar, CVD breakout (new 60-min high/low), tape acceleration (print rate ≥ 1.5× 60-min avg) |
| `STRONG_CONFIRM` | 2+ of the above |
| `WARNING` (reject) | Volume divergence: breakout bar range ≥ 1.5× avg but volume < avg → mechanical print, skip |
| **Invalidation OF** | Counter-imbalance (3:1) on pullback bars OR CVD reversal during pullback — exit |

---

## Cross-Setup Counter-Signals (universal)

These force `WARNING` for **any** setup:

| Counter-signal | Trigger |
|----------------|--------|
| **Macro CVD trend** | 1h CVD trending opposite to proposed trade for ≥ 12 bars |
| **News spike active** | Print rate > 3× 60-min avg AND no scheduled news → likely unscheduled headline; stand down 5 min |
| **Spread blowout** | Bid-ask spread > 2× 20-day median for the bar — data integrity warning |

---

## Confirmation Decay (time-based)

A `STRONG_CONFIRM` classification is valid **only on the bar it
fires** and the following 1 bar. If the trigger sequence (per setup
§ 3) does not produce an entry within that window, the confirmation
**expires** and must be re-evaluated on a new bar.

This prevents stale confirmation chases.

---

## Output Block (per signal evaluation)

```json
{
  "setup": "01_liquidity_sweep_reversal",
  "bar_close_time": "2026-05-13T13:35:00Z",
  "side": "SHORT",
  "of_classification": "STRONG_CONFIRM",
  "of_signals_fired": ["DELTA_DIVERGENCE", "ABSORPTION"],
  "counter_signals_fired": [],
  "warning": false,
  "expires_at_bar_close": "2026-05-13T13:40:00Z"
}
```

---

## Maintenance

Per-setup confirmation requirements are reviewed in the weekly
performance review. If a setup's win rate drops below 40% over a
rolling 30-trade window, the **first parameter** to retune is
`MIN_CONFIRM` (tighten to require 2 signals instead of 1).
