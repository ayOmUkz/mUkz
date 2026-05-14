# 03 · A+ SETUP PLAYBOOK
*Version: v0.1 · Last revised: 2026-05-13 · Owner: solo operator*

> The playbook is the **complete and exhaustive** list of what may be traded. If a chart pattern is attractive but not described here, it is not a setup — it is a story. The job of the operator is not to invent; it is to recognize.

---

## §1 How to read this file

Each setup is documented under the same 12 fields. Every field must be answerable for the trade to qualify under file 02 §7 checklist item 4 ("Entry trigger present").

| Field | Meaning |
|---|---|
| 1. **Name & one-line thesis** | The label used in the journal and the underlying market logic. |
| 2. **Day type filter** | Which day types (trend / balance / open-drive / open-rejection / failed-auction) the setup is valid on. |
| 3. **Context preconditions** | The structural facts (overnight inventory, value-area location, prior-day relationship) that must be true before the setup can fire. |
| 4. **Entry trigger** | The exact, observable event on the chart that makes the setup *fire*, not *forming*. |
| 5. **Stop location** | Where the written stop goes, by structure, not by ticks. |
| 6. **Targets** | TP1 and TP2 as structural levels. |
| 7. **R/R requirement** | Minimum reward-to-risk to TP1. |
| 8. **Position management** | Partial at TP1, BE move, runner trail rule, time stop. |
| 9. **Disqualifiers** | Conditions that look like the setup but kill it. If any is true, skip. |
| 10. **Frequency** | How often this setup is realistically expected per week. |
| 11. **Screenshot filename pattern** | The filename to use in `/screenshots/` so historical examples can be retrieved. |
| 12. **Notes & confirmations** | Optional auxiliary confirmations (delta, footprint, EMA alignment). These do not count as entry triggers. |

A setup with a missing field is not a tradeable setup. The promotion criteria in §6 explicitly require all 12 fields filled.

---

## §2 Setup A — Value Edge Reversal

**Type:** Mean-reversion into prior-day value.
**Frequency expectation:** 2–4 fires per week across ES + NQ combined.

### 1. Name & one-line thesis
**Value Edge Reversal.** Price overextends outside the prior session's value area, gets rejected at a structural edge (PD VAH or PD VAL), and reverts toward POC. The trade is the rejection, not the chase.

### 2. Day type filter
- **Tradeable:** Balance day, open-rejection, failed-auction.
- **Skip:** Trend day, open-drive (the trade is fading momentum that has just been confirmed as one-sided — bad idea).
- Day type is determined by the first 45 minutes per file 04 Routine 2.

### 3. Context preconditions
All four must be true:
1. Price has traded **outside** the prior day's value area in the direction of the proposed fade (above PD VAH for a short, below PD VAL for a long).
2. Price has reached or slightly exceeded a **named external reference** — ON High, ON Low, prior swing high/low, weekly VAH/VAL.
3. Volume profile of the current session shows **single prints** (TPO-style) or visibly thin volume in the excursion zone — i.e. the move was unauctioned.
4. There is **no displacement bar** in the direction of the excursion in the last 5 minutes before the trigger (a fresh displacement would mean fading momentum that just got confirmed — disqualifier).

### 4. Entry trigger
On the 1-minute (or chosen execution TF) chart:
- A bar **closes back inside** the prior day's value area after having traded fully outside it.
- The reclaim bar prints with **opposing delta** (sells on a short fade, buys on a long fade) of at least the bar's own range in delta terms.
- Entry is at the **close of the reclaim bar**, or on the first 1-tick pullback within 60 seconds. After 60 seconds, the trigger is stale.

### 5. Stop location
- Short: 2 ticks above the **highest tick** of the excursion (the wick of the sweep, not the body).
- Long: 2 ticks below the **lowest tick** of the excursion.
- Typical distance on ES: 6–14 ticks. On NQ: 18–40 ticks.
- If the structurally correct stop is wider than the per-trade dollar risk allows when sized down to 1 contract, **the trade does not happen.**

