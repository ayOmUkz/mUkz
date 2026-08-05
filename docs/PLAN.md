# Dark Pool Intelligence Engine — Implementation Plan

## Context

You want an application that turns raw dark-pool prints from your Unusual Whales (UW) API subscription into careful, probabilistic market intelligence: where institutions *may* be accumulating or distributing, which price levels *may* matter, which prints are genuinely unusual, and what would invalidate each conclusion. The repo (`ayOmUkz/mUkz`) is empty today, so this is a greenfield build on branch `claude/unusual-options-activity-plpcje`.

Decisions you made during planning:
- **Cadence:** end-of-day pipeline first; near-real-time intraday mode added later.
- **Universe:** hybrid — cheap whole-tape discovery pass + deep analysis on discovered symbols and your watchlist.
- **Alerts:** dashboard feed + email digest.
- **Deployment:** local, single-user, Docker Compose. No dashboard auth needed initially.

Guiding principle baked into every component: **a dark-pool print never proves direction by itself.** Every print has a buyer *and* a seller, and the tape does not say who initiated. All directional conclusions come from an evidence ledger and are expressed probabilistically with invalidation conditions.

---

## 1. API capability assessment (verified, not assumed)

I inspected the live API through this session's UW connection: pulled real sample prints, the OpenAPI docs for the dark-pool endpoints, the per-price-level endpoint, and UW's own help articles.

### Endpoints we will use

| Endpoint | What it gives us | Notes (verified) |
|---|---|---|
| `GET /api/darkpool/recent` | Latest dark-pool prints across the whole market | `limit` ≤ 200, `date` param for past days, min/max premium/size/volume filters, `order_by` executed_at / trf_executed_at / premium / size / volume. **This is the discovery scan.** |
| `GET /api/darkpool/{ticker}` | All prints for one ticker on one day | `limit` ≤ 500 per call, `newer_than`/`older_than` timestamp pagination → full-day and multi-day history per symbol. **This is the deep fetch.** |
| `GET /api/darkpool/{ticker}/price-levels` | Provider-computed dark-pool + lit volume per rounded price bucket for a session | Independent cross-check for our own zone aggregation. |
| Websocket channel `off_lit_trades` | Real-time streaming of dark-pool prints | Documented in the API; reserved for the later intraday phase. |
| Supporting endpoints | candles/OHLC, stock state (current price), company info, stock screener (market cap/ADV), short interest & short volume, options flow alerts/screener, greek exposure (GEX), IV term structure, market tide, sector ETFs, earnings calendar, economic events, technical indicators (ATR etc.) | All exist in the same API family and are already reachable from this session. |

### Your Phase-1 checklist, mapped to reality

**Directly on each print (verified from live samples):** ticker, execution price, size (shares), premium (notional = price × size), execution timestamp (`executed_at`), TRF execution timestamp (`trf_executed_at`), report/tape timestamp (`created_at`), market center code, sale-condition codes, trade codes, extended-hours codes, NBBO bid & ask **with quantities**, canceled flag, consolidated day volume at print time, 30-day average volume, sector, issue type (Common Stock / ETF / ADR / Index), settlement type, tracking ID.

**Derivable (we compute):** price vs bid / ask / midpoint, price vs VWAP (from minute candles), % of ADV30, % of day volume, report delay (`created_at − executed_at`), distance from prior-day high/low, ATR context.

**Available via other endpoints:** current price, daily volume history, market cap, sector/industry, short interest, options flow, open interest, IV, earnings dates, economic events, market/sector trend.

**Not provided — the honest gaps:**
- **Buyer-vs-seller attribution.** Fundamental limit of TRF data, not a UW gap. We never pretend to know the aggressor.
- **Float / shares outstanding** — not on the print; may exist via company/short-data endpoints. *Verify in M1; float-based metrics stay optional until confirmed.*
- **FINRA ATS weekly venue statistics** — not exposed. Venue identity is only a one-letter `market_center` code.
- **Corrections feed** — only a boolean `canceled`; no correction/as-was history.
- **Bid/ask depth beyond the NBBO snapshot.**

---

## 2. Unknowns and limitations (flagged, not guessed)

