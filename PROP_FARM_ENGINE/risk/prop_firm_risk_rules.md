# Prop Firm Risk Rules — Hard Caps

These rules are **binding**. They override every setup grade, every
bias, and every order flow signal. The execution engine's pre-trade
gate (see `automation/execution_safety_rules.md`) enforces them
programmatically.

The order of precedence is:

1. Prop firm hard rules (this file).
2. Daily loss protection (`daily_loss_protection.md`).
3. Risk mode caps (`risk_modes.md`).
4. Setup-specific risk rules (per-setup file § 9).

If two rules conflict, **the tighter rule wins**.

---

## 1. Universal Hard Caps

| # | Rule | Value | Trigger |
|---|------|-------|---------|
| 1 | Max risk per trade | **1.0% of account equity** (Scaling mode max) | If proposed risk > cap → reject |
| 2 | Max daily loss (soft) | **2.0% of equity** | Switch to A+ only |
| 3 | Max daily loss (hard) | **3.0% of equity** | Lock out for the day |
| 4 | Max trailing drawdown buffer | **leave ≥ 30% buffer** to prop firm's trailing DD | Reduce size or stand down |
| 5 | Max trades / day | **4** | Reject the 5th trade entry |
| 6 | Max consecutive losses | **2** | Tier down to next risk mode (see § 4) |
| 7 | Max losing trades / day | **3** | Lock out for the day regardless of $ loss |
| 8 | Min time between trades | **5 minutes** | Reject entries within window of a closed trade |

---

## 2. Position Sizing Formula (binding)

```
contracts = floor( (equity × risk_pct) / (stop_ticks × tick_value) )

constraints:
    contracts >= 1   (else skip — risk too large for min size)
    contracts <= max_contracts[mode]
    contracts <= correlated_exposure_cap (see § 3)
```

**Tick values:**

- ES (E-mini S&P 500): **$12.50 / tick**, 0.25 pt
- NQ (E-mini Nasdaq):  **$5.00 / tick**, 0.25 pt

**Example (Funded mode, $50,000 account, ES, 8-tick stop):**

```
risk_$        = 50000 × 0.0075 = 375
risk_per_contract = 8 × 12.50  = 100
contracts     = floor(375 / 100) = 3
```

---

## 3. Correlation Exposure Cap

ES and NQ are highly correlated. When both setups fire same direction
within 5 minutes:

| 30-day corr | Rule |
|-------------|------|
| ≥ 0.9 | **Skip the second leg** entirely |
| 0.7 – 0.9 | Reduce second leg by **40%** (count as 0.6× exposure) |
| < 0.7 | Both legs full size |

Combined risk across correlated legs must still satisfy: total open
risk ≤ **1.5%** of equity at any time (Funded mode); 1.0% in
Evaluation; 2.0% in Scaling.

---

## 4. Loss-Streak Tier-Down

After **2 consecutive losses**, the trader tier-downs:

| Current mode | Tier-down → |
|--------------|-------------|
| Scaling | Funded |
| Funded | Evaluation |
| Evaluation | Stand down for the rest of the day |

Tier-down restores at the **next session open** if expectancy over the
prior 20 trades is positive (see `account_scaling_model.md`).

---

## 5. News Blackout Window

| Event severity | Pre-event window | Post-event window |
|----------------|------------------|-------------------|
| HIGH (FOMC, CPI, NFP, PPI, GDP) | 5 min | 15 min |
| MEDIUM (Retail Sales, PMI, Housing) | 2 min | 5 min |
| LOW | none | none |

During a blackout window:

- **No new entries.**
- Existing positions: continue with original stops/targets, **but**
  tighten stops to 0.5× original stop distance.
- Bracket-attached orders remain; pending entries are cancelled.

---

## 6. Behavioral Rules (no-go conditions)

The trader (or engine) must **not** trade if any of:

- A trade was closed at a loss within the last 5 minutes (revenge cooldown).
- The trader manually overrode a system rule today (rule violation → lockout).
- The setup grade is < B (insufficient quality threshold).
- The R:R to T1 is < the setup's stated R:R floor.
- The data feed is stale (last tick > 5s old).
- The execution platform spread is > 2× the 20-day median.

---

## 7. Profit Protection

| Trigger | Action |
|---------|--------|
| Daily P/L ≥ **+2R** | Move all open stops to **+0.5R** minimum |
| Daily P/L ≥ **+3R** | Stop opening new positions for the day |
| Open trade reaches +2R | Trail with the relevant setup's trail rule (per setup file § 7) |

The point: protect green days. A green day that flips red is the
single biggest expectancy killer in prop firm trading.

---

## 8. Account-Wide Hard Stops

Beyond per-trade and per-day rules, account-wide:

| Rule | Threshold | Action |
|------|-----------|--------|
| Weekly max loss | 5% of equity | Stop trading for the week |
| Monthly max loss | 8% of equity | Stop trading for the month, full performance review |
| Drawdown from peak | 6% (Funded), 4% (Evaluation) | Tier-down + 1-week review |

---

## 9. Programmatic Enforcement

The execution engine consumes this file as part of its pre-trade gate.
A pseudocode summary:

```
function pre_trade_gate(signal, account_state):
    if account_state.daily_loss_pct >= 3.0: REJECT(reason="hard_daily_loss")
    if account_state.daily_loss_pct >= 2.0 and signal.grade != "A+": REJECT(reason="soft_loss_aplus_only")
    if account_state.trades_today >= 4: REJECT(reason="max_trades_per_day")
    if account_state.losses_today >= 3: REJECT(reason="max_losses_per_day")
    if account_state.consecutive_losses >= 2 and not tier_down_applied: APPLY_TIER_DOWN()
    if signal.risk_pct > risk_modes[current_mode].max_per_trade: REJECT(reason="exceeds_per_trade_cap")
    if now_in_news_blackout(signal.timestamp): REJECT(reason="news_blackout")
    if account_state.time_since_last_close_min < 5 and last_trade.pnl_R < 0: REJECT(reason="revenge_cooldown")
    if data_feed.last_tick_age_s > 5: REJECT(reason="stale_data")
    if signal.projected_R_to_T1 < setup.r_floor: REJECT(reason="insufficient_rr")
    if signal.size > correlated_exposure_cap(): REJECT(reason="correlation_cap")
    return APPROVE
```

If any gate fails, the engine logs the rejection in the journal with
the reason code so post-session review can audit the system's
discipline.

---

## 10. Rule Changes

Hard rules in this file are changed **only** through:

1. A documented weekly review with statistical evidence.
2. A 30-trade backtest of the proposed change.
3. A 2-week paper trade with the new rule.

**No live changes mid-week.**
