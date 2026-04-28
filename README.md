# ACTUAL TRADES — Top-Down Trading Dashboard

A single-page command center that operationalises a top-down workflow
(**4H → 1H → 5M**) and refuses to let you execute unless the alignment rules
pass. Doctrine over discretion.

This is the **blueprint and skeleton** — pure HTML/CSS/JS, no build step,
no backend, no charts library. Drop it open in a browser.

---

## Three Questions

The page is wired to answer three questions, in order:

1. **What is the higher timeframe bias?**          → 4H card
2. **Where is the opportunity forming?**           → 1H card
3. **When do I execute?**                          → 5M card

You cannot answer question 3 until 1 and 2 are answered. The 5M card
is locked behind a state gate.

---

## Run

```bash
# from /home/user/mUkz
python3 -m http.server 8080
# → http://localhost:8080/
```

Or just open `index.html` directly — there is no build, no server requirement.

---

## File Map

| File         | Purpose                                                     |
| ------------ | ----------------------------------------------------------- |
| `index.html` | Semantic skeleton: 4H / 1H / 5M / output / rule engine      |
| `styles.css` | Design tokens (beige + ink + gold/blue/green TF colors)     |
| `app.js`     | State model, pure derivation, rule engine, DOM sync         |

---

## Doctrine Encoded in Code

The rules are not suggestions — they are gates. See `app.js`:

| Rule               | Source                                       |
| ------------------ | -------------------------------------------- |
| 4H aligned         | `align4H()` — bias set, structure consistent |
| 1H confirmed       | `align1H()` — sweep + BOS/ChoCH + POI tagged |
| 5M trigger         | `trigger5M()` — trigger + momentum/absorption + prices |
| Risk defined       | `riskOk()` — R:R ≥ 2.0, non-negotiable        |
| No news event      | manual — a human must clear it               |

Hard refusals built into the engine:

- **RANGE regime blocks all 1H trend setups.**
  Auction Market Theory: in balance, fade edges; do not chase.
- **Counter-bias structure invalidates 4H.**
  Bull bias + LH/LL structure ⇒ refuse. Bear bias + HH/HL ⇒ refuse.
- **R:R < 2 disables execution.**
  No exceptions, no manual override — change the trade, not the rule.
- **5M card is overlaid and locked** until the upper TFs are aligned.
  Removes the temptation to trade the entry candle.

---

## Trade State Machine

The body has a `data-trade-state` attribute that drives all gated styling.

```
INVALID  → no 4H bias / counter-structure
WAITING  → 4H ok, 1H still building
ARMED    → 4H + 1H aligned, missing trigger / risk / news
VALID    → all five rules clear, EXECUTE button live
```

Every CSS lock and pill color reads off this single attribute.

---

## Future Upgrade Path

Each upgrade is **additive** — the rule engine, state shape, and DOM contract
do not change.

| Capability               | Drop-in point                                                    |
| ------------------------ | ---------------------------------------------------------------- |
| TradingView charts       | Replace each `.card--{tf}` body with the TV widget iframe        |
| Live price feed          | `state.feed = new WebSocket(...)`, push into `evaluate()`        |
| Journal database         | Swap `localStorage` writer in `wireExecute()` for `fetch('/api/entries')` |
| News calendar gating     | Auto-tick `r_news` from a fetched economic calendar              |
| Multi-asset watchlist    | Promote `state` to `Map<market, state>`; header dropdown switches |
| Backtest replay          | Time-travel slider that drives `state` from logged ticks         |
| Auth / multi-user        | Wrap journal `fetch` in token; UI is unchanged                   |
| Signal / alert push      | After `evaluate()` resolves to `VALID`, fire a webhook           |

---

## Verification (manual smoke)

1. Open `index.html`. Status pill = `WAITING`. Execute disabled.
2. **Misalign block** — leave 4H bias unset, fill 1H + 5M. Status stays `INVALID`,
   5M overlay stays locked.
3. **Happy path** — set bias = Bullish, structure = HH/HL; on 1H toggle
   *Liquidity Swept = Yes*, set Structure Event = BOS, add a Liquidity tag and
   a POI tag; on 5M choose Sweep + reclaim, tick Momentum, fill Entry/Stop/TP
   so R:R ≥ 2; tick *No news event*. All five rules tick green, status flips
   to `VALID`, button enables.
4. **R:R guard** — push the TP closer so R:R < 2. `r_risk` un-ticks, button disables.
5. **Persistence** — click EXECUTE TRADE. Reload the page. Journal count
   reads ≥ 1; `localStorage.getItem("actualTrades.entries")` holds the snapshot.
6. **Regime override** — switch regime to RANGE while in a valid setup. `r_1h`
   un-ticks, status drops out of `VALID`.
7. **Responsive** — narrow window below 760px; layout collapses to one column.

---

## What This Is Not

- Not a charting tool. Use TradingView in a separate tab; embed later.
- Not a broker bridge. The EXECUTE button logs intent, not orders.
- Not a backtest engine. Forward journaling first; replay is a future upgrade.
- Not configurable. The rules are doctrine — change the code, not the UI.
