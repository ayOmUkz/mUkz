# Volume Profile Big Opportunity Detection Engine — Blueprint

## Context

The repository (`/home/user/mUkz`, branch `claude/volume-profile-opportunity-engine-R4XZV`) is currently empty (only a `.gitkeep`). We are building a greenfield Pine Script v6 system for TradingView that goes beyond surface-level volume profile S/R and answers Auction Market Theory questions: who is trapped, who controls value, where inventory is imbalanced, and what the auction is attempting next. The first deliverable is this blueprint — no code yet — so the system is fully designed before any line is written. The intended target instruments are CME ES and NQ futures, with separate handling of RTH vs. ETH sessions.

---

## 1. System Purpose

A modular, non-repainting TradingView indicator that:

- Computes a session-anchored Volume Profile (POC, VAH, VAL, HVNs, LVNs) for prior and developing sessions.
- Classifies the current auction state (Balance / Failed / Initiative / Repair).
- Detects 7 high-quality setups ("BIG OPPORTUNITY") on bar close.
- Scores each setup 0–100 across 5 dimensions and assigns A+ / A / B / No Trade.
- Emits labels, regime backgrounds, a dashboard table, and per-setup alert conditions.
- Is built so each layer (calc → state → setup → score → render → alert) can be modified independently.

Primary users: discretionary ES/NQ futures traders who already understand auction theory and want a rule-based confirmation/scanner layer.

---

## 2. Market Theory (operating assumptions)

- Markets are two-way auctions; price advertises, volume confirms.
- Value = the price range where the market spent ~70% of session volume (VAH/VAL bound it; POC is the fairest price).
- Acceptance = price holds outside value AND new volume builds there.
- Rejection = price probes outside value AND snaps back inside without building volume.
- Trapped traders create the fuel for the next move; their forced exit is the opportunity.
- Single prints, poor highs/lows, and LVNs are unfinished business — magnets for repair.
- "Big" opportunities require multiple confluences: location + state + trap + acceptance/rejection + inventory imbalance + order flow + clean target.

---

## 3. Auction States

State machine with one active state per bar (after close):

| State | Definition | Best trade type |
|---|---|---|
| Balance | Developing POC stationary (within N ticks for K bars), price oscillating inside developing VA | Responsive fade VAH→POC, VAL→POC |
| Failed Auction | Excursion outside prior VA that fails to build value and reclaims VA | Fade back through VA toward POC / opposite extreme |
| Initiative Expansion | Excursion outside prior VA that holds, builds volume, and migrates POC | Continuation on pullback to broken VA edge |
| Repair Auction | Price targeting prior single prints / poor highs/lows / LVNs / unfinished gaps | Trade toward repair zone, exit on completion |

Transitions are evaluated on confirmed bars only and require at least M consecutive bars of the new condition before flipping (debounce to avoid flip-flop).

---

## 4. Required Inputs

Group 1 — Session
- RTH session string (default `0930-1600` America/New_York for ES/NQ index).
- ETH toggle (true = use 24h, false = RTH only).
- Profile lookback: how many prior sessions to render (default 1, max 5).

Group 2 — Profile resolution
- Row size mode: `Auto by ATR` | `Ticks` | `Points`.
- Manual row size (ticks).
- Value Area % (default 70).
- Lower-timeframe source for volume-by-price (default `1` minute via `request.security_lower_tf`).

Group 3 — HVN / LVN
- HVN threshold = volume bin ≥ X× median bin volume (default 1.5).
- LVN threshold = volume bin ≤ Y× median bin volume (default 0.4).
- Min bin width for LVN run (ticks).

Group 4 — Order flow
- CVD source: `Built-in ta.requestVolumeDelta` (locked for v1).
- CVD lookback bars for divergence (default 20).
- Absorption: large delta with price not progressing (configurable thresholds).

Group 5 — Detection sensitivity
- Min bars outside VA to qualify as breakout/breakdown (default 3).
- Min bars holding outside VA for "acceptance" (default 5).
- POC migration threshold (ticks/bar).
- POC stretch threshold for magnet setup (ATR-multiples from POC).

Group 6 — Scoring weights & grade cutoffs (tunable, defaults below).

Group 7 — Visuals & alerts
- Toggle each setup on/off.
- Dashboard position, size, theme.
- Show/hide regime background, profile lines, HVN/LVN bands.

---

## 5. Required Calculations

All calculations run on confirmed bars (`barstate.isconfirmed`) and use only past data. Intraday "developing" values update bar-by-bar; "prior" values are frozen at session close.

