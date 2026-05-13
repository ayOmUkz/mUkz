# TradingView Indicator Logic (Pine v5)

The Pine indicator is **Phase 2** of the automation roadmap — it
detects setups visually and emits webhook alerts. **No order placement
from Pine.** The webhook payload is consumed by an external execution
engine.

This file is the indicator's specification. The Pine source lives in
a separate `pine/` directory at `v0.2` (not yet committed).

---

## 1. Inputs (Pine `input.*`)

| Group | Input | Type | Default |
|-------|-------|------|---------|
| Session | `session_rth` | session | `0930-1600` America/New_York |
| Session | `session_eth` | session | `1800-1700` America/New_York |
| Volume Profile | `vp_lookback_days` | int | 1 (prior day) |
| Volume Profile | `vp_rows` | int | 100 |
| Volume Profile | `vp_va_pct` | float | 0.70 (70% VA standard) |
| Bias | `show_bias_panel` | bool | true |
| Setups | `enable_setup_01` | bool | true |
| Setups | `enable_setup_02` | bool | true |
| Setups | `enable_setup_03` | bool | true |
| Setups | `enable_setup_04` | bool | true |
| Setups | `enable_setup_05` | bool | true |
| Order Flow | `delta_source` | source | `volume` (proxy) or external CVD feed |
| Order Flow | `avg_window_bars` | int | 20 |
| Order Flow | `min_lvn_width_ticks_es` | int | 3 |
| Order Flow | `min_lvn_width_ticks_nq` | int | 6 |
| Sweep buffer | `sweep_buffer_ticks_es` | int | 2 |
| Sweep buffer | `sweep_buffer_ticks_nq` | int | 4 |
| Alerts | `webhook_url` | string | "" |

---

## 2. Plots

### 2.1 Levels (always-on)

| Plot | Color | Style |
|------|-------|-------|
| PDH | red | dashed |
| PDL | red | dashed |
| ONH | orange | dotted |
| ONL | orange | dotted |
| IBH | yellow | solid (after 10:30 ET) |
| IBL | yellow | solid (after 10:30 ET) |
| Prior VAH | blue | solid |
| Prior VAL | blue | solid |
| Prior VPOC | purple | solid, bold |
| Weekly H | green | dashed |
| Weekly L | green | dashed |
| HVN edges | gray | solid (composite weekly) |
| LVN edges | gray | dashed |

### 2.2 Setup Markers

When a setup trigger fires on bar close:

| Setup | Marker | Position | Color |
|-------|--------|----------|-------|
| 01 long  | `▲` | below bar | green |
| 01 short | `▼` | above bar | red |
| 02 long  | `◆` | below bar | green |
| 02 short | `◆` | above bar | red |
| 03 long  | `■` | below bar | green |
| 03 short | `■` | above bar | red |
| 04 long  | `★` | below bar | green |
| 04 short | `★` | above bar | red |
| 05 long  | `▶` | below bar | lime |
| 05 short | `◀` | above bar | maroon |

Each marker uses `label.new()` with the setup's grade letter as text
(A+, A, B) so multiple setups on the same bar don't overlap.

### 2.3 Order Flow Markers

| Marker | Condition |
|--------|-----------|
| Green triangle below bar | OF tier `STRONG_CONFIRM` long |
| Red triangle above bar   | OF tier `STRONG_CONFIRM` short |
| Yellow dot (above or below) | OF tier `MIN_CONFIRM` |
| Gray ✕ on bar              | OF tier `WARNING` |

### 2.4 Bias Panel (top-right table)

| Row | Value source |
|-----|--------------|
| Classification | bias engine output |
| Confidence | bias engine output (0–100) |
| Regime | regime classifier output |
| Allowed Setups | comma-separated |
| Banned Setups | comma-separated |
| Size Multiplier | regime multiplier (× trailing-DD multiplier) |
| Daily P/L (R) | live tracking |
| Daily State | `OPEN` / `CAUTION` / `A_PLUS_ONLY` / `LOCKED` / `STOP_FOR_DAY` |

---

## 3. Pine Functions (sketch)