1. **Historical depth** of `/darkpool/{ticker}?date=` is undocumented. M1 includes a probe script that walks backwards until the API stops returning data, and records the true horizon in the DB.
2. **Rate limits** are not stated in the OpenAPI docs I retrieved. The client will read rate-limit response headers at runtime, keep a token-bucket budget, and treat HTTP 429 as authoritative. Budget numbers live in config, not code.
3. **NBBO snapshot timing**: it is unclear whether `nbbo_bid/ask` reflect the quote at *execution* or at *report* time. For late-reported prints this changes the location classification entirely. M1 includes an experiment: for prints where `created_at − trf_executed_at` is large, check how often price falls outside the attached NBBO. Until resolved, late prints get `location_confidence = low`.
4. **`market_center` letter codes** (e.g. `"L"`) are not documented by UW. We store them raw and display them raw; no venue names are invented.
5. **`sale_cond_codes` / `trade_code` coverage**: the API enumerates `contingent_trade`, `odd_lot_execution`, `prior_reference_price`, `average_price_trade` and `derivative_priced`, `intermarket_sweep`, `qualified_contingent_trade`. Most sampled prints have `null` — meaning "regular way". Unknown codes, if they ever appear, are stored raw and flagged, never silently dropped.
6. **The MCP tools vs the REST API**: this planning session used the MCP wrapper; production code calls the public REST API with your API token. Field names matched in every sample I compared, but M1 asserts schema parity with recorded fixtures.
7. **EOD-first consequence**: intraday backtest horizons (5m/15m/30m/1h) only become truly honest once we run intraday ingestion and know when *we* would have seen each print. Until then those horizons are computed from historical candles and labeled "hypothetical — assumes real-time ingestion".

---

## 3. Data-field dictionary (plain language)

| Field | Type | Plain-language meaning |
|---|---|---|
| `ticker` | text | The stock symbol, e.g. `TSM`. |
| `size` | int | Number of shares in this single print. |
| `price` | decimal | Price per share the block traded at. |
| `premium` | decimal | Total dollars = price × size. ("How big was the check.") |
| `executed_at` | timestamptz | When the trade actually happened. **All analysis keys off this.** |
| `trf_executed_at` | timestamptz | When the trade was executed per the FINRA Trade Reporting Facility record. Usually equals `executed_at`. |
| `created_at` | timestamptz | When the print appeared on the tape / in the API. **All backtests key off this** — it's when *you* could have known. |
| `canceled` | bool | The trade was busted. Excluded from analytics, kept in raw storage. |
| `sale_cond_codes` | enum/null | Special settlement/reporting condition. `average_price_trade` ≈ institutional VWAP-style fill; `prior_reference_price` ≈ priced off an earlier quote (often a negotiated block reported late); `odd_lot_execution` ≈ tiny slice; `contingent_trade` ≈ tied to another transaction. `null` = regular. |
| `trade_code` | enum/null | `derivative_priced` ≈ leg of an options/derivative package (weak directional info); `qualified_contingent_trade` similar; `intermarket_sweep` ≈ aggressive sweep. `null` = regular. |
| `ext_hour_sold_codes` | enum/null | Marks prints executed outside regular hours or reported late ("sold out of sequence"). |
| `market_center` | char | One-letter reporting-facility code. Stored raw; letters are not mapped to venue names (undocumented). |
| `nbbo_bid` / `nbbo_ask` | decimal | Best public bid / offer attached to the print ("the sticker-price range"). |
| `nbbo_bid_quantity` / `nbbo_ask_quantity` | int | Shares displayed at those quotes — tells us how thin the public quote was vs the block. |
| `volume` | int | Symbol's total consolidated volume that day *up to this print*. |
| `avg30_volume` | decimal | 30-day average daily volume — our baseline for "how unusual is this size". |
| `tracking_id` | bigint | Provider's ID for the print. Part of our dedup key. |
| `trade_settlement` | enum | `regular` (T+1) vs cash/next-day. Non-regular settlement is flagged unusual. |
| `sector`, `issue_type` | text | Sector; Common Stock / ETF / ADR / Index. ETFs and index products are scored on separate curves. |

Analogy for the whole record: *a delivery receipt for furniture brought in through the back door — you see what, how much, at what price, and when the receipt was filed, but not who wanted the deal more.*

---

## 4. System architecture

