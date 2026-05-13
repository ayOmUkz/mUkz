# ES vs NQ Personality

ES and NQ are correlated but **behaviorally different**. Treating them
as one instrument is a common mistake. This file defines the
instrument-specific parameters used across the playbook.

---

## 1. Contract & Tick Reference

| Spec | ES (E-mini S&P 500) | NQ (E-mini Nasdaq) |
|------|---------------------|---------------------|
| Tick size | 0.25 index pts | 0.25 index pts |
| Tick value | **$12.50** | **$5.00** |
| Point value | $50.00 | $20.00 |
| Margin (intraday, typical) | ~$500 – $1,500 | ~$500 – $1,500 |
| RTH session | 09:30 – 16:00 ET | 09:30 – 16:00 ET |
| Globex (ETH) | 18:00 – 17:00 ET | 18:00 – 17:00 ET |
| Halt window | 17:00 – 18:00 ET | 17:00 – 18:00 ET |

---

## 2. Behavioral Characteristics

| Characteristic | ES | NQ |
|----------------|----|-----|
| Auction cleanliness | **High** — respects VA edges, prints clean profile | **Lower** — frequent stop runs, messy edges |
| Average daily range (20d) | ~25 – 50 pts | ~150 – 300 pts |
| Typical ATR(5m, 20) RTH | ~3 pts (12 ticks) | ~15 pts (60 ticks) |
| Impulsiveness | Moderate | **High** — moves are bigger and faster |
| Liquidity at extremes | Very deep | Deep but thinner at NQ extremes |
| Reaction to macro news | Strong | **Stronger** — tech-weighted reactions |
| Best regime fit | `BALANCE`, `TREND` | `TREND`, `VOLATILITY_EXPANSION` |
| Setup affinity | 02, 03 (responsive) | 01, 04, 05 (reversal + breakout) |

---

## 3. Per-Setup Parameter Differences

| Parameter | ES | NQ |
|-----------|----|-----|
| **Setup 01** sweep buffer | 2 ticks (0.50 pt) | 4 ticks (1.00 pt) |
| **Setup 01** stop buffer beyond extreme | 2 ticks | 4 ticks |
| **Setup 02** entry tolerance | 1 tick | 2 ticks |
| **Setup 02** stop buffer beyond rejection wick | 3 ticks | 5 ticks |
| **Setup 03** stop buffer beyond VA edge | 4 ticks | 8 ticks |
| **Setup 04** LVN min width | 3 ticks | 6 ticks |
| **Setup 04** entry tolerance | 1 tick | 2 ticks |
| **Setup 05** LVN min width | 3 ticks | 6 ticks |
| **Setup 05** pullback wick stop buffer | 2 ticks | 4 ticks |

The buffers scale with NQ's higher ATR. Using ES buffers on NQ
guarantees stop-outs on normal noise.

---

## 4. Correlation Behavior

**30-day rolling correlation** (typical): 0.85 – 0.95.

Rules:

| 30-day corr | Cross-trading rule |
|-------------|--------------------|
| ≥ 0.9 | Take first signal only. Skip the second leg entirely. |
| 0.7 – 0.9 | Take first at full size. Reduce second leg by **40%**. |
| < 0.7 | Both legs full size, treat as independent. |

The correlation regime is recomputed weekly from the prior 30 RTH
sessions' 5m returns.

---

## 5. Session Behavior Differences

| Window (ET) | ES tendency | NQ tendency |
|-------------|------------|-------------|
| 09:30 – 10:30 | Establishes day's character; IB is informative | Often gappier; opening drives can persist |
| 10:30 – 11:30 | Rotation around VPOC | Initial pullback or extension |
| 11:30 – 13:30 | Lunch chop — narrow range, mean-reverting | **Often deceptive** — fake breakouts |
| 13:30 – 15:00 | Afternoon trend or rotation | Trend acceleration on news cues |
| 15:00 – 15:30 | Position squaring | **Increased volatility** as funds rebalance |
| 15:30 – 16:00 | Close-driven imbalances | Stronger imbalances; noisy |

---

## 6. When to Prefer One Over the Other

| Condition | Prefer |
|-----------|--------|
| Clean balance regime, responsive setups | **ES** |
| News-driven trend day, volatility-expansion regime | **NQ** |
| Wide stop required to satisfy R:R ≥ 2 | **NQ** (better tick value efficiency) |
| Tight stop available | **ES** (cleaner structure) |
| Setup 05 (Initiative breakout) | **NQ** (lives in trend regime) |
| Setup 02 (Value Area Rejection) | **ES** (auction respects edges) |
| Account near trailing DD threshold | **ES** (slower moves, easier to size down) |

---

## 7. Per-Instrument Stand-Down Conditions

### ES
- VIX > 28 absolute → stand down.
- ES specific halt risk: hit limit move on overnight (uncommon, but
  blocks open).
- SPX cash open imbalance > $1B same direction → first 5 minutes RTH
  no entries.

### NQ
- VIX > 28 AND NDX-specific top-name earnings same week → reduce to
  half size or stand down.
- NQ specific: 5 consecutive 5m bars with range > 2× ATR(5m, 20) →
  pause for 15 min, reclassify regime.

---

## 8. Output Block (consumed by execution engine)

```json
{
  "instruments": {
    "ES": {
      "tick_size": 0.25,
      "tick_value": 12.50,
      "sweep_buffer_ticks": 2,
      "stop_buffer_ticks": 2,
      "min_lvn_width_ticks": 3,
      "session_atr_baseline_pts": 3.0,
      "low_vol_atr_threshold_pts": 1.8,
      "preferred_regimes": ["BALANCE", "TREND"],
      "preferred_setups": ["02", "03", "01"]
    },
    "NQ": {
      "tick_size": 0.25,
      "tick_value": 5.00,
      "sweep_buffer_ticks": 4,
      "stop_buffer_ticks": 4,
      "min_lvn_width_ticks": 6,
      "session_atr_baseline_pts": 15.0,
      "low_vol_atr_threshold_pts": 9.0,
      "preferred_regimes": ["TREND", "VOLATILITY_EXPANSION"],
      "preferred_setups": ["01", "04", "05"]
    }
  },
  "correlation_30d": 0.88,
  "cross_trade_rule": "reduce_second_leg_40pct"
}
```

---

## 9. Common Mistakes

1. **Using ES tick buffers on NQ** → premature stop-outs on normal
   noise.
2. **Trading NQ in `BALANCE` with responsive setups (02, 03)** → NQ
   often fakes through VA edges before mean-reverting; entries get
   stopped first.
3. **Trading ES in `VOLATILITY_EXPANSION` with full size** → ES
   expansion moves are still smaller than NQ's; the multiplier rule
   still applies but the R-value of each move is also smaller.
4. **Ignoring correlation** → 2× full size correlated is a single 2%
   risk trade in disguise.

---

## 10. Maintenance

The ATR baselines, sweep buffers, and correlation thresholds are
recomputed every **Sunday evening** from the prior 20 RTH sessions.
The output block in § 8 is regenerated and consumed by the engine on
Monday's open.