```pine
//@version=5
indicator("PROP FARM ENGINE — Setup Scanner", overlay=true, max_lines_count=500, max_labels_count=500)

// --- Volume profile (per-day from prior session)
[vah, val, vpoc] = f_prior_session_va(vp_va_pct, vp_rows)

// --- Sweep buffer in ticks → points
sweep_buf_pts = (syminfo.ticker == "ES1!" ? sweep_buffer_ticks_es : sweep_buffer_ticks_nq) * syminfo.mintick

// --- Setup 01 detector
is_sweep_high = high > level_to_sweep + sweep_buf_pts
is_reclaim    = close < level_to_sweep
of_tier       = f_order_flow_classify(...)

setup_01_fires = is_sweep_high[1] and is_reclaim and (of_tier == "MIN_CONFIRM" or of_tier == "STRONG_CONFIRM")

if setup_01_fires
    label.new(bar_index, high + 2*syminfo.mintick, "01 " + grade, color=color.red, textcolor=color.white, style=label.style_label_down)
    alert(f_payload_01("SHORT"), alert.freq_once_per_bar_close)
```

---

## 4. Alert Conditions (Pine `alertcondition` + `alert()` JSON)

Each setup emits an alert with a **webhook-ready JSON body**:

```json
{
  "setup": "01_liquidity_sweep_reversal",
  "instrument": "{{ticker}}",
  "side": "SHORT",
  "grade": "{{plot('grade')}}",
  "entry": {{plot('entry')}},
  "stop":  {{plot('stop')}},
  "t1":    {{plot('t1')}},
  "t2":    {{plot('t2')}},
  "swept_level": { "name": "PDH", "price": {{plot('level_price')}} },
  "confirmation": "{{plot('of_signals')}}",
  "regime": "{{plot('regime')}}",
  "bias_side": "{{plot('bias_side')}}",
  "bias_confidence": {{plot('bias_confidence')}},
  "timestamp_utc": "{{timenow}}"
}
```

TradingView replaces `{{plot(...)}}` and `{{ticker}}` / `{{timenow}}`
at alert-fire time. The webhook receiver validates this payload
against the canonical schema in each setup's § 12.

---

## 5. Alert Cadence

- All setup alerts: `alert.freq_once_per_bar_close`.
- The indicator never re-fires the same setup on an unchanged bar.
- Suppression: if the same setup+side fires within 5 minutes of the
  prior fire on the same level, the second alert is **suppressed**
  (avoid duplicate alerts on consecutive 5m bars sweeping the same
  PDH twice).

---

## 6. Webhook Receiver Contract

The receiver (external service) is responsible for:

1. Validating payload schema.
2. Running the pre-trade gate from `execution_safety_rules.md`.
3. Computing position size (Pine doesn't know account state).
4. Submitting bracket orders to the broker (Phases 3+ only).
5. Logging rejections to `journal/` store.

Pine **never** submits orders.

---

## 7. Performance Budget (Pine constraints)

| Metric | Target |
|--------|--------|
| `max_lines_count` | 500 (level lines per chart) |
| `max_labels_count` | 500 (markers) |
| Lookback bars | 5000 (Pine default) |
| Re-evaluation on history | none — `barstate.isconfirmed` gates |
| Per-bar runtime | < 50 ms (Pine soft cap to avoid CPU warning) |

If the per-bar runtime exceeds budget, split into two indicators (one
for levels + bias panel, one for setup detection).

---

## 8. Testing Protocol

1. **Replay test** — run the indicator on 30 historical RTH sessions
   for ES and NQ. Count setup fires per setup per day. Expectation:
   1–3 Setup-01 fires per session, 0–2 of Setups 02/04, 0–1 of Setup
   03, 0–2 of Setup 05.
2. **False-positive audit** — manually review 30 fires per setup;
   true-positive rate must be ≥ 70%.
3. **Alert latency** — webhook arrival should be < 5s after bar close.

If true-positive rate < 70%, tighten the trigger parameters before
graduating Phase 2 → Phase 3.

---

## 9. Visualization Best Practices

- All-time levels (PDH/PDL/ONH/ONL) are drawn **only on the current
  RTH session**. Historical levels are removed each session open.
- VA edges are drawn as **horizontal rays** ending at session close.
- Markers are placed with `style=label.style_label_down` (for shorts)
  or `label.style_label_up` (for longs) to avoid bar overlap.
- The bias panel uses `table.new()` in `position.top_right`.
- Color scheme respects dark/light theme via `color.from_gradient`.

---

## 10. Maintenance

The Pine source is versioned independently from this spec. Changes:

1. Update this spec first.
2. Update Pine source.
3. Replay-test on 30 sessions.
4. Document fire-count changes in `journal/weekly_performance_review.md`.
5. Promote to Phase 2 production.
