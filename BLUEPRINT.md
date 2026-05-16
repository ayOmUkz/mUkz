# MVP_TRADES — Volume Profile Big Opportunity Detection Engine

A rule-based Volume Profile intelligence engine that classifies futures auctions (ES/NQ focus) and surfaces only **BIG OPPORTUNITY** setups with clear bias, trapped side, target, grade, and invalidation.

**MVP shape:** single-page HTML dashboard. Detection layer in JS, intentionally structured to mirror Pine Script v6 1:1 so the later TradingView port is mechanical.

**Locked decisions (MVP):**
- Session: **RTH only** (09:30–16:00 ET) — 26 bars per session at 15m
- Data: **synthetic OHLCV generator + sample JSON** (each setup deliberately embedded)
- Order flow: **tick-rule CVD proxy** (`+vol if close>open, -vol if close<open`)
- Primary timeframe: **15-minute**

---

## 1. System Purpose

Identify high-quality, **non-repainting** trade opportunities in ES/NQ futures by interpreting Volume Profile + auction state + trapped inventory + order flow proxy. Output a single answer per bar close:

> *"Is there a BIG OPPORTUNITY here, in which direction, at what grade, to what target, and what kills it?"*

Not a S/R indicator. Not a multi-signal aggregator. One verdict per bar.

---

## 2. Market Theory (Auction Market Theory)

- Markets are two-way auctions. Price moves to advertise opportunity until that opportunity is rejected.
- **Value** = the price range where ~70% of period volume traded (VAH–POC–VAL).
- Price **outside value** is an advertisement. Price **inside value** is acceptance.
- Edge sources:
  - **Failed auctions** — price leaves value, fails to find acceptance, snaps back. Traps the chasers.
  - **Initiative expansion** — price leaves value, finds acceptance, POC migrates.
  - **Responsive rotation** — price re-enters value from outside, rotates to opposite extreme.
  - **Repair** — price seeks poor structure (single prints, poor highs/lows, LVNs left behind).

---

## 3. Auction States (mutually exclusive label per bar)

| State | Definition | Best Edge |
|---|---|---|
| **BALANCE** | POC stationary N bars, price oscillating inside VAH/VAL, range contracting. | Responsive fades VAH→POC, VAL→POC. |
| **FAILED AUCTION** | Price broke a value extreme then closed back inside within K bars with no value built outside. | Counter-trend back to POC / opposite extreme. |
| **INITIATIVE EXPANSION** | Price closed and held outside value, volume expanding, POC migrating in trend direction. | Continuation pullbacks to former extreme. |
| **REPAIR AUCTION** | Price trending toward poor structure (single prints, poor high/low, LVN gap from prior session). | Targeted move into the unfinished zone. |

State is determined by a precedence cascade (Failed > Repair > Initiative > Balance) evaluated only on confirmed bars.

---

## 4. Required Inputs

**User-controlled:**
- Symbol (ES / NQ / other)
- Session: RTH (09:30–16:00 ET) — MVP scope
- Value Area % (default 70)
- Profile lookback: current session + prior session + composite 5-day
- HVN threshold: top X% of price bins by volume (default top 15%)
- LVN threshold: bottom X% of price bins by volume (default bottom 15%)
- Failed-auction window K (default **3 bars** at 15m = 45 min)
- POC-stretch threshold (ATR multiples from developing POC, default 2.0)
- Min grade to display (default B = 55)
- Order flow proxy mode: `tick-rule` (MVP)

**Defaults calibrated for 15m RTH:**
| Parameter | Value | Rationale |
|---|---|---|
| K (failed-auction window) | 3 bars | 45 min window fits inside 26-bar session |
| ATR period | 14 | ≈ half a session |
| POC migration lookback | 8 bars | 2 hours |
| Volume avg window | 20 bars | smooths intra-session noise |
| Acceptance N bars outside | 2 confirmed closes | minimum for "held" |
| Composite profile | prior 1 + composite 5-day | balances recency vs structure |

**Data inputs (per bar):** timestamp, open, high, low, close, volume.

---

## 5. Required Calculations

All functions are pure, deterministic, evaluated on **closed bars only**.

### 5.1 Profile primitives (per session)
- `priceBins[]` — fixed-tick bins (ES 0.25, NQ 0.25; configurable)
- `binVolume[]` — volume at price (use OHLC distribution: split bar volume across H–L bins, weighted toward close)
- `POC` = argmax(binVolume)
- `VAH, VAL` = expand outward from POC until ≥ ValueArea% of total volume captured
- `HVNs` = local maxima of binVolume above HVN threshold
- `LVNs` = local minima below LVN threshold, bounded by adjacent HVNs

### 5.2 Prior vs developing
- **Prior** = previous completed session's profile (snapshot at session end, never repaints)
- **Developing** = current session profile updated each confirmed bar