5.1 Session bookkeeping
- `inSession` boolean from session input.
- `sessionStart` / `sessionEnd` event bars.
- On `sessionEnd`: snapshot developing → prior. Reset accumulators.

5.2 Volume-by-price (per session)
- Define price grid: `rowSize` ticks, anchored to session open.
- For each confirmed bar, request lower-TF (1-min default) bars via `request.security_lower_tf`.
- Distribute each LTF bar's volume across the price bins it spans (linear pro-rata across `[low, high]`).
- Maintain two arrays per session: `prices[]`, `volumes[]`.

5.3 POC / VAH / VAL
- POC = price of bin with max volume.
- Value Area: starting at POC, repeatedly add the larger-volume neighbor (above or below) until cumulative volume ≥ 70% of total. VAH = highest accepted bin top; VAL = lowest accepted bin bottom.
- Compute for prior session (frozen) and developing session (live, updates each bar).

5.4 HVN / LVN
- Median bin volume `medV`.
- HVN bins: `volume[i] ≥ HVN_mult * medV`. Cluster contiguous bins → HVN zone (top, bottom, peak).
- LVN bins: `volume[i] ≤ LVN_mult * medV` AND surrounded by higher-volume bins on both sides. Cluster → LVN zone.

5.5 Distance / stretch from POC
- `stretchATR = (close - dPOC) / atr(14)`.
- Used by POC magnet setup.

5.6 Acceptance / rejection
- Define `outsideVA` = `close > priorVAH or close < priorVAL`.
- Acceptance = `outsideVA` true for ≥ `acceptBars` bars AND new bin volume in that zone > prior session median bin.
- Rejection = excursion outside VA for ≥ 1 bar but ≤ `acceptBars` bars, then reclaim with close back inside VA.

5.7 POC migration
- `pocSlope = dPOC - dPOC[migrationLookback]`.
- `migrating` = |pocSlope| ≥ `migrationThreshold` ticks AND monotonic (no reversals in window).

5.8 CVD / delta
- `ta.requestVolumeDelta` (Pine v6 built-in) — locked source for v1.
- Compute session-anchored CVD, CVD slope, CVD divergence vs price (higher highs in price + lower highs in CVD → bearish).

5.9 Volume expansion
- `volExp = sessionVolumeRunRate / avgRunRateLastN`.
- `expanding` = `volExp ≥ 1.25`.

5.10 Trap quality
- Trapped longs: bar closes below VAH after recently making a new high above VAH on positive delta.
- Trapped shorts: bar closes above VAL after recently making a new low below VAL on negative delta.
- Quality = magnitude of failed excursion × delta against trap × time spent outside.

5.11 Failed auction logic
- Excursion bars outside VA, then reclaim, then retest fails to recapture excursion high/low with negative follow-through delta.

5.12 Helper utilities
- `tickRound(p)`, `inRange(p, lo, hi)`, `clusterBins(...)`, `crossEvent(...)` — kept in a single `utils` block.

---

## 6. Setup Logic (all gated on `barstate.isconfirmed` of the signal timeframe)

S1 — Failed Breakdown Below VAL → LONG
- Bar(s) closed below `priorVAL` for 1..N ≤ `acceptBars`.
- Current bar reclaims and closes above `priorVAL`.
- CVD made no new low OR diverged bullishly during excursion.
- Delta on excursion bars net negative (sellers chased) but next bar absorbed (delta < 0, range up).
- Targets: dPOC → priorPOC → priorVAH → poor high / liquidity above.
- Invalidation: close back below VAL after reclaim, or new low on negative delta.

S2 — Failed Breakout Above VAH → SHORT
- Mirror of S1 around priorVAH.
- Targets: dPOC → priorPOC → priorVAL → poor low / liquidity below.

S3 — 80% Value Rotation
- Bullish: open outside priorVA below, reclaim priorVAL, hold inside priorVA for ≥ `acceptBars`. Target priorPOC then priorVAH.
- Bearish: mirror — open above priorVA, lose priorVAH, hold inside, target priorPOC then priorVAL.
- Requires no immediate rejection (no close back outside within hold window).

S4 — Initiative Expansion Above VAH → LONG
- Close > priorVAH for ≥ `acceptBars` bars.
- New bin volume above priorVAH > prior session median bin (acceptance).
- dPOC migrating up (5.7).
- CVD makes higher highs, higher lows.
- Pullback condition: prior bar low touches priorVAH ± buffer, current bar holds → entry.
- Target: next HVN above / prior session high / liquidity pool.

S5 — Initiative Expansion Below VAL → SHORT
- Mirror of S4.

