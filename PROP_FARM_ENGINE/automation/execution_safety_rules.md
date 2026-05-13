# Execution Safety Rules

The pre-trade gate and runtime kill switches. Every signal — manual,
semi-auto, or full-auto — must pass these gates before an order is
submitted.

These rules **override every other layer** of the system. If a gate
rejects a signal, the rejection is final for that signal.

---

## 1. Pre-Trade Gate (every signal)

Run as a single function. The first failing condition rejects the
signal with a `reason_code`. All rejections are logged.

```pseudo
function pre_trade_gate(signal, account_state, market_state, news_calendar) -> Decision:
    # 1. Account state
    if account_state.daily_state == "LOCKED":
        REJECT("daily_locked")
    if account_state.daily_state == "STOP_FOR_DAY":
        REJECT("stop_for_day")
    if account_state.daily_state == "A_PLUS_ONLY" and signal.grade != "A+":
        REJECT("a_plus_only")
    if account_state.trades_today >= account_state.mode.max_trades_per_day:
        REJECT("max_trades_per_day")
    if account_state.losses_today >= account_state.mode.max_losses_per_day:
        REJECT("max_losses_per_day")

    # 2. Risk
    if signal.risk_pct > account_state.mode.max_risk_per_trade:
        REJECT("exceeds_per_trade_cap")
    if signal.size_contracts > account_state.mode.max_contracts:
        REJECT("exceeds_contracts_cap")
    if account_state.open_correlated_risk_pct + signal.risk_pct > correlated_total_cap[mode]:
        REJECT("correlation_cap")
    if account_state.trailing_dd_buffer_pct < 0.05:
        REJECT("trailing_dd_critical")

    # 3. R:R
    if signal.projected_R_to_T1 < signal.setup_r_floor:
        REJECT("insufficient_rr")

    # 4. Regime / bias
    if market_state.regime not in signal.allowed_regimes:
        REJECT("regime_banned")
    if market_state.regime == "NEWS_RISK":
        REJECT("regime_news_risk")

    # 5. Time
    if not signal.timestamp.in_window(signal.allowed_time_windows):
        REJECT("time_of_day")

    # 6. Setup attempts
    if account_state.attempts_today[signal.setup] >= signal.setup_max_attempts:
        REJECT("setup_attempts_exhausted")

    # 7. News
    if news_calendar.high_impact_within(signal.timestamp, ±300s):
        REJECT("news_blackout_high")
    if news_calendar.medium_impact_within(signal.timestamp, ±120s):
        REJECT("news_blackout_medium")

    # 8. Behavioral
    last_loss = account_state.last_closed_loss
    if last_loss is not None and (signal.timestamp - last_loss.close_time).seconds < 300:
        REJECT("revenge_cooldown")
    if account_state.emotional_lock_active:
        REJECT("emotional_lock")

    # 9. Data integrity
    if market_state.feed.last_tick_age_seconds > 5:
        REJECT("stale_data")
    if market_state.spread_bps > 2 * market_state.spread_20d_median_bps:
        REJECT("spread_blowout")
    if market_state.exchange_connection != "OK":
        REJECT("exchange_disconnect")

    # 10. Order flow integrity
    if signal.of_classification == "UNKNOWN":
        REJECT("of_data_unknown")
    if signal.of_classification == "WARNING":
        REJECT("of_warning")

    return APPROVE
```

---

## 2. Rejection Reason Codes

| Code | Meaning |
|------|---------|
| `daily_locked` | Daily P/L hit hard stop |
| `stop_for_day` | Daily green-protection triggered |
| `a_plus_only` | Daily state requires A+ grade |
| `max_trades_per_day` | Trade count cap reached |
| `max_losses_per_day` | Loss count cap reached |
| `exceeds_per_trade_cap` | Risk % above mode cap |
| `exceeds_contracts_cap` | Size above contracts cap |
| `correlation_cap` | Total correlated risk would exceed cap |
| `trailing_dd_critical` | Less than 5% trailing DD buffer remaining |
| `insufficient_rr` | Projected R:R below setup floor |
| `regime_banned` | Current regime is banned for this setup |
| `regime_news_risk` | Regime is NEWS_RISK |
| `time_of_day` | Outside allowed window |
| `setup_attempts_exhausted` | This setup hit its daily attempt cap |
| `news_blackout_high` / `news_blackout_medium` | Inside news window |
| `revenge_cooldown` | < 5 min since last losing close |
| `emotional_lock` | Behavioral lock active |
| `stale_data` | Last tick > 5s old |
| `spread_blowout` | Spread > 2× 20d median |
| `exchange_disconnect` | Broker / exchange feed broken |
| `of_data_unknown` | Order flow data missing |
| `of_warning` | Counter-signal detected |

Every rejection writes a record:

```json
{
  "rejected_at": "2026-05-13T13:42:00Z",
  "setup": "01_liquidity_sweep_reversal",
  "instrument": "ES",
  "side": "SHORT",
  "grade": "A",
  "reason": "regime_news_risk",
  "context": { "regime": "NEWS_RISK", "next_event": "FOMC at 14:00 ET" }
}
```