Monorepo, four runtime containers (Docker Compose): **TimescaleDB**, **Redis**, **FastAPI backend**, **Next.js dashboard**. One scheduled job (APScheduler inside the backend container — deliberately not Airflow; simpler for one user) runs the nightly DAG.

Python packages (all under `backend/app/`):

- `client/` — typed UW REST client: auth from env, retries with exponential backoff, token-bucket rate limiting, timestamp pagination, response models.
- `ingestion/` — discovery scan + per-ticker deep fetch; writes `raw_prints` verbatim.
- `validation/` — the bouncer at the door (Section 8): dedup, sanity checks, quarantine. Only clean prints enter analytics.
- `enrichment/` — candles, VWAP, ATR, prior-day levels, company meta, short interest, options context, market context.
- `analytics/` — `classify.py` (per-print), `zones.py` (clustering), `inference.py` (accumulation/distribution ledger), `scoring.py` (all five scores).
- `scanner/` — ranked category queries.
- `alerts/` — rule evaluation → outbox table → dashboard feed + SMTP email digest, with dedup/cooldowns in Redis.
- `backtest/` — event-study engine over recorded signals.
- `api/` — FastAPI routers serving the dashboard (REST now; WebSocket reserved for intraday phase).
- `reports/` — renders the Phase-12 per-ticker output format (markdown + JSON).

Everything configurable lives in `config/settings.yaml` (weights, thresholds, universe, cadence) + `.env` (secrets only).

## 5. Data flow

```
                    NIGHTLY PIPELINE (after close)
┌──────────────┐   ┌───────────────┐   ┌───────────────┐
│ 1. DISCOVERY │──▶│ 2. DEEP FETCH │──▶│ 3. VALIDATION │──▶ raw_prints
│ /darkpool/   │   │ /darkpool/    │   │ dedup, sanity │    quarantine
│ recent       │   │ {ticker}      │   │ checks        │        │
│ (whole tape) │   │ (candidates + │   └───────┬───────┘        ▼
└──────────────┘   │  watchlist)   │           │          data_quality_log
                   └───────────────┘           ▼
┌──────────────────┐   ┌──────────────┐   ┌────────────┐
│ 6. ZONES         │◀──│ 5. CLASSIFY  │◀──│ 4. ENRICH  │◀─ candles, meta,
│ cluster prints   │   │ size/location│   │ VWAP, ATR, │   options, context
│ into price zones │   │ timing/liq.  │   │ prior days │
└────────┬─────────┘   └──────────────┘   └────────────┘
         ▼
┌──────────────────┐   ┌──────────────┐   ┌────────────┐   ┌───────────┐
│ 7. INFERENCE     │──▶│ 8. SCORING   │──▶│ 9. SCANNER │──▶│ 10. ALERTS│
│ evidence ledger  │   │ 5 sub-scores │   │ 10 ranked  │   │ dedup +   │
│ acc/dist/neutral │   │ + DPSS 0-100 │   │ categories │   │ digest    │
└──────────────────┘   └──────────────┘   └────────────┘   └───────────┘
                                                 │
                                                 ▼
                                   FastAPI ──▶ Next.js dashboard
                                   reports ──▶ per-ticker markdown/JSON
```

## 6. Database schema (TimescaleDB)