S6 — LVN Air Pocket Move
- Identify nearest LVN zone vs current price.
- Long version: price accepts above LVN bottom, momentum bar enters LVN with expanding volume (5.9), no opposing HVN within `LVN width × 1.5`. Target next HVN above.
- Short version: mirror, target next HVN below.
- Invalidation: price stalls inside LVN for > `acceptBars` (no air pocket — the LVN became HVN).

S7 — POC Magnet Inventory Unwind
- `|stretchATR| ≥ stretchThreshold` (default 2.5).
- No new value built at extreme (no new HVN forming).
- CVD divergence against direction of stretch.
- Volume drying up on continuation (5.9 < 0.9).
- Bias = back toward dPOC.
- Targets: dPOC → priorPOC.

Each setup outputs a struct: `{name, side, score, grade, target1, target2, target3, invalidPrice}`.

---

## 7. Scoring Model

Per-setup, sum five components → 0–100:

| Component | Weight | How it's earned |
|---|---|---|
| Location alignment | 0–25 | At priorVAH/VAL/POC, dVAH/VAL/POC, HVN edge, LVN edge, prior/ON high-low — full points only when ≤ 1 row from the level |
| Trap quality | 0–25 | Magnitude of failed excursion (ATR-normalized) × delta-against-trap × time-outside (capped) |
| Acceptance / rejection quality | 0–20 | Clean reclaim with close inside, or clean acceptance with rising bin volume; partials for marginal cases |
| Order flow confirmation | 0–20 | CVD direction + divergence + absorption signature |
| Target clarity | 0–10 | Distance to nearest opposing HVN ≥ 1.5× distance to target; +bonus if poor structure repair |

Grades:
- A+ : 85–100
- A : 70–84
- B : 55–69
- No Trade : < 55

Scoring is implemented as pure functions per component so weights/cutoffs are tunable from inputs.

---

## 8. Visual Dashboard Design

8.1 Chart overlay
- Prior VAH/VAL/POC: solid horizontal lines, labeled at right edge.
- Developing VAH/VAL/POC: dashed lines, dynamic.
- HVN zones: subtle filled bands.
- LVN zones: hatched or low-opacity contrasting bands.
- Session background: tint by auction state (Balance=neutral, Failed=amber, Initiative=blue/green/red by side, Repair=violet).

8.2 Signal labels
- On confirmed setup bar: label with setup short code (`FB-VAL`, `FB-VAH`, `80%R↑`, `IE↑`, `IE↓`, `LVN↑`, `LVN↓`, `POC←`) plus grade (`A+`, `A`, `B`).
- Tooltip: full setup name, score breakdown, target list, invalidation price.

8.3 Dashboard table (top-right by default)
Row 1: Auction State | Bias | Trapped Side
Row 2: Active Setup | Grade | Score
Row 3: Target 1 / 2 / 3
Row 4: Invalidation level
Row 5: dPOC | dVAH | dVAL
Row 6: pPOC | pVAH | pVAL
Row 7: CVD slope | Volume expansion | Stretch (ATR)

Cells color-coded by state/grade.

---

## 9. Alerts

One `alertcondition` per setup × side, plus a meta-alert:

- `BIG_OPP_LONG_FB_VAL`
- `BIG_OPP_SHORT_FB_VAH`
- `BIG_OPP_LONG_80R`
- `BIG_OPP_SHORT_80R`
- `BIG_OPP_LONG_IE`
- `BIG_OPP_SHORT_IE`
- `BIG_OPP_LONG_LVN`
- `BIG_OPP_SHORT_LVN`
- `BIG_OPP_LONG_POC_MAGNET`
- `BIG_OPP_SHORT_POC_MAGNET`
- `BIG_OPP_ANY_A_PLUS` (fires on any A+ regardless of setup)

Alert payload (via `alert()`): JSON-style string with symbol, tf, setup, side, grade, score, entry, t1/t2/t3, invalid. Triggered only on bar close.

---

## 10. Pine Script Build Plan

File layout (single Pine v6 file, organized by `// ─── SECTION` banners):

```
//@version=6
indicator("VP Big Opportunity Engine", overlay=true, max_lines_count=500, max_labels_count=500, max_boxes_count=500)

// 1. INPUTS                  — all user inputs grouped
// 2. SESSION                  — RTH/ETH detection, session events
// 3. VOLUME-BY-PRICE          — LTF aggregation, bin arrays
// 4. PROFILE METRICS          — POC, VAH, VAL (prior + developing)
// 5. HVN / LVN                — node detection + clustering
// 6. ORDER FLOW               — CVD via ta.requestVolumeDelta, divergence, absorption
// 7. AUCTION STATE MACHINE    — balance / failed / initiative / repair
// 8. CONTEXT METRICS          — stretch, migration, vol expansion, trap quality
// 9. SETUP DETECTORS          — S1..S7, each in its own function
// 10. SCORING                 — per-component scorers + grader
// 11. RENDER                  — lines, bands, labels, table, bg color
// 12. ALERTS                  — alertcondition + alert() payloads
```