---

## 3. Order Submission Rules

If the gate approves:

| Rule | Value |
|------|-------|
| Order type | **Bracket only** — entry + stop + T1 limit submitted atomically |
| Time-in-force (entry) | DAY if RTH, GTC if ETH-permitted setup |
| Time-in-force (stop / target) | DAY |
| Slippage cap | Reject fill if slippage > 1 tick (ES) / 2 ticks (NQ) |
| Partial fill policy | Cancel and re-submit if partial < 100% within 2s |
| OCO link | T1 limit and stop must be OCO-linked |
| Max submit latency | 1 second from gate-approve to broker-ack |

**No naked positions are allowed.** If the bracket fails to submit
fully, cancel the entry immediately.

---

## 4. Runtime Kill Switches

These run **continuously** in the background. Any fire triggers
account-wide halt: cancel all pending entries, manage open positions
at original stops/targets only, no new entries.

| Kill switch | Trigger |
|-------------|---------|
| `LATENCY_KILL` | Median order-submit latency > 1s for the last 5 trades |
| `SPREAD_KILL` | Bid-ask spread > 3× 20d median for ≥ 60s continuously |
| `DATA_STALE_KILL` | Any feed > 10s stale |
| `BROKER_KILL` | Broker disconnect or order reject rate > 5% in last 10 orders |
| `DAILY_LOSS_KILL` | `LOCKED` state reached (daily P/L hard stop) |
| `NEWS_KILL` | Unscheduled news headline detected (heuristic: print rate > 3× 60-min avg + no scheduled event) |
| `MANUAL_KILL` | Operator hits the kill switch in the UI |

A kill switch fire is **non-resettable until the next session open**,
except `MANUAL_KILL` which the operator can release after acknowledging
a confirmation prompt.

---

## 5. Position Management Rules (runtime)

After a successful entry:

| Event | Action |
|-------|--------|
| T1 hit | Scale per setup (typically 50%); move stop to entry |
| T2 hit | Scale per setup (typically 30%); trail stop |
| Time stop reached without +1R | Exit at market |
| Invalidation signal (per setup § 8) fires | Exit remaining position at market |
| Daily P/L state escalates (e.g., to `A_PLUS_ONLY`) | Tighten existing stops to 0.5× original distance |
| Kill switch fires | Hold positions at current stops; do not exit at market unless `DATA_STALE_KILL` (then exit) |

---

## 6. Manual Override Policy

There are **no manual overrides** of:

- The pre-trade gate's REJECT decisions.
- `LOCKED` daily state.
- News blackout windows.

There **is** a manual override for:

- Submitting a signal at half the system's calculated size (subject to
  all gates passing).
- Closing an open position early (partial or full exit).
- Triggering `MANUAL_KILL`.

Any manual override is logged with operator ID and reason. Manual
oversizing or off-playbook entries are **prohibited** and counted as
behavioral violations (`risk/daily_loss_protection.md` § 5).

---

## 7. Audit Logging Requirements

For every signal, the system logs:

- Signal payload (per setup file § 12).
- Pre-trade gate decision + reason code.
- Order submit timestamp + broker ack timestamp.
- Fill prices + slippage.
- Every position management event (T1, T2, stop move, trail update).
- Exit reason + R realized.

Logs are immutable, append-only, written to disk synchronously before
any further trade action.

---

## 8. Daily Sanity Checks (start of session)

The engine runs these at 09:25 ET. Failure = stand down for the day.

| Check | Pass condition |
|-------|----------------|
| Account equity matches broker | Within $1 |
| Account mode loaded | mode != null |
| All pending orders from prior session cleared | 0 stale orders |
| Bias output present | classification != null |
| Regime classifier present | regime != null |
| Footprint feed connected | feed.connected == true |
| News calendar fetched | latest event ≤ 24h old |
| Levels computed | PDH, PDL, VAH, VAL, VPOC all populated |
| Trailing DD buffer | > 30% |
| Kill switches | all in OK state |

---

## 9. Pseudocode — Full Pre-Trade Path

```
function evaluate_signal(signal):
    decision = pre_trade_gate(signal, account_state, market_state, news_calendar)
    if decision != APPROVE:
        log_rejection(signal, decision.reason)
        return

    order = build_bracket_order(signal)
    ack = broker.submit(order)
    if not ack.ok:
        log_failure(signal, ack)
        return
    if not ack.fully_filled_within(2s):
        broker.cancel(order)
        return

    open_positions.add(Position.from(signal, ack))
    journal.log_entry(signal, ack)
```

---

## 10. Maintenance

The pre-trade gate is the **most critical** automation component. Any
change requires:

1. Unit tests covering each rejection code.
2. Replay test over the prior 100 sessions (does the new gate change
   decisions on historical signals?).
3. 2-week paper trade with the new gate.
4. Documented review.

No mid-week changes to the pre-trade gate.
