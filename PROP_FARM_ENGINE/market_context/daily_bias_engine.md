# Daily Bias Engine

The bias engine produces a **directional read** before the session
begins. The output is a single classification plus a 0–100 confidence
score. Setups consume this output as one of the A+ grading criteria.

The bias is not a trade signal. It tells us **which side to favor** and
**which setups are valid today**.

---

## 1. Inputs (computed before 09:25 ET)

| # | Input | Source | Timeframe |
|---|-------|--------|-----------|
| 1 | Weekly structure | 1D bars | Last 4 weeks |
| 2 | Daily structure | 1D bars | Last 20 sessions |
| 3 | Overnight high/low (ONH/ONL) | 1m ETH | 18:00 ET prior → 09:30 ET today |
| 4 | Prior day high/low (PDH/PDL) | 1m RTH | Prior RTH session |
| 5 | Prior day value area (VAH/VAL/VPOC) | TPO or volume profile | Prior RTH |
| 6 | Globex range | 1m ETH | Overnight |
| 7 | Opening range (computed live 09:30–09:45) | 1m RTH | First 15 min RTH |
| 8 | Liquidity pools | Aggregate | Past 5 sessions |
| 9 | Major swing highs/lows | 1h | Past 10 sessions |
| 10 | Poor highs/lows | 1h | Past 10 sessions (TPO definition: ≤ 1 single TPO at the extreme) |
| 11 | Single prints | TPO | Prior session |
| 12 | HVNs and LVNs | Volume profile | Prior session + composite weekly |
| 13 | Prior session trapped inventory | Last-hour CVD vs price | Prior RTH last 60 min |
| 14 | 200-period 1h trend slope | Linear regression | Last 200 1h bars |
| 15 | VIX context | Daily | Latest close vs 20-day MA |

---

## 2. Output Classifications

| Output | Meaning |
|--------|---------|
| `LONG_BIAS` | Favor long setups; short setups require A+ + counter-trend confluence |
| `SHORT_BIAS` | Favor short setups; long setups require A+ + counter-trend confluence |
| `BALANCED` | No directional edge; responsive (mean-reversion) setups favored |
| `RANGE_EXPANSION_LIKELY` | Volatility expansion expected; favor Setup 05 + Setup 01 |
| `MEAN_REVERSION_LIKELY` | Compression expected; favor Setups 02, 03, 04 |
| `STAND_DOWN` | Conditions too unclear or risky; trade smaller than allowed by mode |

Each output carries a `confidence: 0–100` score. Setups require
`confidence ≥ 50` to count the bias toward A+ grade.

---

## 3. Scoring Components (sum to 100)

| Component | Weight | Source |
|-----------|-------:|--------|
| Higher-timeframe trend (1h slope) | 25 | Input 14 |
| Overnight inventory | 15 | Inputs 3, 13 |
| Gap classification | 10 | Inputs 5, 7 vs ON range |
| VA migration | 15 | Last 3 sessions VAH/VAL/VPOC drift |
| Liquidity-pool location | 15 | Where unrun pools sit vs current price |
| Open-type expectation | 10 | TPO open-type rules |
| VIX environment | 10 | Latest VIX vs 20-day MA |

---

## 4. Component Rules

### 4.1 Higher-timeframe trend (25 points)

```
slope = linear_regression_slope(close, last 200 × 1h bars)
slope_pct = slope / mean(close, last 200 × 1h bars)

if slope_pct > +0.0005: LONG +25
elif slope_pct < -0.0005: SHORT +25
elif abs(slope_pct) > 0.0002: half-weight in direction (+12 or -12)
else: BALANCED +25 (allocated to neutrality)
```

### 4.2 Overnight inventory (15 points)

| Inventory | Definition | Bias contribution |
|-----------|-----------|-------------------|
| Long | ETH close in upper 25% of overnight range AND CVD positive | SHORT +15 (expect rebalance lower) |
| Short | ETH close in lower 25% AND CVD negative | LONG +15 |
| Balanced | ETH close in middle 50% | BALANCED +15 |

### 4.3 Gap classification (10 points)

| Gap type | RTH open vs prior value | Contribution |
|----------|------------------------|--------------|
| Gap inside prior VA | Open within [VAL, VAH] | BALANCED +10 (favor 02) |
| Gap outside, ≤ 0.75× VA width | Above VAH or below VAL by small amount | RANGE_EXPANSION_LIKELY +5, **direction TBD by open type** |
| Gap outside, > 0.75× VA width | Large gap | MEAN_REVERSION_LIKELY +10 (favor Setup 03) |

### 4.4 VA migration (15 points)

Track VAH, VAL, VPOC across the last 3 sessions:

| Pattern | Contribution |
|---------|--------------|
| 3 sessions of higher VPOC + higher VAH | LONG +15 |
| 3 sessions of lower VPOC + lower VAL | SHORT +15 |
| Overlapping VAs (≥ 70% overlap each pair) | BALANCED +15 |
| Diverging (VPOC drift unclear) | 0 |

### 4.5 Liquidity-pool location (15 points)

