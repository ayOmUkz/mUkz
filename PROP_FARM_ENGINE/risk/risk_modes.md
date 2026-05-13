# Risk Modes — Evaluation / Funded / Scaling

Three operational risk profiles. The active mode is set by the
`account_scaling_model.md` progression gates. The execution engine
enforces these caps on every entry.

---

## 1. Mode: EVALUATION

**Goal:** Pass the prop firm evaluation. Survival over profit.

| Parameter | Value |
|-----------|-------|
| Max contracts per trade | **1** |
| Per-trade risk | **0.5%** of starting equity |
| Daily loss limit (soft stop) | **1.5%** of equity (move to `A_PLUS_ONLY`) |
| Daily loss limit (hard stop) | **2.5%** of equity → `LOCKED` |
| Daily profit cap | Stop trading at **+2%** (lock the day's gain) |
| Max trades per day | **3** |
| Max losses per day | **2** |
| Allowed setups | All 5, but only **A+ and A** grades |
| News window | HIGH = no trade, MEDIUM = no trade |
| Time windows | 09:30 – 11:30 ET only (skip afternoon) |
| Setup-specific attempt cap | **1 per setup per day** |

**Rationale:** evaluation accounts have tight rules and tight rewards.
A single bad trade can fail the eval. We trade only the cleanest part
of the day, only the highest-grade signals, and we lock the win.

**Promotion to Funded:** see `account_scaling_model.md` § 3.

---

## 2. Mode: FUNDED

**Goal:** Generate consistent returns on the funded account while
respecting trailing drawdown.

| Parameter | Value |
|-----------|-------|
| Max contracts per trade | **2** |
| Per-trade risk | **0.75%** of equity |
| Daily loss limit (soft stop) | **2.0%** → `A_PLUS_ONLY` |
| Daily loss limit (hard stop) | **3.0%** → `LOCKED` |
| Daily profit cap | Move stops to +0.5R at +2R; no new entries at +3R |
| Max trades per day | **4** |
| Max losses per day | **3** |
| Allowed setups | All 5; A+, A, **and B at half size** |
| News window | HIGH = no trade, MEDIUM = no trade |
| Time windows | 09:30 – 15:30 ET (skip lunch chop 11:30–13:30 unless Setup 05) |
| Setup-specific attempt cap | **2 per setup per day** |

**Rationale:** funded accounts pay real money but have trailing
drawdown. We scale up slowly and add the second contract only after
the move-up gate is passed. We allow B-grade signals at half size to
maintain trade frequency.

---

## 3. Mode: SCALING

**Goal:** Scale contract size with proven expectancy while protecting
the equity high-water-mark.

| Parameter | Value |
|-----------|-------|
| Max contracts per trade | **4 – 8** (by sub-tier in `account_scaling_model.md` § 6) |
| Per-trade risk | **1.0%** of equity |
| Daily loss limit (soft stop) | **2.0%** → `A_PLUS_ONLY` |
| Daily loss limit (hard stop) | **3.0%** → `LOCKED` |
| Daily profit cap | Stops to +0.5R at +2R; no new entries at +3R |
| Max trades per day | **5** |
| Max losses per day | **3** |
| Allowed setups | All 5; A+, A, B at half size |
| News window | HIGH = no trade, MEDIUM = no trade |
| Time windows | 09:30 – 15:30 ET (full session per regime) |
| Setup-specific attempt cap | **2 per setup per day** |

**Scaling-mode sub-tiers** (from `account_scaling_model.md` § 6):

| Equity band | Max contracts |
|-------------|--------------:|
| $300k – $500k | 4 |
| $500k – $1M | 6 |
| $1M+ | 8 |

**Tier-down trigger:** any of expectancy < 0R, profit factor < 1.0,
max DD ≥ 5R, ≥ 2 locked sessions in last 5, or 2 consecutive losses.
On trigger, drop to Funded mode immediately.

---

## 4. Mode Comparison Table

| Parameter | Evaluation | Funded | Scaling |
|-----------|-----------:|-------:|--------:|
| Max contracts | 1 | 2 | 4 – 8 |
| Per-trade risk | 0.5% | 0.75% | 1.0% |
| Soft daily stop | 1.5% | 2.0% | 2.0% |
| Hard daily stop | 2.5% | 3.0% | 3.0% |
| Max trades/day | 3 | 4 | 5 |
| Max losses/day | 2 | 3 | 3 |
| Grades allowed | A+, A | A+, A, B(½) | A+, A, B(½) |
| Time window | AM only | Full RTH | Full RTH |
| News HIGH | No trade | No trade | No trade |

---

## 5. Per-Mode Profit Protection

| Mode | Action when daily P/L ≥ +2R | Action when daily P/L ≥ +3R |
|------|----------------------------|-----------------------------|
| Evaluation | Stop trading; lock the day | Stop trading; lock the day |
| Funded | Move all stops to +0.5R | No new entries; lock the day |
| Scaling | Move all stops to +0.5R | No new entries; lock the day |

Evaluation mode is **strictest** because a single 2-tick excursion
beyond the prop firm's profit target is the easiest evaluation win
available — don't give it back.

---

## 6. Programmatic Mode Selection

The engine loads the active mode at session open:

```
function load_active_mode(account_state):
    mode = account_state.current_mode    # set by scaling_model
    risk = risk_modes_table[mode]
    apply_caps(risk)
    return risk
```

Mode cannot be changed **intra-session** by manual action. Only the
`account_scaling_model.md` tier-down logic can change mode during a
session (and only downward).

---

## 7. Setup-Mode Compatibility Matrix

| Setup | Eval | Funded | Scaling |
|-------|:---:|:---:|:---:|
| 01 Liquidity Sweep Reversal | A+/A only | All grades | All grades |
| 02 Value Area Rejection | A+/A only | All grades | All grades |
| 03 80% Value Area Rule | A+/A only | All grades | All grades |
| 04 LVN Rejection | A+/A only | All grades | All grades |
| 05 Initiative Breakout | **Disabled in Eval** (trend regime requires wider context) | All grades | All grades |

Setup 05 is disabled in Evaluation because trend-regime breakouts
require room to breathe; the tight Evaluation stops violate the
setup's natural structure.

---

## 8. Versioning

Risk-mode parameters are reviewed quarterly. Mid-quarter changes
require a documented 30-trade backtest and 2-week paper validation.
