# Signal Detection Logic

The algorithmic implementation of each setup's trigger sequence. Each
function below has a defined input, return type, and edge cases. This
file is the bridge between the playbook (human-readable rules) and the
execution engine (code).

All functions evaluate on **closed bars only**. Mid-bar evaluation is
forbidden — it produces phantom signals.

---

## 1. Shared Data Structures

```pseudo
Bar {
    timestamp_utc:   datetime
    open, high, low, close: float
    volume:          int
    delta:           int          // optional, from footprint feed
    cvd_close:       int          // cumulative volume delta at bar close
    bid_ask_imb:     dict[price -> int]   // optional, from footprint
    print_rate_60s:  float        // prints per second
    timeframe:       "1m" | "5m" | "15m" | "30m" | "1h"
}

Level {
    name:    "PDH" | "PDL" | "ONH" | "ONL" | "IBH" | "IBL"
             | "VAH" | "VAL" | "VPOC" | "WEEKLY_H" | "WEEKLY_L"
             | "HVN_edge" | "LVN_edge" | "PRIOR_SWING_HI" | "PRIOR_SWING_LO"
    price:   float
    age_bars: int    // age on the most recent bar at evaluation time
}

OrderFlowResult {
    tier:    "STRONG_CONFIRM" | "MIN_CONFIRM" | "NO_CONFIRM" | "WARNING" | "UNKNOWN"
    signals: list[str]
    warning_signals: list[str]
}
```

---

## 2. Level Detection

### 2.1 `compute_session_levels(date)`

Returns a list of `Level` for the session:

```
PDH, PDL, VAH, VAL, VPOC : from prior RTH (09:30–16:00 ET)
ONH, ONL                  : from ETH (18:00 prior → 09:30 ET today)
IBH, IBL                  : from first 60 min RTH (09:30–10:30 ET)
WEEKLY_H, WEEKLY_L        : from current week's RTH so far
PRIOR_SWING_HI/LO         : pivot-based, > 5 bars age on 5m
HVN/LVN edges             : volume profile of prior session
```

### 2.2 `is_liquidity_level(price, levels, tolerance_ticks)`

Returns true if `price` is within `tolerance_ticks` of any level in
the list. Used to gate sweep detection.

---

## 3. Setup 01 — Liquidity Sweep Reversal

### 3.1 `is_liquidity_sweep(bar, level, instrument)`

```
sweep_buffer_ticks = { ES: 2, NQ: 4 }[instrument]

if level.side == "HIGH":
    return bar.high > level.price + (sweep_buffer_ticks × tick_size)
else:
    return bar.low  < level.price - (sweep_buffer_ticks × tick_size)
```

### 3.2 `is_reclaim_within_window(bars, level, side, max_bars=3)`

```
for b in bars[-max_bars:]:
    if side == "SHORT" and b.close < level.price: return true
    if side == "LONG"  and b.close > level.price: return true
return false
```

### 3.3 `has_structural_break_1m(bars_1m, side)`

```
if side == "SHORT":
    # Find first 1m bar with a lower high than the prior 1m bar
    for i in range(1, len(bars_1m)):
        if bars_1m[i].high < bars_1m[i-1].high: return true
else:
    # Mirror for higher low
    for i in range(1, len(bars_1m)):
        if bars_1m[i].low > bars_1m[i-1].low: return true
return false
```

### 3.4 `setup_01_trigger(bars_5m, bars_1m, levels, instrument)`

```
for level in levels filtered by ELIGIBLE_FOR_SETUP_01:
    latest = bars_5m[-1]
    if is_liquidity_sweep(latest, level, instrument):
        # Look forward up to 3 × 5m bars (but we evaluate on bar close,
        # so iterate as future bars close)
        if is_reclaim_within_window(future_bars_5m[:3], level, side):
            of = classify_order_flow(reclaim_bar, history, level, side)
            if of.tier in [MIN_CONFIRM, STRONG_CONFIRM]:
                if has_structural_break_1m(bars_1m_post_reclaim, side):
                    return Signal(
                        setup="01",
                        side=side,
                        entry=level.price,
                        stop=sweep_extreme ± buffer,
                        ...
                    )
return None
```

---

## 4. Setup 02 — Value Area Rejection

### 4.1 `is_va_approach(bar, level, tolerance_ticks=2)`

```
return abs(bar.high - level.price) <= tolerance_ticks × tick_size  (for VAH)
    OR abs(bar.low  - level.price) <= tolerance_ticks × tick_size  (for VAL)
```

### 4.2 `is_va_rejection_bar(bar, level, side)`