- `symbols` — ticker, name, sector, industry, issue_type, cap_bucket, marketcap, adv30, shares_outstanding*, float*, updated_at. (*nullable until M1 verifies availability.)
- `raw_prints` — verbatim JSONB payload + ticker, tracking_id, executed_at, ingested_at. Unique on `(ticker, tracking_id, executed_at)`. Hypertable on `executed_at`. Never mutated.
- `prints` — validated + enriched + classified: all API fields typed, plus `mid`, `spread_bps`, `price_vs_mid_bps`, `location_bucket`, `location_confidence`, `size_class`, `size_percentile`, `pct_adv30`, `pct_day_volume`, `timing_bucket`, `report_delay_s`, `character` (liquidity classification), `quality_flags[]`, `quality_score`. Hypertable on `executed_at`.
- `candles` — per-ticker 1-min (recent) and daily bars with computed session VWAP. Hypertable.
- `zones` — ticker, window_start/end, price_low/high, wavg_price, total_shares, total_notional, print_count, unique_days, first_print_at, last_print_at, pct_adv30, pct_of_dark_volume, strength_score, strength_class, status (`untested|tested|respected|reclaimed|broken`), config_version.
- `zone_events` — zone_id, ts, event (`touch|reject|reclaim|break|close_above|close_below`), price, evidence.
- `market_context` — date, spy_trend, qqq_trend, vix_regime, breadth, sector_trends JSONB, notable_events JSONB.
- `signals` — ticker, as_of, classification (6-state enum), confidence, dpss, sub_scores JSONB, evidence JSONB (`supporting[]`, `contradicting[]`), invalidation JSONB, context_label (`market_confirmed|sector_confirmed|technically_confirmed|conflicting|isolated`), available_at. Immutable once written (backtest integrity).
- `alerts` — rule, ticker, ref ids, payload, dedup_key, created_at, delivered_channels.
- `backtest_events` / `backtest_results` — frozen event snapshots and aggregated stats per segment/horizon.
- `data_quality_log` — every rejected/flagged print with reason.

## 7. Print classification logic

**Size** (per symbol, against its *own* history — a whale print in KO is a minnow print in NVDA):
- Maintain a rolling 60-trading-day distribution of that symbol's dark-print sizes (median, MAD, percentiles). Robust stats, not mean/SD, because print sizes are heavy-tailed.
- `normal` < p90 · `elevated` p90–p99 · `unusual` p99–p99.9 · `extreme` > p99.9 **or** > 1% of ADV30 **or** (if float confirmed) > 0.25% of float.
- Cold start (< 60 days of history): fall back to notional buckets per cap tier, marked `size_confidence = provisional`.

**Location** (a feature, never a verdict — stated in code comments and UI):
- `mid = (nbbo_bid + nbbo_ask)/2`; tolerance = 10% of spread. Buckets: at_bid / near_bid / below_mid / at_mid / above_mid / near_ask / at_ask / below_bid (outside) / above_ask (outside).
- Plus contextual tags: vs session VWAP (±0.1% band), vs prior-day high/low (within 0.25×ATR), inside/outside current consolidation range (from daily candles).
- Late-reported prints (`report_delay_s` > 900): `location_confidence = low` until the M1 NBBO-timing experiment resolves.

**Timing** (exchange-calendar aware, `pandas-market-calendars`): premarket / open (9:30–10:00) / morning / lunch (11:30–13:30) / afternoon / close (15:30–16:00) / after_hours / late_report (delay > 15 min, its own bucket — these are often negotiated blocks).

**Liquidity character** (always "possible/probable", driven by condition codes first):
- `average_price_trade` → probable routine institutional VWAP execution (de-emphasized in directional scoring).
- `derivative_priced` / `qualified_contingent_trade` → probable derivative-linked leg (e.g. buy-write) — near-zero directional weight.
- `prior_reference_price` or (large + long delay + at/outside spread) → possible negotiated block.
- `odd_lot_execution` → excluded from signals entirely.
- Large print + NBBO quantities tiny relative to size → probable dark-liquidity crossing (meaningful participation).
- Everything else → routine off-exchange liquidity / uncertain.

## 8. Data-quality safeguards (the bouncer)

| Check | How | False signal it prevents |
|---|---|---|
| Duplicates | Unique `(ticker, tracking_id, executed_at)`; pagination overlap fetches are idempotent upserts | One block counted 3× turns a weak zone "exceptional" |
| Canceled trades | `canceled=true` → raw only, never analytics | Phantom block that never stood |
| Late reports | `report_delay_s` computed for every print; late prints excluded from *intraday reaction* features | "Price rallied after the print" when the print became public *after* the rally |
| Out-of-sequence | `ext_hour_sold_codes` + executed_at vs created_at ordering checks | Same as above |
| Abnormal timestamps | executed_at in the future, > 7 days stale, or created_at < executed_at → quarantine | Zones built on garbage times |
| Zero/missing values | price ≤ 0, size ≤ 0, missing ticker → quarantine | Divide-by-zero notionals, junk zones |
| Impossible prices | Price outside that day's consolidated high/low ± 20% band (band configurable; wide-of-market blocks are legal) → flag `price_outlier`, exclude from zone weighting | A fat-finger print becomes a "magnet level" |
| Stale/crossed quotes | bid ≥ ask, or zero-size quotes → `location_confidence = none` | Wrong at-bid/at-ask labels |
| Splits & reverse splits | Nightly close-price jump detector (|1 − p_t/p_{t-1}·k| for common ratios) + split factor table; zones re-scaled or invalidated with an audit row | Yesterday's $500 zone "supporting" today's $50 stock |
| Symbol changes | Discovery symbols reconciled against company-info endpoint; unknown tickers quarantined until resolved | Zones split across old/new symbols |
| Outside-hours trades | Tagged premarket/after-hours, analyzed separately | Overnight prints polluting intraday reaction stats |

