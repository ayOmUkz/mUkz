# Daily Loss Protection — Circuit Breakers & Lockout

Prop firm accounts die from **one bad day**, not from slow attrition.
This file defines the circuit breaker logic that prevents a single
session from violating the daily loss limit or trailing drawdown.

These rules are enforced automatically by the execution engine and
must also be enforced manually in Phase 1 (manual playbook).

---

## 1. Daily P/L State Machine

The account is in exactly one state at any time during RTH:

| State | Daily P/L (in R) | Behavior |
|-------|------------------|----------|
| `OPEN` | 0 to –0.99R | Normal trading; all setups allowed per regime |
| `CAUTION` | –1R to –1.99R | **Single contract** only; reduce size to 1 contract regardless of formula |
| `A_PLUS_ONLY` | –2R to –2.49R | Only **A+ grade** signals; no A, B, or paper trades |
| `LOCKED` | ≤ –2.5R **OR** 3 losses today **OR** daily $ loss ≥ 3% equity | **No new entries.** Manage existing only |
| `GREEN_PROTECT` | ≥ +2R | Move all stops to +0.5R; continue with full rules |
| `STOP_FOR_DAY` | ≥ +3R OR daily $ gain ≥ 3% equity | No new entries; **lock the day's gain** |

The state is recomputed after every position close.

---

## 2. Trigger Logic (binding)

```
function update_daily_state(account):
    pnl_R     = account.session_realized_R + account.session_open_R_at_risk
    pnl_pct   = account.session_realized_pct
    losses    = account.session_losses_count
    consec    = account.consecutive_losses

    if pnl_R <= -2.5 OR losses >= 3 OR pnl_pct <= -3.0:
        state = LOCKED
    elif pnl_R <= -2.0:
        state = A_PLUS_ONLY
    elif pnl_R <= -1.0:
        state = CAUTION
    elif pnl_R >= 3.0 OR pnl_pct >= 3.0:
        state = STOP_FOR_DAY
    elif pnl_R >= 2.0:
        state = GREEN_PROTECT
    else:
        state = OPEN

    if consec >= 2: apply_tier_down()
    return state
```

---

## 3. State Transitions & Reset

- **Transitions are one-way during the session.** Once `A_PLUS_ONLY` is
  entered, you cannot return to `OPEN` even if P/L recovers above –2R.
  Recovery happiness is a known overtrading trap.
- **`LOCKED` is terminal for the day.** No new entries until next
  session open. Manage existing positions only.
- **Reset:** all states reset to `OPEN` at **18:00 ET** (CME session
  close) and re-evaluate at 09:30 ET next session open.

---

## 4. News-Window Circuit Breaker

Independent of P/L, the engine enters **`NEWS_LOCK`** state during the
windows defined in `prop_firm_risk_rules.md` § 5.

- `NEWS_LOCK` blocks new entries.
- Open positions tighten stops to 0.5× original distance.
- Exits at original targets remain in force.
- `NEWS_LOCK` releases at the post-event window expiry.

---

## 5. Behavioral Lockouts

The trader is in `EMOTIONAL_LOCK` state if any of:

| Trigger | Detection |
|---------|-----------|
| Rule override | Trader manually placed a trade rejected by the gate |
| Revenge entry | Trade opened within 5 min of a losing close |
| Oversize | Trade placed with > setup_max_size for the mode |
| Off-playbook | Trade taken on a setup not in `/playbook` |

`EMOTIONAL_LOCK` requires a **written journal entry** in
`journal/daily_trade_journal.md` explaining the violation **before**
any further trades that day. If the violation occurs twice in the same
session, the engine enters `LOCKED` for the rest of the day.

---

## 6. Trailing Drawdown Buffer (prop firm specific)

Prop firms typically enforce a **trailing maximum drawdown** measured
against the highest equity reached on the account. The engine
maintains a programmatic buffer:

```
function trailing_dd_check(account, prop_firm_rules):
    distance_to_dd = account.equity - prop_firm_rules.trailing_dd_threshold
    buffer_pct = distance_to_dd / account.starting_equity

    if buffer_pct < 0.30:        # less than 30% buffer remaining
        scale_size_multiplier = 0.5  # half size
    elif buffer_pct < 0.15:
        scale_size_multiplier = 0.25
    elif buffer_pct < 0.05:
        state = LOCKED               # protect the account
    else:
        scale_size_multiplier = 1.0
    return scale_size_multiplier
```

The size multiplier is applied **after** the position sizing formula,
not before.

---

## 7. Recovery Protocol

When the account exits `LOCKED` at next session open:

1. **Start in `CAUTION` state**, not `OPEN`. One contract max for the
   first 2 trades.
2. **Only A or A+ grades** for the first 4 trades of the new session.
3. **Mandatory weekly review** if `LOCKED` was hit ≥ 2 times in a
   rolling 5-session window.
4. **Tier-down** to next lower risk mode if `LOCKED` was hit twice in
   the rolling 5-session window (Scaling → Funded → Evaluation).

---

## 8. Override Policy

There is **no manual override** for `LOCKED` state. If the trader
attempts to place an entry during `LOCKED`, the engine logs the attempt
as a behavioral violation (counts toward `EMOTIONAL_LOCK`).

`A_PLUS_ONLY` and `CAUTION` are **also non-overridable** during the
session.

---

## 9. Programmatic Hook

The execution engine checks the daily state on **every** signal:

```
function check_daily_protection(signal, state, account):
    if state == LOCKED: REJECT(reason="daily_locked")
    if state == STOP_FOR_DAY: REJECT(reason="stop_for_day")
    if state == A_PLUS_ONLY and signal.grade != "A+": REJECT(reason="a_plus_only")
    if state == CAUTION: signal.size_multiplier = min(signal.size_multiplier, 1/account.formula_size)
    if state == GREEN_PROTECT: ensure_open_stops_at_least(0.5R_in_profit)
    return signal
```

---

## 10. Reporting

The daily journal (`journal/daily_trade_journal.md`) automatically logs:

- Highest state reached during the session.
- Number of entries blocked by each state.
- Number of rule-violation attempts.
- Whether tier-down was applied.

A session with ≥ 1 rule-violation attempt or ≥ 2 state escalations is
flagged for the weekly review.