```
range = bar.high - bar.low
body_pct = abs(bar.close - bar.open) / range
wick_beyond_level = ...   # the wick excursion past `level.price`
wick_pct = wick_beyond_level / range

if side == "SHORT":
    return bar.close < level.price
       AND body_pct >= 0.50
       AND wick_pct >= 0.30
       AND bar.close < bar.open    # bearish bar
# mirror for LONG
```

### 4.3 `setup_02_trigger(bars_5m, prior_session_levels)`

```
VAH = prior_session_levels.VAH
VAL = prior_session_levels.VAL

# First test of session
if has_been_tested_today(VAH): return None
latest = bars_5m[-1]
if is_va_approach(latest, VAH, tolerance_ticks=2)
   AND is_va_rejection_bar(latest, VAH, side="SHORT")
   AND not_accepted_outside_value(history):
    of = classify_order_flow(latest, history, VAH, "SHORT")
    if of.tier >= MIN_CONFIRM:
        return Signal(setup="02", side="SHORT", entry=VAH, ...)
# mirror for VAL → LONG
```

---

## 5. Setup 03 — 80% Value Area Rule

### 5.1 `is_open_outside_value(rth_open_price, prior_VAH, prior_VAL)`

```
if rth_open_price > prior_VAH: return ("ABOVE", rth_open_price - prior_VAH)
if rth_open_price < prior_VAL: return ("BELOW", prior_VAL - rth_open_price)
return ("INSIDE", 0)
```

### 5.2 `is_value_reentry_within(bars, prior_VAH, prior_VAL, minutes=60)`

```
cutoff = rth_open + minutes
for b in bars where b.timestamp <= cutoff:
    if prior_VAL <= b.high AND prior_VAL <= b.low <= prior_VAH:
        return true     # price has re-entered the VA range
return false
```

### 5.3 `is_acceptance_bar_30m(bar, prior_VAH, prior_VAL)`

```
return prior_VAL <= bar.close <= prior_VAH    # 30m close inside value
```

### 5.4 `is_holding_bar(prev_acceptance_bar, current_bar, prior_VAH, prior_VAL)`

```
range = current_bar.high - current_bar.low
prev_near_edge = ... (the edge of VA the auction came from)
overshoot = max(0, (current_bar.high - prev_near_edge if open_above else prev_near_edge - current_bar.low))
return prior_VAL <= current_bar.close <= prior_VAH
   AND overshoot <= 0.25 × range
```

### 5.5 `setup_03_trigger(bars_30m, rth_open, prior_VAH, prior_VAL)`

```
direction, gap = is_open_outside_value(rth_open, prior_VAH, prior_VAL)
if direction == "INSIDE": return None

if is_value_reentry_within(intraday_bars, prior_VAH, prior_VAL, 60):
    acceptance_idx = first 30m bar that closed inside VA
    holding_idx    = acceptance_idx + 1
    if is_acceptance_bar_30m(bars_30m[acceptance_idx], prior_VAH, prior_VAL)
       AND is_holding_bar(bars_30m[acceptance_idx], bars_30m[holding_idx], prior_VAH, prior_VAL):
        of = classify_order_flow(bars_30m[holding_idx], history, ..., side)
        if of.tier >= MIN_CONFIRM:
            return Signal(setup="03", side=("SHORT" if direction=="ABOVE" else "LONG"), ...)
return None
```

---

## 6. Setup 04 — LVN Rejection

### 6.1 `identify_lvns(volume_profile, vpoc_vol_per_price)`

```
return [
    LVN(price_low, price_high)
    for node in volume_profile
    if node.volume_per_price <= 0.40 × vpoc_vol_per_price
       AND node.width_ticks >= min_lvn_width[symbol]
       AND has_adjacent_strong_side_hvn(node)
]
```

### 6.2 `is_lvn_attack(bars_1m, lvn)`

```
bars_inside = count(b for b in bars_1m if lvn.low <= b.high AND b.low <= lvn.high)
return bars_inside >= 2
```

### 6.3 `is_failure_to_accept(bars_5m, lvn, max_bars=3)`

```
for b in bars_5m[-max_bars:]:
    body_inside_pct = body_overlap_with(b, lvn) / abs(b.close - b.open)
    if b.close inside lvn AND body_inside_pct > 0.70:
        return false   # acceptance achieved, setup invalidated
return true            # no acceptance within window
```

### 6.4 `is_rejection_bar_5m(bar, strong_side_hvn_edge, side)`

```
range = bar.high - bar.low
body_pct = abs(bar.close - bar.open) / range
if side == "SHORT" (attack was upward, rejection is downward):
    return bar.close <= strong_side_hvn_edge
       AND body_pct >= 0.50
       AND bar.close < bar.open
# mirror for LONG
```