Every rejection is logged to `data_quality_log`, and each symbol-day gets a `data_quality_score` (share of clean prints, quote coverage, enrichment completeness) that gates the final DPSS.

**Three clocks, kept separate everywhere:** `executed_at` (when it happened — analytics), `created_at` (when the tape knew — backtests), ingestion time (when *we* fetched it — ops/debugging).

## 9. Zone clustering logic

*Analogy: don't mark every spot an elephant stood — find the watering holes they keep returning to.*

- Input per ticker: clean prints of class ≥ `elevated` over a rolling window (default 20 trading days; configurable).
- 1-D agglomerative clustering on price (DBSCAN-style in one dimension): sort prints by price; merge neighbors while gap ≤ ε.
- ε = max( 0.25 × ATR(14), 0.15% × price, 2 ticks ) — all three knobs configurable. ATR-scaling makes tolerance meaningful for both a $12 stock and a $1,200 stock.
- Time proximity: a zone additionally records per-day sub-totals; a zone touched on ≥ 3 distinct days ranks above one built in a single afternoon (recurrence beats burst).
- Per zone, compute exactly the metrics you listed: share-weighted average price, total shares, total notional, print count, first/last print time, % of day volume, % of ADV30, % of float (if available), distance from current price / VWAP / prior-day high & low, later price reactions (from candle crossings), and status: `untested` (price never returned) → `tested` (touched) → `respected` (touched and bounced ≥ 0.5×ATR) → `reclaimed` (crossed back above after breaking) → `broken` (closed beyond by > 0.5×ATR without reclaim in 3 sessions).

**Zone strength score (0–100, additive, capped components; all weights in `settings.yaml`):**

```
shares as % of ADV30      → 0–30   (log-scaled; 5%+ of ADV = full marks)
recurrence                → 0–20   (distinct days with qualifying prints)
recency blend             → 0–15   (exponential decay, half-life 5 sessions)
price tightness           → 0–10   (zone width vs ATR; tighter = higher)
dark-share concentration  → 0–10   (zone's share of the symbol's total dark volume in window)
observed price reactions  → 0–15   (respected touches; broken −, reclaimed +)
```
Classes: weak < 40 · moderate 40–60 · strong 60–80 · exceptional > 80. The formula is printed on the dashboard per zone ("show your work").

Cross-check: our aggregation for a ticker-day is compared against UW's own `/darkpool/{ticker}/price-levels`; large disagreement raises a data-quality flag.

## 10. Accumulation vs distribution inference

*Analogy: a court case. One witness — however loud — never convicts. You need independent witnesses telling a consistent story, and the defense (contradicting evidence) is always heard.*

Rules-first evidence ledger. Each evidence item = `(id, direction, weight 1–3, description, source_group)`. Source groups enforce independence:
- **A. Dark-pool structure** — repeated large prints in a tight zone; prints clustered while price holds.
- **B. Price behavior** — zone holds/reclaims (bull) or fails/breaks (bear); higher lows vs lower highs after prints; heavy volume without progress.
- **C. Relative strength & volume** — RS vs sector ETF improving/deteriorating; up/down-day volume asymmetry (our CVD proxy from daily/minute candles — the API has no true tick-level CVD; labeled as a proxy).
- **D. Options confirmation** — net call/put premium tilt, flow alerts near the zone strikes, GEX posture (from the options endpoints).

