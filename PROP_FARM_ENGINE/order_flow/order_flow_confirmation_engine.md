# Order Flow Confirmation Engine

The universal confirmation framework. Every setup in `/playbook`
references this file for the **classification** of its order flow
signal. The engine consumes order flow data (delta, CVD, footprint,
tape) and outputs a single tier per bar.

---

## 1. Inputs

| Input | Definition | Required source |
|-------|-----------|-----------------|
| **Delta** | Buy market volume minus sell market volume (per bar) | Footprint feed (e.g., Bookmap, Sierra Chart, Rithmic) |
| **CVD (Cumulative Volume Delta)** | Running sum of delta | Same feed |
| **Bid/Ask imbalance** | Ratio of buying vs selling at each price | Footprint |
| **Volume** | Total contracts traded per bar | OHLCV |
| **Bar range** | High − Low per bar | OHLCV |
| **Tape print rate** | Trades per second (rolling 60s) | Time & sales |
| **20-bar averages** | Of volume, range, delta | Computed |

Without footprint/CVD data, the engine cannot evaluate confirmation
and outputs `UNKNOWN` (treated as `NO_TRADE` by setups).

---

## 2. Output Tiers

| Tier | Meaning |
|------|---------|
| `NO_CONFIRM` | Zero signals fired. Setup is skipped. |
| `WARNING` | Counter-signal detected (e.g., delta agrees with continuation, not reversal). Setup is rejected even if other conditions pass. |
| `MIN_CONFIRM` | Exactly one signal fired. Setup eligible for A or B grade. |
| `STRONG_CONFIRM` | Two or more signals fired. Setup eligible for A+ grade. |
| `UNKNOWN` | Order flow data missing or stale. Treated as `NO_CONFIRM`. |

---

## 3. Signal Catalog

### 3.1 Delta Divergence

```
IF current bar prints a new local price extreme
AND CVD on the same bar does NOT confirm the extreme
   (CVD makes lower-high on price higher-high, or vice versa)
THEN signal = DELTA_DIVERGENCE
```

### 3.2 CVD Reversal

```
IF the rolling 10-bar CVD slope flips sign within the current bar
AND price reverses direction with body_pct >= 0.50
THEN signal = CVD_REVERSAL
```

### 3.3 Absorption

```
IF bar volume >= 2 * avg_volume_20
AND bar range <= 0.5 * avg_range_20
AND (bar makes a new local extreme OR sits at a known level)
THEN signal = ABSORPTION
```

### 3.4 Aggressive Buying/Selling Trapped

```
IF previous bar shows delta > 1.5 * avg_delta_20 (in direction X)
AND current bar reverses direction
AND current bar delta > 1.5 * avg_delta_20 (in direction -X)
THEN signal = TRAPPED_AGGRESSION
```

### 3.5 Footprint Imbalance Flip

```
IF the current bar contains a >= 3:1 imbalance ratio
   on the OPPOSITE side of the prior bar's directional aggression
AND the imbalance occurs at or beyond a known level (PDH/PDL/VAH/VAL/...)
THEN signal = FOOTPRINT_FLIP
```

### 3.6 Tape Exhaustion

```
IF print_rate (rolling 60s) >= 1.5 * avg_print_rate_60min
   immediately before a new local extreme
AND within 60s of the extreme, print_rate drops > 40%
THEN signal = TAPE_EXHAUSTION
```

### 3.7 Failed Continuation

```
IF price breaks a known level (PDH, PDL, VAH, VAL, LVN edge, ...)
AND within next 3 bars (same TF), price closes back through the level
AND delta during the breakout phase was NOT confirming
   (delta < 0.8 * avg_delta_20 in breakout direction)
THEN signal = FAILED_CONTINUATION
```

### 3.8 Volume Expansion (used by continuation setups)

```
IF bar volume >= 1.5 * avg_volume_20
AND bar range >= 1.5 * avg_range_20
AND bar body_pct >= 0.6
AND bar delta agrees with bar direction (>= 1.5 * avg_delta_20)
THEN signal = VOLUME_EXPANSION
```

---

## 4. Counter-Signals (cause `WARNING`)

If any of these fire **against** the proposed trade direction, the
classification is forced to `WARNING` regardless of confirming signals:

| Counter-signal | Definition |
|----------------|-----------|
| **Trend delta** | CVD trending strongly in the **opposite** direction to the trade for ≥ 6 bars |
| **Continuation footprint** | ≥ 3:1 imbalance **in the direction the trade is fading** on the trigger bar |
| **Acceptance outside** | For reversal setups: 2 consecutive bars closing beyond the swept level after the reclaim |

`WARNING` overrides `MIN_CONFIRM` and `STRONG_CONFIRM`. A trade gated
`WARNING` is **rejected**.

---

## 5. Classification Algorithm

```
function classify_order_flow(bar, history, level, side):
    if data_missing(bar): return "UNKNOWN"

    # 1. Check counter-signals first
    if any_counter_signal_fires(bar, history, side): return "WARNING"

    # 2. Count confirming signals
    confirming = []
    if delta_divergence(bar, history, side):        confirming += ["DELTA_DIVERGENCE"]
    if cvd_reversal(bar, history, side):            confirming += ["CVD_REVERSAL"]
    if absorption(bar, history):                    confirming += ["ABSORPTION"]
    if trapped_aggression(bar, history, side):      confirming += ["TRAPPED_AGGRESSION"]
    if footprint_flip(bar, history, side, level):   confirming += ["FOOTPRINT_FLIP"]
    if tape_exhaustion(bar, history, side):         confirming += ["TAPE_EXHAUSTION"]
    if failed_continuation(bar, history, side, level): confirming += ["FAILED_CONTINUATION"]
    if volume_expansion(bar, history, side):        confirming += ["VOLUME_EXPANSION"]

    if len(confirming) >= 2: return ("STRONG_CONFIRM", confirming)
    if len(confirming) == 1: return ("MIN_CONFIRM", confirming)
    return ("NO_CONFIRM", [])
```

---

## 6. Per-Setup Mapping

The full table is in `orderflow_rules_per_setup.md`. Summary:

| Setup | Required signals (any of) | Counter-signal |
|-------|--------------------------|---------------|
| 01 Liquidity Sweep | Delta divergence, Absorption, Footprint flip, Tape exhaustion | Continuation footprint |
| 02 Value Area Rejection | CVD reversal, Absorption, Volume spike (no progress) | Trend delta through edge |
| 03 80% VA Rule | Volume expansion (into value), Failed continuation (open-side) | Failed acceptance |
| 04 LVN Rejection | Delta reversal, Trapped aggression, Absorption inside LVN, Tape exhaustion | Slow acceptance |
| 05 Initiative Breakout | Volume expansion, CVD breakout, Tape acceleration | Volume divergence |

---

## 7. IF / AND / THEN — Worked Example (Setup 01 short)

```
IF price prints new high (sweep extreme)
AND CVD on the sweep bar fails to make a new high (DELTA_DIVERGENCE)
AND the sweep bar has volume >= 2× avg AND range <= 0.5× avg (ABSORPTION)
AND there is NO 3:1 buy imbalance on the sweep bar (no counter-signal)
THEN classify_order_flow(sweep_bar) = STRONG_CONFIRM (2 signals)
THEN setup_01 eligibility = A+ candidate (pending other A+ criteria)
```

This block runs **on every closed bar** of the relevant timeframe.

---

## 8. Data Freshness Requirements

| Data | Max staleness |
|------|---------------|
| Footprint feed | 2 seconds |
| CVD calculation | 2 seconds |
| Tape print | 2 seconds |
| OHLCV bar close | 5 seconds after bar close |

If any data source is stale beyond its threshold, classification
returns `UNKNOWN`.

---

## 9. Visualization (TradingView Indicator)

The Pine indicator (see `automation/tradingview_indicator_logic.md`)
plots:

- A **green triangle** below a bar when `STRONG_CONFIRM` for a long
  setup.
- A **red triangle** above a bar when `STRONG_CONFIRM` for a short
  setup.
- A **yellow dot** when `MIN_CONFIRM` only.
- A **gray X** when `WARNING`.

Markers are setup-tagged via Pine's `label.new()` so multiple setups
can light up simultaneously without overlap.

---

## 10. Maintenance

Signal thresholds (the 1.5×, 2×, 3:1 ratios) are reviewed quarterly
from journal data. A signal whose fire rate is > 30% of bars (too
loose) or < 2% (too tight) is recalibrated. No mid-quarter changes.