### 6.5 `setup_04_trigger(bars_5m, bars_1m, lvns, hvns)`

```
for lvn in lvns:
    if is_lvn_attack(bars_1m, lvn)
       AND is_failure_to_accept(bars_5m, lvn, max_bars=3)
       AND is_rejection_bar_5m(bars_5m[-1], strong_side_hvn_edge_of(lvn), side):
        of = classify_order_flow(bars_5m[-1], history, lvn, side)
        if of.tier >= MIN_CONFIRM:
            return Signal(setup="04", side, entry=strong_side_hvn_edge, ...)
return None
```

---

## 7. Setup 05 — Initiative Breakout

### 7.1 `is_coiling_near_lvn(bars_5m, lvn, lookback=6)`

```
atr5 = atr(bars_5m, 20)
near_edge = lvn.entry_side_edge
return count(b for b in bars_5m[-lookback:]
             if abs(b.close - near_edge) < atr5) >= lookback
```

### 7.2 `is_breakout_bar(bar, lvn, avg_range_20, avg_delta_20, side)`

```
range = bar.high - bar.low
body_pct = abs(bar.close - bar.open) / range
if side == "LONG":
    breaks = bar.close > lvn.high
    delta_ok = bar.delta >= 1.5 * avg_delta_20
else:
    breaks = bar.close < lvn.low
    delta_ok = bar.delta <= -1.5 * avg_delta_20
return breaks AND body_pct >= 0.60 AND range >= 1.5 * avg_range_20 AND delta_ok
```

### 7.3 `is_pullback_hold(breakout_bar, pullback_bars, lvn, side)`

```
retracement = ...
if retracement > 0.50: return false
for b in pullback_bars:
    if side == "LONG"  and b.close < lvn.high: return false
    if side == "SHORT" and b.close > lvn.low:  return false
return true
```

### 7.4 `is_acceptance_beyond_far_edge(bar, lvn, side)`

```
if side == "LONG":  return bar.close > lvn.high     # already beyond, want continuation past far edge in pullback context
if side == "SHORT": return bar.close < lvn.low
```

### 7.5 `setup_05_trigger(bars_5m, lvns)`

```
for lvn in lvns_eligible_for_setup_05:
    if is_coiling_near_lvn(bars_5m, lvn, lookback=6)
       AND is_breakout_bar(bars_5m[-1 or -k], lvn, avg_range_20, avg_delta_20, side):
        # wait for pullback + acceptance bar to print
        if is_pullback_hold(breakout_bar, pullback_bars, lvn, side)
           AND is_acceptance_beyond_far_edge(latest_bar, lvn, side):
            of = classify_order_flow(latest_bar, history, lvn, side)
            if of.tier >= MIN_CONFIRM:
                return Signal(setup="05", side, entry=lvn.near_edge, ...)
return None
```

---

## 8. Main Detection Loop (pseudocode)

```
function on_bar_close(bar, instrument):
    if bar.timeframe == "5m":
        levels = compute_session_levels(today)
        lvns   = identify_lvns(volume_profile_yday, vpoc_vol_per_price)
        for setup_fn in [setup_01_trigger, setup_02_trigger, setup_04_trigger, setup_05_trigger]:
            signal = setup_fn(bars_5m, bars_1m, levels, lvns, instrument)
            if signal is not None:
                signal.grade = grade_signal(signal, regime, bias, of_signals)
                signal.size_contracts = compute_size(signal, account_state)
                if pre_trade_gate(signal, account_state):
                    emit(signal)
                else:
                    log_rejection(signal, reason_code)

    if bar.timeframe == "30m":
        signal = setup_03_trigger(bars_30m, rth_open, prior_VAH, prior_VAL)
        if signal is not None:
            ...same flow...
```

---

## 9. Edge Cases (binding)

- **Bar gaps** (e.g., 5m bar formed when no trades occurred): treat as
  `UNKNOWN` data; do not evaluate triggers.
- **Mid-bar level breach** that closes back inside: no signal — we
  only fire on closed bars.
- **Multiple setups firing on same bar**: emit each independently;
  the engine deduplicates correlated entries (e.g., Setup 01 short at
  PDH and Setup 02 short at VAH may be the same trade).
- **Time-of-day boundary**: a setup that completes inside its window
  but fires after a window switch is **not** valid; window is checked
  at signal emission.

---

## 10. Performance Targets

| Metric | Target |
|--------|--------|
| Detection latency (bar close → signal emit) | < 500 ms |
| Order flow classification per bar | < 100 ms |
| Memory: per-symbol history | last 200 × 5m bars + 600 × 1m bars |
| Persistence: signals + rejections | written async to journal store |