Verdict rules (defaults, configurable):
- ≥ 4 net weight AND ≥ 3 items AND ≥ 2 distinct source groups → `probable` (accumulation or distribution).
- ≥ 2 net weight AND ≥ 2 items in ≥ 2 groups → `possible`.
- Heavy activity, balanced evidence → `neutral institutional activity`.
- Not enough clean data (quality gate) or < 2 items → `insufficient evidence`.
- Confidence = logistic squash of (supporting − contradicting weight), **hard-capped at 0.85** — this system is never certain.

Every signal stores: supporting evidence, contradicting evidence, confidence, and machine-generated invalidation conditions (e.g. "daily close below 214.60 (zone low − 0.5×ATR)", "RS vs XLK makes a new 10-day low", "zone broken and not reclaimed within 3 sessions"). Invalidation is monitored nightly; triggered invalidations flip the signal to `invalidated` and emit an alert.

## 11. Signal scoring

Five sub-scores, each 0–100:
1. **Print significance** — size percentile (40%), % of ADV30 (25%), character (negotiated block > routine VWAP fill; derivative-linked ≈ 0) (20%), timing (15%).
2. **Zone significance** — the zone strength score (Section 9).
3. **Directional confidence** — evidence-ledger confidence × 100.
4. **Data quality** — Section 8 gate.
5. **Trade relevance** — proximity of the zone to current price (in ATRs), freshness decay, options availability, liquidity (spread + ADV), earnings distance.

**Dark Pool Significance Score:**
`DPSS = (0.25·print + 0.30·zone + 0.25·direction + 0.20·relevance) × (data_quality/100)` — quality multiplies (gates) rather than adds, so bad data can only hurt. All weights in `settings.yaml`.

**Cap-fairness rule (your requirement):** every raw metric that correlates with size (notional, shares, ADV%) is converted to a *percentile within the symbol's bucket* — mega, large, mid, small, ETF, index-product — before entering any score. A $40M print in a small cap can outscore a $400M print in SPY. ETFs/index products additionally get a "probable portfolio-flow, weak single-name signal" discount, configurable.

## 12. Market context

Nightly, from the same API family: SPY/QQQ trend (20/50-EMA slope + swing structure on daily candles), sector ETF trend for the symbol's sector, RS line vs sector, VIX regime (calm < 15 / normal 15–20 / stressed 20–30 / crisis > 30), market tide, gap direction, ATR, position vs VWAP and vs major daily S/R, earnings proximity (flag inside ±5 sessions), economic-events calendar, short interest, options premium tilt, GEX.
Each signal is then labeled: `market_confirmed` / `sector_confirmed` / `technically_confirmed` (can hold several) or `conflicting` or `isolated`. Context never *creates* a signal; it only confirms, conflicts, or isolates one.

## 13. Scanner

Ranked SQL views over `signals`/`zones`/`prints`, each row carrying a generated plain-English "why it ranked" string built from its evidence list. Global filters (all configurable): min notional, min size, min %ADV, min DPSS, max distance from price (ATRs), min repeated-print count, cap bucket, price floor, liquidity floor, sector, options availability, earnings window, freshness.

The ten default categories map to queries:
1. Fresh institutional activity — new qualifying prints today, DPSS-ranked.
2. Repeated accumulation zones — `probable/possible accumulation` + recurrence ≥ 3 days.
3. Repeated distribution zones — mirror.
4. Reclaims — `zone_events.event = reclaim` in last 2 sessions.
5. Rejections — `event = reject` at strong+ zones.
6. Unusually large single prints — class ≥ unusual, bucket-percentile ranked.
7. Options-confirmed dark-pool activity — group-D evidence present and aligned.
8. Dark pool vs price conflict — heavy prints + opposing price behavior (flagged, *not* auto-labeled "smart money fading").
9. Levels likely to matter today — strong+ zones within 1 ATR of last close.
10. Historical zones approaching — older strong zones within 2%, untested.

## 14. Alert architecture

- Rules evaluated at the end of the nightly run (and later intraday): new extreme print, repeated prints at a level, cumulative notional threshold, price approaching / touching / rejecting / reclaiming / closing through a zone, volume confirmation, options confirmation, **signal invalidated**, signal stale (no fresh evidence in N sessions → auto-expire).
- Every alert gets `dedup_key = hash(rule, ticker, round(zone_price, tolerance), direction)`. Redis `SETNX` + TTL enforces per-key cooldown (default 24h nightly / 30m intraday). Min-DPSS threshold per rule. Max alerts per symbol per day.
- Delivery: outbox table → dashboard feed (always) + one consolidated email digest after the nightly run (SMTP creds from env). Per-alert emails off by default to avoid spam; switchable for `extreme` only.

