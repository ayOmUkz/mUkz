# Execution Engine — Pseudocode

The full end-to-end pseudocode for the future execution engine. This
file describes the **logical flow**, not the implementation language.
Concrete implementations (Python, TypeScript, Rust, …) follow this
spec.

---

## 1. Top-Level Structure

```
main():
    config        = load_config()
    market_state  = MarketState(config)
    account_state = AccountState(config.broker, config.account)
    journal       = Journal(config.journal_path)

    run_daily_sanity_checks(account_state, market_state)

    bias = compute_daily_bias(market_state, prior_session, ovnt)
    journal.log_daily_bias(bias)

    if bias.classification == "STAND_DOWN":
        notify_operator("Stand-down day; no trading.")
        return

    subscribe_market_data(["ES", "NQ"])
    subscribe_news_calendar()
    spawn_kill_switch_monitor()

    while session_open():
        event = next_event()
        match event:
            BAR_CLOSE:    on_bar_close(event, market_state, account_state, journal)
            TICK:         update_market_state(event, market_state)
            ORDER_UPDATE: on_order_update(event, account_state, journal)
            NEWS_EVENT:   on_news_event(event, market_state, account_state)

    run_session_close(account_state, journal)
```

---

## 2. Bar-Close Handler

```
function on_bar_close(bar, market_state, account_state, journal):
    market_state.regime = classify_regime(now(), market_state, news_calendar)
    market_state.update_levels(bar)

    # Only 5m and 30m bar closes drive setup detection
    if bar.timeframe == "5m":
        levels = market_state.session_levels
        lvns   = market_state.lvns

        setups = [
            (setup_01_trigger, {"levels": levels}),
            (setup_02_trigger, {"prior_levels": market_state.prior_session_levels}),
            (setup_04_trigger, {"lvns": lvns, "hvns": market_state.hvns}),
            (setup_05_trigger, {"lvns": lvns}),
        ]
        for fn, args in setups:
            signal = fn(market_state.bars_5m, market_state.bars_1m, **args, instrument=bar.instrument)
            if signal is not None:
                evaluate_and_submit(signal, market_state, account_state, journal)

    if bar.timeframe == "30m":
        signal = setup_03_trigger(
            market_state.bars_30m,
            market_state.rth_open,
            market_state.prior_VAH,
            market_state.prior_VAL,
        )
        if signal is not None:
            evaluate_and_submit(signal, market_state, account_state, journal)
```

---

## 3. Signal Evaluation & Submission

```
function evaluate_and_submit(signal, market_state, account_state, journal):
    # Grade
    signal.grade = grade_signal(signal, market_state, account_state)
    if signal.grade not in {"A+", "A", "B"}:
        journal.log_skipped(signal, "grade_below_threshold")
        return

    # Order flow tier already attached by detection. If WARNING, gate rejects.
    # Sizing
    signal.size_contracts = compute_size(signal, account_state, market_state)
    signal.risk_$         = signal.size_contracts × signal.stop_ticks × tick_value[signal.instrument]
    signal.risk_pct       = signal.risk_$ / account_state.equity

    # Apply regime size multiplier
    signal.size_contracts = max(1, floor(signal.size_contracts × market_state.regime_size_multiplier))
    if signal.size_contracts < 1:
        journal.log_skipped(signal, "size_too_small")
        return

    # B grade is half size
    if signal.grade == "B":
        signal.size_contracts = max(1, floor(signal.size_contracts × 0.5))

    # Pre-trade gate
    decision = pre_trade_gate(signal, account_state, market_state, news_calendar)
    if decision.status != "APPROVE":
        journal.log_rejection(signal, decision.reason_code)
        return

    # Bracket order
    bracket = build_bracket(signal)
    ack = broker.submit_bracket(bracket)
    if not ack.ok:
        journal.log_broker_failure(signal, ack)
        return

    # Wait for fill (2s)
    fill = broker.wait_for_fill(ack.order_id, timeout=2s)
    if fill is None or not fill.fully_filled:
        broker.cancel(ack.order_id)
        journal.log_no_fill(signal)
        return

    # Register the position
    pos = Position(
        signal=signal, fill=fill,
        stop_order_id=ack.stop_id, t1_order_id=ack.t1_id,
        opened_at=now(),
    )
    account_state.open_positions.add(pos)
    account_state.attempts_today[signal.setup] += 1
    account_state.trades_today += 1
    journal.log_entry(pos)
```

---

## 4. Position Sizing

```
function compute_size(signal, account_state, market_state):
    mode = account_state.mode
    risk_$        = account_state.equity × mode.max_risk_per_trade
    stop_ticks    = abs(signal.stop - signal.entry) / tick_size[signal.instrument]
    risk_per_ctr  = stop_ticks × tick_value[signal.instrument]
    contracts     = floor(risk_$ / risk_per_ctr)

    # Caps
    contracts = min(contracts, mode.max_contracts)

    # Correlation
    if has_open_correlated_position(signal, account_state):
        contracts = floor(contracts × correlation_multiplier(market_state.es_nq_corr_30d))

    # Trailing DD
    contracts = floor(contracts × trailing_dd_multiplier(account_state))

    return max(1, contracts)
```

---

## 5. Grading

```
function grade_signal(signal, market_state, account_state):
    points = 0
    if market_state.regime in signal.allowed_regimes
       AND market_state.regime not in signal.banned_regimes:
        points += 1
    if market_state.bias.side == signal.side AND market_state.bias.confidence >= 50:
        points += 1
    if has_multi_level_confluence(signal.level, market_state.session_levels):
        points += 1
    if signal.of_classification == "STRONG_CONFIRM":
        points += 1
    if signal.timestamp.in_prime_window():
        points += 1

    grade = {5: "A+", 4: "A", 3: "B"}.get(points, "skip")
    if signal.projected_R_to_T1 < signal.setup_r_floor:
        grade = "skip"
    return grade
```