Build order (each step ends with a manual visual check on ES 5m and NQ 5m before moving on):

1. Inputs + session scaffolding.
2. LTF volume aggregation → render raw bins as histogram (sanity check vs TV's built-in VP).
3. POC/VAH/VAL (prior + developing) → compare to TV native.
4. HVN/LVN clustering → visual bands.
5. CVD via `ta.requestVolumeDelta` + divergence helpers.
6. Auction state machine + regime background.
7. S1, S2 (failed auctions) — easiest to validate visually.
8. S3 (rotation), S4/S5 (initiative).
9. S6 (LVN), S7 (POC magnet).
10. Scoring + grading.
11. Dashboard table.
12. Alerts.

Quality gates:
- All signals must respect `barstate.isconfirmed` before label/alert.
- No `request.security` with default `lookahead_on`.
- Snapshots happen exactly on session-end bar; never on the following bar.
- Manual repaint test: replay history vs live, confirm signal bars don't move.

Critical functions to design as pure & testable:
- `f_buildProfile(prices, vols, vaPct) → [poc, vah, val]`
- `f_clusterNodes(vols, prices, mult, dir) → array<zone>`
- `f_cvdDelta(src) → [cvd, slope, divergence]`
- `f_classifyState(...) → stateEnum`
- `f_score{Location|Trap|Quality|Flow|Target}(...) → int`
- `f_grade(score) → string`

---

## 11. Known Limitations

- Pine Script cannot access true tick-by-tick order flow; CVD via `ta.requestVolumeDelta` is the best available approximation on TV without external data.
- True bid/ask delta is not available without an external feed; absorption detection is heuristic.
- Volume-by-price is built from LTF bars distributed pro-rata across their range — not a true tick-distribution profile.
- Max 500 lines/labels/boxes per indicator; multi-session profile rendering must reuse and recycle objects.
- `request.security_lower_tf` increases load time and may hit TV's limits on long histories.
- Repaint risk if user enables `barmerge.lookahead_on` — explicitly disabled in code.
- Session anchoring is exchange-time-dependent; user must set the correct session string.
- HVN/LVN thresholds are heuristic (multiple of median bin) — not statistically rigorous.
- Backtesting is limited because this is an indicator, not a strategy. A separate `strategy()` wrapper is out of scope for v1.

---

## 12. Locked Decisions & Remaining Questions

Locked for v1 (confirmed by user):

1. **Pine v6** — gives us native `ta.requestVolumeDelta`, arrays, and maps.
2. **RTH-only default with ETH toggle** — session string defaults to `0930-1600` America/New_York; toggle exposes 24h.
3. **Built-in `ta.requestVolumeDelta` only** — no external CVD symbol input in v1; LTF proxy is dropped.
4. **Single combined indicator** — one `.pine` file covering profile + state + setups + scoring + dashboard + alerts. No split, no paired strategy.

Still open (defaults assumed unless user objects later):

5. Multi-session render depth: assume **prior session + developing** only for v1.
6. Composite (weekly / balance) profiles: **out of scope** for v1.
7. Strategy wrapper for backtesting: **out of scope** for v1.
8. Validation set: **ES + NQ on 1m, 5m, 15m** during RTH.

---

## Verification Plan (post-implementation)

1. Visual parity: load on ES 5m RTH; confirm prior/developing POC, VAH, VAL match TradingView's built-in Volume Profile within 1 row.
2. Non-repaint check: bar replay across a full session; confirm signals on confirmed bars stay fixed when going live.
3. State machine sanity: walk a known balance day, a known trend day, and a known failed-auction day; visually confirm regime classification.
4. Setup validation: hand-pick 5 historical examples per setup on ES and NQ; confirm at least 4/5 fire with grade ≥ B.
5. Alert smoke test: arm each `alertcondition` on demo; trigger via replay; confirm payload formatting.
6. Performance: load on 1m chart with 5 prior sessions of profile; confirm script runs under TV's compile/runtime limits.

---

## Critical Files (to be created in subsequent phases)

- `volume_profile_big_opportunity_engine.pine` — the single Pine v6 indicator file (repo root).
- `README.md` — usage notes, input descriptions, alert payload schema (after v1 code lands).
- `CHANGELOG.md` — version history (after v1 code lands).