## 15. Dashboard (Next.js)

- **Market overview:** strongest activity today, top accumulation candidates, top distribution candidates, strongest zones market-wide, conflicting signals (its own section — honesty is a feature), data-quality banner (API health, last run, quarantine count).
- **Symbol detail:** price chart (lightweight-charts, TradingView's OSS library — eases future TradingView migration) with zone bands, print markers sized by percentile, VWAP; score breakdown showing each sub-score and formula; evidence panel with three columns — bullish, bearish, contradictory; invalidation levels drawn on the chart; options-confirmation panel.
- **Dark-pool tape:** table with execution time, report time (+delay), symbol, price, size, notional, condition codes, bid/ask/mid at print, location bucket, percentile, character, DPSS.
- Every technical term everywhere gets a plain-language tooltip from a single glossary file (e.g. NBBO: "the best public buy and sell prices at that moment — the 'sticker price range'").

## 16. Backtesting methodology

Event-study framework, honesty first:
- **Event = a stored signal or qualifying print, timestamped by `available_at` = `created_at`** (when the tape knew), never `executed_at`. In EOD mode, `available_at` additionally floors to "that evening's run" — we test what *this system* could actually have acted on.
- Entry = first candle open after `available_at` (+ configurable lag). Horizons: 5m, 15m, 30m, 1h, close, 1d, 3d, 5d, 20d. Intraday horizons carry the "hypothetical until intraday ingestion is live" label (Section 2.7).
- Metrics per cohort: hit rate, average & median return, MFE, MAE, max drawdown, volatility-adjusted return (return / ATR), false-positive rate (signals invalidated before any target), and **n with bootstrap confidence intervals — no cohort reported without its sample size**.
- Benchmarks: raw, market-adjusted (minus SPY), sector-adjusted (minus sector ETF). A "signal" that just tracks beta is not a signal.
- Segmentation: cap bucket, sector, market regime, size percentile, location bucket, time-of-day, repeated vs single print, accumulation vs distribution, earnings proximity, ETF vs single stock.
- Bias controls: features computed only from data with `available_at ≤ event time` (enforced by the immutable `signals` table — we backtest what was *actually written*, not recomputed); overlapping-event control (one active event per ticker-direction; overlaps flagged and also reported separately); duplicate-inflation control (zone-level events, not one event per print); survivorship note (every symbol ever scanned stays in the DB; the API's historical depth limit is recorded and disclosed on every backtest report).
- Output: a written report per run stating what was tested, the config hash, and explicitly which signals showed **no** predictive value. Null results are kept, not buried.

## 17. Testing strategy

- **Unit tests** (pytest): recorded, scrubbed JSON fixtures from the real API for every parser/classifier; every validation rule has a poisoned-fixture test (duplicate, canceled, crossed quote, split day…).
- **Property tests** (hypothesis) for clustering: permutation invariance, tolerance monotonicity (bigger ε never yields more zones), no print assigned to two zones.
- **Golden-file tests** for scoring: fixed fixture day → exact expected scores; any weight change forces a deliberate golden update in the same PR.
- **Integration tests**: full nightly pipeline against a mock API server (respx/httpx) replaying a recorded day; asserts DB end-state, scanner rows, alert dedup behavior.
- **Backtest self-test**: a synthetic dataset with a planted known edge (and a planted look-ahead trap) — the engine must find the edge and must *not* profit from the trap.
- CI: GitHub Actions running lint (ruff), type-check (mypy), tests on every push.

## 18. Security checklist

- API token, SMTP creds only in `.env` (gitignored); loaded via `pydantic-settings`; a `.env.example` with placeholders is committed instead.
- Structured logging (structlog) with a redaction processor — `Authorization` headers and any env-named secret can never appear in logs or exceptions.
- Recorded test fixtures scrubbed of tokens before committing.
- Dashboard talks only to our FastAPI; the UW token never reaches the browser.
- Docker: non-root users, internal network for DB/Redis (no published ports except the two UIs), pinned image digests.
- Dependency pinning via `uv` lockfile; `pip-audit` in CI.
- Rate-limit budget guard so a bug can't hammer the API (circuit breaker after repeated 429s).
- No credentials in screenshots/docs — documentation uses the placeholder `UW_API_TOKEN=***`.

## 19. Implementation phases

- **M0 — Scaffold (first PR):** repo layout, Docker Compose (TimescaleDB + Redis + backend + web stub), config system, CI, migrations (alembic).
- **M1 — Ingest & trust:** UW client, discovery + deep fetch, raw storage, validation layer, quality log. Plus the three probes: historical-depth walker, NBBO-timing experiment, float-availability check. *Exit criteria: 2 weeks of clean prints for the watchlist, schema-parity fixtures recorded.*
- **M2 — Enrich & classify:** candles/VWAP/ATR/prior-day levels, symbol stats, per-print classification. *Exit: tape view queryable with correct buckets on fixture day.*
- **M3 — Zones & inference:** clustering, zone status tracking, evidence ledger, scoring. *Exit: NVDA-style ticker-day matches the provider's price-levels endpoint within tolerance; golden scores locked.*
- **M4 — Scanner, alerts, reports:** ten categories, alert bus + email digest, Phase-12 per-ticker report (markdown + JSON) generated nightly.
- **M5 — Dashboard:** three pages + tape + glossary tooltips.
- **M6 — Backtesting:** event store already populated since M3; build the engine, run the first honest study, publish results (including nulls) into the dashboard.
- **M7 — Intraday upgrade:** websocket `off_lit_trades` (or 30–60s polling fallback), FastAPI WebSocket push to the dashboard, intraday alert cooldowns, true intraday backtest horizons from then on.

## 20. Folder structure

```
mUkz/
├── docker-compose.yml
├── .env.example
├── config/
│   └── settings.yaml          # every weight/threshold; hot-reloadable
├── backend/
│   ├── pyproject.toml
│   ├── alembic/               # migrations
│   ├── app/
│   │   ├── config.py
│   │   ├── client/uw_client.py
│   │   ├── models/            # pydantic + ORM models (print.py, zone.py, signal.py…)
│   │   ├── ingestion/
│   │   ├── validation/
│   │   ├── enrichment/
│   │   ├── analytics/         # classify.py, zones.py, inference.py, scoring.py
│   │   ├── scanner/
│   │   ├── alerts/
│   │   ├── backtest/
│   │   ├── reports/
│   │   ├── api/               # FastAPI routers
│   │   └── jobs/nightly.py    # the DAG
│   └── tests/
│       ├── fixtures/          # scrubbed recorded API responses
│       ├── unit/ · integration/ · property/
└── web/                       # Next.js dashboard
    └── src/{pages,components,lib}
```

## 21. First three files to build

1. **`backend/app/config.py`** — pydantic-settings: env secrets + YAML weights/thresholds, validated at startup. Everything downstream depends on it, and it enforces "no hard-coded keys" from commit one.
2. **`backend/app/client/uw_client.py`** — typed httpx client for `/darkpool/recent`, `/darkpool/{ticker}`, `/darkpool/{ticker}/price-levels`, stock candles/state: auth, retries with backoff, token-bucket rate limiting, timestamp pagination, structured errors. The only file that ever touches the network.
3. **`backend/app/models/print.py`** — the `DarkPoolPrint` pydantic model mirroring the verified schema (Section 3), with normalization (decimals, tz-aware timestamps) and the first validation rules — plus its fixture-based tests. This freezes our contract with the API before any analytics exist.

## 22. Verification

- Each milestone has explicit exit criteria (Section 19); nothing advances on "looks right".
- End-to-end check per run: `docker compose up` → trigger `jobs/nightly.py` against the mock API fixture day → assert DB state, scanner output, one alert, one rendered ticker report → then the same against the live API for the watchlist.
- Independent cross-checks: our zone aggregation vs UW's own `price-levels` endpoint; our current-price/VWAP vs the stock-state endpoint.
- Backtest engine validated by the planted-edge/planted-trap synthetic dataset before any real study is trusted.
- Every analytical claim in the UI traces to stored evidence rows — if the dashboard says "probable accumulation, 0.71", clicking it shows the exact ledger entries and the invalidation levels that would kill it.