### 6. Targets
- **TP1:** Prior-day POC. Half off here.
- **TP2:** Opposite edge of the prior-day value area (PD VAL for a short, PD VAH for a long), or session POC if it has already migrated past PD POC. Runner.

### 7. R/R requirement
- **Minimum 1.5 R to TP1.** If the structural TP1 (PD POC) yields less than 1.5 R given the stop, skip.

### 8. Position management
- TP1 partial: 50 % off. Stop on remainder moves to break-even **plus 1 tick** (covers fees).
- Runner: trail behind each 5-minute swing pivot in the trade's direction.
- Time stop: if TP1 has not been touched within **20 minutes**, exit the full remaining position at market.

### 9. Disqualifiers
- A second sweep beyond the first within 90 seconds — implies acceptance, not rejection.
- Price was inside value at the open and only excursed for less than 5 minutes — the auction is too young.
- News blackout within 10 minutes (file 02 §6).
- Day type was confirmed trend in the open routine (file 04 Routine 2).
- The reclaim bar is a doji or has range less than the 20-bar average range × 0.7 — weak rejection.

### 10. Frequency
2–4 per week across both instruments combined. If averaging > 5/week, suspect over-identification; review on Sunday.

### 11. Screenshot filename pattern
`value_edge_reversal_<YYYY-MM-DD>_<instrument>_<L|S>_<TF>.png`
Example: `value_edge_reversal_2026-05-13_ES_S_1m.png`.

### 12. Notes & confirmations (optional)
- 9-EMA flat or curling in the trade direction on the 5-minute chart strengthens the case.
- Cumulative delta divergence at the excursion (price made a new extreme, delta did not).
- Order-flow footprint showing absorption (large limit prints at the wick).
- These do not by themselves trigger the trade; only the §4 trigger does.

---

## §3 Setup B — Liquidity Sweep Reclaim

**Type:** Stop-run reversal (Wyckoff spring / UTAD).
**Frequency expectation:** 1–3 fires per week across ES + NQ combined.

### 1. Name & one-line thesis
**Liquidity Sweep Reclaim.** Price runs through a well-known swing level where stops are sitting (ON High, ON Low, prior-day H/L, recent swing), fails to find acceptance beyond it, and reclaims the level with conviction. The trade is the reclaim, not the sweep itself.

### 2. Day type filter
- **Tradeable:** Open-rejection, failed-auction, late-trend exhaustion, balance day with a clean false-break.
- **Skip:** Strong, confirmed trend day in the **same direction as the sweep** (we do not fade trend continuation breakouts unless they sweep and reverse — which is, in fact, this setup; care here on day-type determination).

### 3. Context preconditions
All must be true:
1. The swept level is **named in pre-market notes** (file 04 Routine 1) — not improvised intraday.
2. The level has **stood for at least one full session** without being touched (or, if intraday, was identified ≥ 30 minutes before the sweep).
3. The sweep includes a **visible move beyond the level** (not just a tag); minimum 3 ticks on ES, 8 ticks on NQ, or more.
4. There is **no fundamental driver** (news, earnings, surprise) that would suggest the break is real.
5. Volume on the sweep bar is **above the 20-bar volume average**. Low-volume sweeps don't qualify.

### 4. Entry trigger
- A bar **closes back inside** the swept level (above for longs after a sweep below, below for shorts after a sweep above).
- The reclaim bar shows **opposing delta** at least 60 % of its range.
- A confirmation bar — the bar **after** the reclaim — must close in the trade direction (no new wick beyond the sweep). If the next bar wicks beyond, the trade is killed.
- Entry is at the **close of the confirmation bar** or on a 1-tick pullback within 60 seconds.

### 5. Stop location
- Short (sweep above): 2 ticks above the **sweep high**.
- Long (sweep below): 2 ticks below the **sweep low**.
- Typical: 8–18 ticks on ES, 25–55 ticks on NQ.
- Wider stops than the per-trade risk allows → 1 contract or skip.

### 6. Targets
- **TP1:** First structural level back in the prior range — most often the prior-day POC, prior session VWAP, or the opposite side of the visible balance.
- **TP2:** The opposite extreme of the immediately prior range (so a sweep of ON Low traded long targets ON High, with the assumption being a full inventory rotation).