---

## 6. Order Update Handler

```
function on_order_update(update, account_state, journal):
    pos = account_state.open_positions.find_by_order_id(update.order_id)
    if pos is None: return

    match update.type:
        FILLED_T1:
            scale_out(pos, pct=pos.signal.scale_t1, reason="T1")
            move_stop_to_entry(pos)
            journal.log_t1(pos)

        FILLED_T2:
            scale_out(pos, pct=pos.signal.scale_t2, reason="T2")
            trail_stop(pos, basis="last_5m_swing")
            journal.log_t2(pos)

        STOPPED:
            close_position(pos, reason="stop")
            journal.log_exit(pos)
            account_state.update_after_close(pos)

        TIME_STOP_TRIGGERED:
            broker.exit_market(pos)
            close_position(pos, reason="time_stop")
            journal.log_exit(pos)
            account_state.update_after_close(pos)

        INVALIDATION_SIGNAL:
            broker.exit_market(pos)
            close_position(pos, reason="invalidation")
            journal.log_exit(pos)
            account_state.update_after_close(pos)
```

---

## 7. Account State Updates After Close

```
function update_after_close(account_state, pos):
    pnl_R = pos.realized_R
    account_state.session_realized_R += pnl_R
    account_state.session_realized_pct += pos.realized_pct

    if pnl_R < 0:
        account_state.losses_today += 1
        account_state.consecutive_losses += 1
        account_state.last_closed_loss = pos
    else:
        account_state.consecutive_losses = 0

    # Recompute daily state machine
    new_state = update_daily_state(account_state)
    if new_state != account_state.daily_state:
        log_state_transition(account_state.daily_state, new_state)
        account_state.daily_state = new_state

    # Apply tier-down
    if account_state.consecutive_losses >= 2:
        apply_tier_down(account_state)
```

---

## 8. Kill Switch Monitor (background loop)

```
function kill_switch_monitor():
    while session_open():
        if median_latency_last_5_orders() > 1s:           trigger("LATENCY_KILL")
        if spread_above_3x_median_for(60s):               trigger("SPREAD_KILL")
        if any_feed_stale(10s):                           trigger("DATA_STALE_KILL")
        if broker_reject_rate_last_10() > 0.05:           trigger("BROKER_KILL")
        if account_state.daily_state == "LOCKED":         trigger("DAILY_LOSS_KILL")
        if unscheduled_news_heuristic():                  trigger("NEWS_KILL")
        sleep(1s)

function trigger(kill):
    log_kill(kill)
    broker.cancel_all_pending()
    notify_operator(kill)
    if kill == "DATA_STALE_KILL":
        broker.exit_market_all_open()
    halt_new_entries = true
```

---

## 9. News Event Handler

```
function on_news_event(event, market_state, account_state):
    if event.severity == "HIGH":
        # Block new entries from −5 min to +15 min
        market_state.news_lock_until = event.time + 15min
        # Tighten existing stops
        for pos in account_state.open_positions:
            broker.modify_stop(pos.stop_order_id,
                               new_distance=0.5 × pos.original_stop_distance)
        journal.log_news_window(event)
    elif event.severity == "MEDIUM":
        market_state.news_lock_until = event.time + 5min
```

---

## 10. Session-Close Routine

```
function run_session_close(account_state, journal):
    if any_open_positions():
        if config.close_at_session_end:
            for pos in open_positions: broker.exit_market(pos)
        else:
            notify_operator("Positions held overnight; review.")

    # Reset daily counters; persist rolling state
    snapshot = account_state.snapshot()
    journal.write_daily_summary(snapshot)
    journal.write_rejections_summary()
    journal.write_kill_switch_history()

    # Recompute scaling recommendation
    rec = compute_scaling_recommendation(account_state.rolling_20_trades)
    journal.write_scaling_rec(rec)

    # Send daily report
    send_email(generate_daily_report(snapshot, journal))
```

---

## 11. Data Structures (consolidated)

```
Signal {
    setup, side, instrument, grade,
    entry, stop, t1, t2, runner_target,
    swept_level: { name, price },         # setup 01
    of_classification, of_signals,
    allowed_regimes, banned_regimes,
    setup_r_floor, setup_max_attempts,
    scale_t1, scale_t2,
    size_contracts, risk_$, risk_pct,
    projected_R_to_T1, projected_R_to_T2,
    timestamp_utc,
}

Position {
    signal, fill_price, fill_size,
    stop_order_id, t1_order_id,
    opened_at, closed_at,
    realized_R, realized_pct,
    mfe_R, mae_R, exit_reason,
}

AccountState {
    equity, starting_equity_session, mode,
    session_realized_R, session_realized_pct,
    trades_today, losses_today,
    consecutive_losses, attempts_today: dict,
    daily_state, emotional_lock_active,
    open_positions: list[Position],
    last_closed_loss, trailing_dd_buffer_pct,
    rolling_20_trades: list[Position],
}
```

---

## 12. Performance & Reliability Targets

| Component | Target |
|-----------|--------|
| Bar-close → signal emit | < 500 ms |
| Signal → broker submit | < 1 s |
| Broker ack → fill | < 2 s (else cancel) |
| Journal write durability | fsync on each event |
| Kill switch reaction | < 1 s detect, < 2 s halt |
| Memory per symbol | last 200 × 5m + 600 × 1m bars |
| Crash recovery | resume open positions from broker on restart |