### 5.3 Distance / stretch
- `pocDistanceATR = (close - devPOC) / ATR(14)`
- `stretchAbovePOC = pocDistanceATR > 2.0`
- `stretchBelowPOC = pocDistanceATR < -2.0`

### 5.4 Value acceptance / rejection
- **Acceptance outside value** = ≥ 2 consecutive confirmed closes outside VAH (or VAL) AND volume in those bars ≥ recent average.
- **Rejection** = close outside value followed by ≤ K bars and a close back inside.

### 5.5 POC migration
- `pocMigrationUp = devPOC[now] > devPOC[lookback=8] AND diff > tickSize * M`
- Mirror for down.

### 5.6 Order flow proxy (CVD)
- `delta = close > open ? +volume : close < open ? -volume : 0`
- `CVD = cumulative_sum(delta)`
- **Divergence**: price makes new low/high but CVD does not (compare last two swing pivots).
- **Absorption**: very high volume bar with small range, against the trapped side.

### 5.7 Volume expansion
- `volExpand = volume > avgVolume(20) * 1.5`

### 5.8 Failed auction trigger
- Breakout: high > VAH (or low < VAL)
- Within K confirmed bars: close back inside value AND no volExpand bar outside value
- Mark `failedBreakoutAbove` or `failedBreakdownBelow`.

### 5.9 Poor highs/lows / single prints
- **Poor high** = prior session's two highest TPO/volume rows have ≥ 95% of max — flat top, unfinished.
- **Poor low** = mirror.
- **Single prints** ≈ bins with volume < 10% of POC bin between two HVNs.

---

## 6. Setup Logic — 7 detectors

Each detector returns `{triggered, side, score, targets[], invalidations[]}`. Evaluated only on bar close.

### Setup 1 — Failed Breakdown Below VAL  (LONG)
1. Within last K bars, low < priorVAL.
2. Current bar close > priorVAL.
3. No bar in the window had volExpand AND close < priorVAL.
4. CVD on the dip ≥ CVD on prior swing low (bullish divergence).
5. Optional: retest of priorVAL holds.
- **Targets:** priorPOC → priorVAH → priorHigh / poorHigh.
- **Invalidation:** confirmed close back below priorVAL.

### Setup 2 — Failed Breakout Above VAH  (SHORT)
Mirror of Setup 1, above priorVAH.
- **Targets:** priorPOC → priorVAL → priorLow / poorLow.
- **Invalidation:** confirmed close back above priorVAH.

### Setup 3 — 80% Value Rotation
- **Bull:** open above priorVAH or below priorVAL; price re-enters and holds inside prior value ≥ 2 bars; bias toward opposite side. Re-entering from below → target POC then VAH.
- **Bear:** mirror. Re-entering from above → target POC then VAL.
- **Invalidation:** confirmed exit back through the side it re-entered from.

### Setup 4 — Initiative Expansion Above VAH (LONG)
1. Close > priorVAH for ≥ 2 confirmed bars.
2. volExpand on at least one breakout bar.
3. devPOC migrating up.
4. Pullback bar holds priorVAH (low ≥ priorVAH − tolerance, close > priorVAH).
5. CVD making higher highs.
- **Targets:** next HVN above / priorHigh / liquidity pool.
- **Invalidation:** confirmed close back inside priorValue.

### Setup 5 — Initiative Expansion Below VAL (SHORT)
Mirror of Setup 4.

### Setup 6 — LVN Air Pocket Move
- **Bull:** price accepted just above LVN low; volume in LVN zone < HVN_avg × 0.3; next HVN ≤ 2 × ATR above; momentum bar (close > open, volExpand, range > avgRange).
- **Bear:** mirror.
- **Targets:** next HVN.
- **Invalidation:** confirmed close back inside the LVN with volume.

### Setup 7 — POC Magnet Reversion
- **Bull:** stretchBelowPOC; CVD diverges bullishly vs recent low; volume drying up on continuation (last 3 bars vol < avgVol); reversal bar (close > open AND close > prior high).
- **Bear:** mirror.
- **Targets:** devPOC.
- **Invalidation:** confirmed new low after trigger, OR POC migrates further away.

---

## 7. Scoring Model

| Component | Max | Measures |
|---|---:|---|
| Location quality | 25 | Distance/alignment to prior VAH/VAL/POC/HVN/LVN/poor high-low. Multi-confluence = higher. |
| Trap quality | 25 | Size of overshoot before failure, volume on trap bar, bars trapped outside. |
| Acceptance/Rejection clarity | 20 | Speed/depth of reclaim (rejection) or persistence outside (initiative). |
| Order flow confirmation | 20 | CVD divergence strength, absorption, delta polarity vs setup side. |
| Target clarity | 10 | Distance to first target / R:R; clean path with no opposing HVN. |

**Grades:**
- **A+**: 85–100
- **A**: 70–84
- **B**: 55–69
- **No Trade**: < 55

