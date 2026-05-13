# Market Regime Filter

The regime filter answers two questions:

1. Should the system **trade or stand down**?
2. **Which setups** are allowed today?

The output is one of five regimes plus a sub-state for the news
window. Setups consume the regime as a binary gate; trades against a
banned regime are rejected by the execution engine.

---

## 1. Regimes

| Regime | Definition |
|--------|-----------|
| `TREND` | Directional auction, range expansion, one-way price action |
| `BALANCE` | Two-way auction inside a defined range, value building |
| `VOLATILITY_EXPANSION` | High range with no clear direction; expansion bars in both directions |
| `LOW_VOL_CHOP` | Compressed range, no follow-through, mean-reverting micro-swings |
| `NEWS_RISK` | Active or imminent HIGH-impact news event |

A separate flag `POST_NEWS_EXPANSION` (true/false) is set for 30
minutes after a HIGH-impact release; it does not change the regime
but tightens position sizing (see § 5).

---

## 2. Classification Inputs

| Input | Source | Lookback |
|-------|--------|----------|
| **ADX(14)** on 1h | 1h closes | 14 bars |
| **ATR(20)** on 5m | 5m bars | 20 bars |
| **Overnight range vs 20-day median ATR** | ETH | last 20 sessions |
| **VIX** | Daily | latest close + 20d MA |
| **Time inside IB** (Initial Balance) | RTH 09:30–10:30 | first 60 min |
| **Range vs prior session range** | 1h | this session vs last |
| **News calendar** | External | upcoming HIGH events |

---

## 3. Classification Rules (priority order)

Evaluate in this order; the first matching rule wins.

### 3.1 NEWS_RISK (highest priority)

```
IF a HIGH-impact event is scheduled within ±60 min of "now"
   OR VIX > 1.5× 20d MA AND VIX > 25 absolute
THEN regime = NEWS_RISK
```

### 3.2 TREND

```
IF ADX(14, 1h) > 25
   AND |last 20 × 5m bars net direction| > 1.5× ATR(20, 5m)
   AND price has not closed back inside the most recent IB (if IB exists)
   AND HTF (1h) trend slope agrees with the directional move
THEN regime = TREND
```

### 3.3 VOLATILITY_EXPANSION

```
IF (overnight range > 1.25× 20-day median ATR
    OR last 6 × 5m bars include >= 2 with range >= 1.5× ATR(20, 5m))
   AND ADX(14, 1h) is rising
   AND price has broken out of the prior session's VA on the open
THEN regime = VOLATILITY_EXPANSION
```

### 3.4 LOW_VOL_CHOP

```
IF ATR(20, 5m) < 0.6× 20-day average of ATR(20, 5m)
   AND ADX(14, 1h) < 18
   AND last 12 × 5m bars net direction < 0.5× ATR(20, 5m)
THEN regime = LOW_VOL_CHOP
```

### 3.5 BALANCE (default)

```
ELSE regime = BALANCE
```

The classifier runs **every 5m** during RTH. A regime change is
debounced: it must be confirmed by **2 consecutive 5m classifier
runs** before the engine acts on it.

---

## 4. Per-Regime Setup Matrix

| Regime | Allowed setups | Banned setups | Best class |
|--------|---------------|---------------|------------|
| `TREND` | 05 | 01, 02, 03, 04 | Initiative continuation |
| `BALANCE` | 01, 02, 03, 04 | 05 | Responsive / failed auction |
| `VOLATILITY_EXPANSION` | 01, 04, 05 | 02, 03 | Reversal + breakout (no responsive trades) |
| `LOW_VOL_CHOP` | none | all | **Stand down** |
| `NEWS_RISK` | none (pending) | all | **No new entries**; tighten existing stops |

If a setup fires in a banned regime, the engine **rejects** with
reason code `regime_banned`.

---

## 5. Position Sizing Adjustment by Regime

| Regime | Sizing multiplier (applied after formula) | Notes |
|--------|------------------------------------------:|-------|
| `TREND` | 1.00 | Full size on aligned trades |
| `BALANCE` | 1.00 | Full size |
| `VOLATILITY_EXPANSION` | **0.50** | Half size; stops are wider, R-value of moves is larger |
| `LOW_VOL_CHOP` | n/a — no trades | — |
| `NEWS_RISK` | n/a — no new entries | — |
| `POST_NEWS_EXPANSION` flag | **0.50** | First 30 min after HIGH-impact event |

The multiplier is applied **after** the position sizing formula in
`risk/prop_firm_risk_rules.md` § 2 and after the trailing-DD
multiplier in `risk/daily_loss_protection.md` § 6. The **tightest**
constraint wins.

---

## 6. Automation Risk Level by Regime

| Regime | Automation level allowed |
|--------|--------------------------|
| `TREND` | NONE / ALERTS / SEMI / FULL |
| `BALANCE` | NONE / ALERTS / SEMI / FULL |
| `VOLATILITY_EXPANSION` | NONE / ALERTS / SEMI (no FULL) |
| `LOW_VOL_CHOP` | NONE / ALERTS only |
| `NEWS_RISK` | NONE / ALERTS only |

FULL automation is allowed only in clean directional or balanced
regimes. Volatility expansion always requires human-in-the-loop.

---

## 7. ES vs NQ Differences

NQ trends harder and chops harder. The classifier applies
**instrument-specific ATR thresholds**:

| Instrument | ATR(20, 5m) baseline | LOW_VOL threshold |
|------------|---------------------:|-------------------|
| ES | ~3.0 pts (12 ticks) | < 1.8 pts |
| NQ | ~15 pts (60 ticks) | < 9 pts |

The thresholds are recomputed every Sunday from the prior 20 sessions'
median ATR.

See `es_vs_nq_personality.md` for full per-instrument behavior.

---

## 8. Daily Regime Output

```json
{
  "timestamp_utc": "2026-05-13T13:30:00Z",
  "regime": "BALANCE",
  "prior_regime": "BALANCE",
  "regime_age_min": 78,
  "inputs": {
    "adx_1h": 17.4,
    "atr_5m_20": 3.2,
    "atr_5m_20_vs_20d_avg": 0.94,
    "ovnt_range_vs_20d_med_atr": 1.04,
    "vix": 14.8,
    "vix_vs_20d_ma": 0.92
  },
  "news_window_active": false,
  "post_news_expansion_flag": false,
  "allowed_setups": ["01", "02", "03", "04"],
  "banned_setups":  ["05"],
  "size_multiplier": 1.00,
  "automation_level_cap": "FULL"
}
```

---

## 9. Programmatic Hook

```
function classify_regime(now, market_data, news_calendar):
    if news_calendar.high_within(±60 min): return "NEWS_RISK"
    if vix() > 1.5 * vix_20dma() and vix() > 25: return "NEWS_RISK"
    if adx_1h() > 25 and trending(): return "TREND"
    if expansion_conditions(): return "VOLATILITY_EXPANSION"
    if compression_conditions(): return "LOW_VOL_CHOP"
    return "BALANCE"

# debounce
if classify_regime() == prior and classify_regime() == prior_prior:
    commit_regime(classify_regime())
```

---

## 10. Maintenance

Regime thresholds (ADX, ATR multipliers, VIX bands) are reviewed
quarterly via `journal/weekly_performance_review.md`. Adjust only
after ≥ 60 sessions of evidence demonstrating systematic
misclassification.