### 7. R/R requirement
- **Minimum 2.0 R to TP1.** Higher than Setup A because of the wider stop and the additional confirmation bar (which slightly worsens entry).

### 8. Position management
- TP1 partial: 50 % off. Stop on remainder moves to break-even + 1 tick.
- Runner: trail behind each 5-minute swing pivot.
- Time stop: 30 minutes from confirmation-bar close. If TP1 not touched, exit at market.

### 9. Disqualifiers
- The level was swept earlier in the session and reclaimed once already — second sweep on the same level is usually the real break.
- The sweep coincides with a known news event (file 02 §6) — sweeps on news are not "liquidity hunts," they are reactions.
- Reclaim bar volume is below the 20-bar average — the move lacks participation.
- The confirmation bar makes a new high (for shorts) or new low (for longs) past the sweep.
- Day-type filter excludes (per §2 above).

### 10. Frequency
1–3 per week combined. Sweeps of high-quality, named levels are rarer than excursions.

### 11. Screenshot filename pattern
`liquidity_sweep_reclaim_<YYYY-MM-DD>_<instrument>_<L|S>_<TF>.png`
Example: `liquidity_sweep_reclaim_2026-05-13_NQ_L_1m.png`.

### 12. Notes & confirmations (optional)
- Wyckoff "spring" terminology applies to long entries after a sweep of support; "UTAD" for shorts after sweep of resistance.
- Delta divergence on the sweep (price new low, delta not).
- Footprint absorption: large limit prints into the wick.
- 21-EMA on 5-min reclaim adds confluence (price closes back across it).

---

## §4 Setup C — Initiative Breakout Through LVN

**Type:** Initiative continuation through a thin price zone (Auction Market Theory).
**Frequency expectation:** 1–3 fires per week.

### 1. Name & one-line thesis
**Initiative Breakout Through LVN.** Price approaches a clearly defined Low Volume Node, then displaces through it with conviction and continues. The trade is the displacement, not the approach. The thesis: LVNs are zones the market previously rejected as price discovery; revisiting them with strong order flow typically results in fast travel to the next HVN.

### 2. Day type filter
- **Tradeable:** Open-drive, trend day, breakout from balance to new range.
- **Skip:** Balance day inside developed value, open-rejection. Initiative through LVN inside an active rotation tends to fade.

### 3. Context preconditions
All must be true:
1. The LVN is **visible on the daily or composite volume profile** for the last 5–20 sessions — not a same-session micro-LVN.
2. Price has been **approaching from one side for at least 10 minutes** with progressively rising volume.
3. The 9-EMA and 21-EMA on the 5-minute chart are **aligned** in the direction of the proposed break (9 above 21 for longs; 9 below 21 for shorts).
4. There is **no opposing higher-time-frame level** (weekly VAH/VAL, prior-week extreme) within 1 R of the LVN in the trade direction — otherwise TP1 is too compressed.
5. Volume on the approach 5-minute bars is rising vs. the prior 5-minute bars (auction expanding, not contracting).

### 4. Entry trigger
- A single bar (1-minute) **closes beyond the LVN's far edge** with range ≥ 1.5 × the 20-bar average range — this is the displacement bar.
- Delta of the displacement bar is in the trade direction and ≥ 70 % of its range.
- Entry is at the **close of the displacement bar**. No retest entry — the trade is the displacement itself. If the close happens and a retest does not occur within 90 seconds, the entry is missed; do not chase later.

### 5. Stop location
- Long: at the **midpoint of the LVN** (where the displacement began).
- Short: at the **midpoint of the LVN** (where the displacement began).
- Typical: 10–25 ticks on ES, 30–80 ticks on NQ.
- If wider than per-trade risk allows: 1 contract, or skip.

### 6. Targets
- **TP1:** The nearest HVN beyond the LVN (the next dense volume node).
- **TP2:** The far edge of the next HVN, or a higher-time-frame structural level (weekly VAH/VAL, prior-week H/L).

### 7. R/R requirement
- **Minimum 1.5 R to TP1.** If TP1 (next HVN) is too close to satisfy 1.5 R, the LVN is not "real enough" — skip.

