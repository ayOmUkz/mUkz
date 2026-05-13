# Premarket Checklist

Sequential daily prep routine. Run **every session** before 09:25 ET.
The output is a populated **Bias & Levels card** that drives the day's
trading decisions.

If any required item cannot be answered, the day is `STAND_DOWN`.

---

## Time: T-60 min (08:30 ET) — Calendar & Macro

- [ ] **News calendar** — list all HIGH and MEDIUM impact events for
      today, ET-tagged.
  - HIGH events today: __________
  - MEDIUM events today: __________
- [ ] **Earnings** — top SPX names reporting before open / after close
      that could move the index futures.
- [ ] **Overnight headlines** — any non-scheduled headline that has
      moved ETH price > 0.5%?
- [ ] **VIX close + change** — VIX vs 20d MA: ____ / ____  → multiplier: ____
- [ ] **Asia / London ranges** — print on chart for liquidity-pool
      reference.

---

## Time: T-45 min (08:45 ET) — Levels

Compute and chart:

- [ ] **PDH** = __________
- [ ] **PDL** = __________
- [ ] **Prior VAH** = __________
- [ ] **Prior VAL** = __________
- [ ] **Prior VPOC** = __________
- [ ] **ONH** = __________ (from 18:00 ET prior to 09:30 ET today)
- [ ] **ONL** = __________
- [ ] **Weekly H** = __________
- [ ] **Weekly L** = __________
- [ ] **Composite HVNs** (top 3) = __________
- [ ] **Composite LVNs** (top 3) = __________
- [ ] **Single prints** from prior session (price ranges): __________
- [ ] **Poor highs/lows** in last 5 sessions: __________
- [ ] **Unmitigated swings** > 5 bars old on 5m: __________

---

## Time: T-30 min (09:00 ET) — Overnight Inventory & Gap

- [ ] **ETH close vs ETH range** — upper 25% / middle 50% / lower 25%?
- [ ] **ETH CVD** — positive / neutral / negative?
- [ ] **Inventory classification:** Long / Balanced / Short → __________
- [ ] **RTH open price expectation** (last ETH print): __________
- [ ] **Gap vs prior value:** inside / outside-small / outside-large?
- [ ] **Open-type expectation:**
  - [ ] Open-Drive (overnight strong + directional)
  - [ ] Open-Test-Drive (overnight quiet → push at open)
  - [ ] Open-Rejection-Reverse (overnight extreme into known level)
  - [ ] Open-Auction (overnight balanced inside prior VA)

---

## Time: T-15 min (09:15 ET) — Bias Engine

Run `market_context/daily_bias_engine.md` § 4 component scoring:

| Component | Side | Points |
|-----------|------|-------:|
| HT trend (1h slope) | ____ | ____ |
| Overnight inventory | ____ | ____ |
| Gap classification | ____ | ____ |
| VA migration (last 3 sessions) | ____ | ____ |
| Liquidity-pool location | ____ | ____ |
| Open-type expectation | ____ | ____ |
| VIX environment | ____ | ____ |
| **Total bias score** | | ____ / 100 |

- [ ] **Classification:** LONG / SHORT / BALANCED / RANGE_EXP /
      MEAN_REV / STAND_DOWN → __________
- [ ] **Confidence:** ____ / 100
- [ ] **Stand-down check** — any of: VIX > 1.5× MA AND > 25, HIGH news
      in first 60 min, overnight range > 1.5× 20d AND no clear
      inventory, data quality flag?
      → Stand-down active? **Yes / No**

---

## Time: T-10 min (09:20 ET) — Regime Pre-Classification

Compute regime inputs:

- [ ] **ADX(14) on 1h** = ____  → trend if > 25
- [ ] **ATR(20) on 5m** = ____ vs 20-day avg ____  → ratio ____
- [ ] **Overnight range vs 20d median ATR** = ____  → expansion if > 1.25×

- [ ] **Pre-open regime guess:** TREND / BALANCE / VOL_EXP /
      LOW_VOL_CHOP / NEWS_RISK → __________
  - (Final regime classification runs every 5m post-open.)

- [ ] **Allowed setups today:** __________
- [ ] **Banned setups today:** __________

---

## Time: T-5 min (09:25 ET) — Account & System Sanity

- [ ] **Account equity** matches broker (within $1)? **Yes / No**
- [ ] **Active mode:** Evaluation / Funded / Scaling
- [ ] **Trailing DD buffer:** ____ % (must be > 30%)
- [ ] **Pending orders cleared from prior session?** Yes / No
- [ ] **Footprint / CVD feed connected?** Yes / No
- [ ] **News calendar loaded?** Yes / No
- [ ] **TradingView indicator loaded with all levels?** Yes / No
- [ ] **Kill switches all green?** Yes / No
- [ ] **Daily P/L state at session open:** OPEN (must be)

If any answer above blocks trading → **STAND_DOWN**.

---

## Final Card — Ready to Trade

```
DATE:        ________
INSTRUMENT:  ES / NQ (or both)
MODE:        ________
BIAS:        ________ (conf ____)
REGIME (pre): ________
ALLOWED:     ________
BANNED:      ________
KEY LEVELS (closest to current price):
  Above:     ________
  At/near:   ________
  Below:     ________
UNRUN POOLS: ________
NEWS WINDOWS (ET): ________
A+ PLAN:     ________ (which setup + which level)
STAND-DOWN?  Yes / No
```

The card is **read once** at 09:25 ET and **not changed during the
session**. The day's plan is set; intraday discretion is limited to
which qualifying signals to take, not which to invent.

---

## Post-Open Adjustment Window (09:30 – 09:45 ET)

After the first 15 minutes:

- [ ] **Opening range high (OR_H)** = ____
- [ ] **Opening range low (OR_L)** = ____
- [ ] **Open-type confirmed?** (matches expectation?) Yes / No
  - If no, **downgrade bias confidence by 20 points** until 10:30 ET.

After 10:30 ET (IB complete):

- [ ] **IBH** = ____ (note on chart)
- [ ] **IBL** = ____ (note on chart)
- [ ] **IB vs prior IB** (wider/narrower): ____  → influences regime

---

## End-of-Session Audit (16:00 ET)

- [ ] **Bias classification accuracy** (did the day match the
      classification?): Match / Partial / Miss
- [ ] **Regime stability** (how many regime transitions?): ____
- [ ] **Allowed setups taken / signaled:** ____ / ____
- [ ] **Banned setups taken (should be 0):** ____
- [ ] **STAND_DOWN respected?** Yes / No

These audits feed `journal/weekly_performance_review.md`.