Only the **single highest-scoring** triggered setup per bar is published. Ties broken by setup priority: Failed > Initiative > Repair (LVN) > Rotation > POC Magnet.

---

## 8. Visual Dashboard Design

Single-page HTML layout:

```
┌──────────────────────────────────────────────────────────────────────┐
│ MVP_TRADES  ·  ES  ·  RTH session  ·  bar close 14:30 ET             │ ← header
├───────────────────────────────────────┬──────────────────────────────┤
│                                       │  AUCTION STATE: FAILED       │
│   CANDLES + VP overlay (right side)   │  BIAS:          LONG         │
│   - prior VAH/VAL/POC lines           │  TRAPPED:       SHORTS       │
│   - dev  VAH/VAL/POC lines            │  GRADE:         A+  (88)     │
│   - HVN/LVN bands                     │  SETUP:         Failed       │
│   - signal labels at trigger bars     │                 Breakdown    │
│   - background tint = regime color    │                 Below VAL    │
│                                       │  TARGETS:       POC, VAH,    │
│                                       │                 PriorHigh    │
│                                       │  INVALIDATION:  Close <      │
│                                       │                 priorVAL     │
├───────────────────────────────────────┴──────────────────────────────┤
│ ALERT FEED (most recent first)                                       │
│ 14:30  A+  LONG  Failed Breakdown Below VAL  T:POC/VAH  Inv:<priorVAL│
│ 13:45  B   SHORT POC Magnet Reversion        T:devPOC   Inv:newHigh  │
└──────────────────────────────────────────────────────────────────────┘
```

**Regime colors (background):**
- BALANCE → neutral gray
- FAILED → amber
- INITIATIVE → green (up) / red (down)
- REPAIR → purple

**Chart lib:** lightweight-charts (TradingView open-source) — overlay-friendly, mirrors the Pine visual idiom.

---

## 9. Alerts

One alert condition per setup (7 total), plus a master "BIG OPPORTUNITY ≥ A" alert.

Payload format:
```
{symbol} {bias} {grade} {setup} | T1:{t1} T2:{t2} Inv:{invalidation} @ {bar_close_time}
```

- **HTML MVP:** toast + alert feed row + optional `Notification` API.
- **Pine v6:** `alertcondition()` per setup, with `alert.freq_once_per_bar_close` (non-repainting).

---

## 10. Pine Script v6 Build Plan (after HTML MVP validates logic)

Module order, each its own `// region`:

1. **Inputs** — all knobs from §4 as `input.*`.
2. **Session detection** — `time()` + `session.regular`; reset accumulators at session start.
3. **Profile arrays** — `array<float>` per bin; updated each bar with HL-distributed volume.
4. **POC/VAH/VAL functions** — pure functions over the binVolume array.
5. **HVN/LVN detection** — array scan for local extrema vs neighbors.
6. **Prior session snapshot** — freeze on session-end bar, store in `var` arrays.
7. **CVD proxy** — running cumulative on signed volume.
8. **State machine** — auction state classifier; uses only `barstate.isconfirmed`.
9. **Seven setup detectors** — each a function returning a named tuple.
10. **Scorer** — applies §7.
11. **Output** — `label.new`, `line.new`, `bgcolor`, `table.new` panel, `alertcondition`.
12. **Non-repaint guard** — every detector gated on `barstate.isconfirmed`; no `request.security` lookahead.

**Cross-port discipline:** JS detector function names match Pine names exactly (e.g. `detectFailedBreakdownBelowVAL(bar, state)` in both).

---

## 11. Known Limitations

- **No real bid/ask delta** on standard Pine charts — CVD is a tick-rule proxy. Real CVD requires footprint/order-flow data (not in TradingView core).
- **Volume-at-price approximation** — without true tick data, bar volume is distributed across H–L bins. Fine for 15m; lossy on 1m.
- **Composite profile cost** — N-day composite is O(bins × days) per bar; cap N at 10 (HTML) / 5 (Pine).
- **Single instrument** — one symbol at a time. Multi-symbol scanner is a follow-on.
- **No execution layer** — pure detection. Entry/stop sizing is operator-defined.
- **Pine `array<>` limits** — bin count ≤ ~5000; we adapt tick size if range demands.

---

## 12. Build Sequence

1. **This blueprint** ← current
2. **Synthetic data generator** — produces 5 RTH sessions of 15m bars, each session deliberately seeded to fire one or more of the 7 setups.
3. **Engine core** (`engine.js`) — profile math, state machine, 7 detectors, scorer. Pine-mirrored function names.
4. **Dashboard shell** (`index.html` + `styles.css`) — chart, panel, alert feed.
5. **End-to-end verification** — visually confirm every setup fires on the seeded bars; scrub-test for non-repainting.
6. **Pine v6 port** — translate `engine.js` module-by-module into a single `.pine` file.