### 8. Position management
- TP1 partial: 50 % off. Stop on remainder moves to break-even + 1 tick.
- Runner: trail behind each 5-minute swing pivot in the direction of the trade.
- Time stop: 20 minutes from displacement-bar close.
- **Add-on rule:** None in v0.1. Adding to winners is intentionally **not** allowed yet; it will be considered for v0.2 after evidence accumulates.

### 9. Disqualifiers
- The "displacement" is actually a news spike — the bar after the spike often fades.
- Volume on the displacement bar is **below** the 20-bar average — appearance of size without actual size.
- 9-EMA / 21-EMA disagree on the 5-min frame.
- An opposing HTF level is within 1 R — TP1 is compressed; risk skewed.
- The LVN is intra-session only (less than 1 day of history) — too noisy.

### 10. Frequency
1–3 per week combined. Genuine initiative through real LVNs is rarer than balance-day rotations.

### 11. Screenshot filename pattern
`initiative_lvn_<YYYY-MM-DD>_<instrument>_<L|S>_<TF>.png`
Example: `initiative_lvn_2026-05-13_ES_L_1m.png`.

### 12. Notes & confirmations (optional)
- Cumulative session delta confirming direction.
- Footprint imbalances stacking on the displacement bar.
- Higher-time-frame trend on the 30-minute chart agreeing.

---

## §5 Cross-setup table (quick reference)

| Spec | Setup A: Value Edge Reversal | Setup B: Liquidity Sweep Reclaim | Setup C: Initiative Breakout LVN |
|---|---|---|---|
| Logic | Mean reversion | Stop-run reversal | Initiative continuation |
| Day types OK | Balance, open-rejection, failed-auction | Open-rejection, failed-auction, late-trend exhaustion | Open-drive, trend, breakout-from-balance |
| Trigger | Close back inside PD VA | Close back inside swept level + confirmation bar | Displacement bar through LVN |
| Stop | Beyond excursion wick | Beyond sweep wick | LVN midpoint |
| TP1 | PD POC | First structural level in prior range | Next HVN |
| TP2 | Opposite VA edge | Opposite extreme of prior range | Far side of next HVN / HTF level |
| Min R/R to TP1 | 1.5 R | 2.0 R | 1.5 R |
| Time stop | 20 min | 30 min | 20 min |
| Expected freq | 2–4/wk | 1–3/wk | 1–3/wk |

---

## §6 Promoting a setup from watchlist to live

A fourth (or later) setup can be added only by satisfying **all** of the following:

1. **20 paper-trade examples** of the setup over ≥ 8 weeks, logged with the same 17-field journal entries (file 05).
2. **All 12 fields** of this playbook fully written, before the first live attempt.
3. **Forward-tested win rate** of the paper sample ≥ the live win rate of the worst of A/B/C over the same window.
4. Average R/R on the paper sample ≥ 1.5.
5. Written justification of why the new setup is **distinct** from A/B/C — overlap with an existing setup is grounds for rejection.
6. Sunday-review approval in writing in two consecutive weekly review files.

Promotion is recorded with a version bump of this file and a brief addendum in the Sunday review entry of the promoting weekend.

---

## §7 Demoting / retiring a setup

A live setup is demoted to "observation only" (no live trades) if:

- Win rate on it falls below **35 %** over a rolling 20-trade window.
- Average R-multiple falls below **0.5 R** over the same window.
- A new disqualifier is discovered and the post-discovery sample (≥ 5 trades) shows the existing playbook misses it.

A demoted setup is reinstated only via the §6 promotion criteria, treating it as new.

---

## §8 Boilerplate — every setup obeys file 02

The rules in file 02 (Risk Constitution) apply to every setup in this file. In particular:

- The §7 12-item checklist must pass.
- Buffer-aware sizing (§3.4) reduces contract count even when the setup fires perfectly.
- News blackout (§6) overrides setup validity.
- No stop widening, no averaging, no second chance after a stop-out on the same level.

If file 03 ever appears to permit something file 02 forbids, file 02 wins.

---

*End of file 03.*