Identify **unrun** pools (PDH/PDL/ONH/ONL/IBH/IBL/weekly H/L/poor
highs/lows) within 1× ATR(1h, 20) of current price.

| Pool direction | Contribution |
|----------------|--------------|
| Unrun pool above only | LONG_BIAS +10 (market hunts upside liquidity) |
| Unrun pool below only | SHORT_BIAS +10 |
| Pools both sides, but one is multi-session confluence | Bias toward the confluence side +15 |
| No clear unrun pool | 0 |

### 4.6 Open-type expectation (10 points)

Based on overnight characteristics, classify expected RTH open type:

| Open type | Probability cue | Bias contribution |
|-----------|----------------|-------------------|
| Open-Drive | Overnight strong directional, ON range > 1× 20-day avg | RANGE_EXPANSION_LIKELY +10 + direction +5 |
| Open-Test-Drive | Overnight quiet, then push at open | RANGE_EXPANSION_LIKELY +5 |
| Open-Rejection-Reverse | Overnight extreme into a known level | Counter-direction bias +10 |
| Open-Auction | Overnight balanced inside prior VA | BALANCED +10 |

### 4.7 VIX environment (10 points)

| VIX vs 20d MA | Regime hint | Contribution |
|----------------|-------------|--------------|
| < 0.85× 20d MA | Low vol | MEAN_REVERSION_LIKELY +10 |
| 0.85× to 1.15× | Normal | 0 (no bias) |
| 1.15× to 1.5× | Elevated | RANGE_EXPANSION_LIKELY +5 |
| > 1.5× | High | STAND_DOWN +10 (reduce size, see § 6) |

---

## 5. Aggregation Logic

```
bias_long  = sum of components contributing to LONG
bias_short = sum of components contributing to SHORT
bias_balanced / range_exp / mean_rev / stand_down = analogous

classification = argmax(bias_long, bias_short, ..., stand_down)
confidence     = score_of(classification)  # already on 0-100 scale

if confidence < 30: classification = BALANCED, confidence = 30
if stand_down_score >= 30: classification = STAND_DOWN
```

---

## 6. Stand-Down Conditions (override classification)

Set classification to `STAND_DOWN` if **any**:

- VIX > 1.5× 20d MA AND > 25 absolute.
- HIGH-impact news within first 60 min RTH.
- Overnight range > 1.5× prior 20-day avg AND no clear directional
  inventory (chop expectation).
- Data feed quality flag: ≥ 3 stale-tick events in the last 60 min.

---

## 7. Daily Output Format

```json
{
  "date": "2026-05-13",
  "classification": "SHORT_BIAS",
  "confidence": 64,
  "components": {
    "ht_trend":           { "side": "SHORT", "points": 12 },
    "overnight_inventory":{ "side": "SHORT", "points": 15 },
    "gap":                { "side": "BALANCED", "points": 5 },
    "va_migration":       { "side": "SHORT", "points": 15 },
    "liquidity_pools":    { "side": "SHORT", "points": 10 },
    "open_type":          { "side": "SHORT", "points": 5 },
    "vix":                { "side": "NEUTRAL", "points": 0 }
  },
  "key_levels": {
    "PDH": 5214.00, "PDL": 5187.25,
    "ONH": 5210.50, "ONL": 5192.00,
    "VAH": 5208.75, "VAL": 5193.50, "VPOC": 5201.25,
    "IBH": null, "IBL": null,
    "weekly_H": 5226.00, "weekly_L": 5181.50
  },
  "unrun_pools": ["weekly_H above", "PDL below"],
  "open_type_expectation": "Open-Drive (short)",
  "stand_down_flag": false,
  "allowed_setups_today": ["01", "02", "04"],
  "banned_setups_today": ["05"],
  "notes": "Overnight inventory short, VA migrating down 3 sessions; favor reversal-into-resistance shorts."
}
```

---

## 8. Pre-Session Workflow

The trader (or engine) runs this sequence by **09:25 ET**:

1. Pull inputs 1–15 (manual checklist or automated).
2. Compute the seven component scores.
3. Aggregate to classification + confidence.
4. Check stand-down conditions.
5. Emit the daily output JSON.
6. Cross-reference against `checklists/premarket_checklist.md`.

---

## 9. Programmatic Hook

```
function compute_daily_bias(market_data, prior_session, ovnt):
    components = {
        "ht_trend":           score_ht_trend(market_data),
        "overnight_inventory":score_ovnt_inventory(ovnt),
        "gap":                score_gap(prior_session, market_data),
        "va_migration":       score_va_migration(prior_session_history),
        "liquidity_pools":    score_liq_pools(market_data, levels),
        "open_type":          score_open_type(ovnt, prior_session),
        "vix":                score_vix(market_data)
    }
    classification, confidence = aggregate(components)
    if check_stand_down(market_data, news_calendar):
        classification = "STAND_DOWN"
    return { classification, confidence, components, key_levels, unrun_pools, ... }
```

---

## 10. Review

The bias engine's outputs are tracked in
`journal/daily_trade_journal.md`. Weekly review compares classification
accuracy (did `LONG_BIAS` days actually go long?) and adjusts component
weights only after a **30-session sample** demonstrates a systematic
miscalibration.
