# V1 Build Roadmap

The ordered build steps from **v0.1 (this spec)** to **v1.0
(controlled execution)**. Each step has a deliverable, an exit
criterion, and an estimated effort.

The roadmap aligns with `automation/automation_roadmap.md` phases.
Skipping a step is not allowed.

---

## v0.1 — Markdown Specification (this commit)

**Deliverable:** Complete playbook + risk + automation + journal +
roadmap as markdown files.

**Exit criterion:** All 28 files present, schema-conformant, reviewed
by operator.

**Status:** **COMPLETE** with this commit.

---

## v0.2 — TradingView Indicator (Phase 2)

**Effort:** 1–2 weeks.

**Deliverables:**

1. Pine v5 indicator implementing
   `automation/tradingview_indicator_logic.md`:
   - Level plotting (PDH/PDL/ONH/ONL/IBH/IBL/VAH/VAL/VPOC/HVN/LVN).
   - Setup 01 trigger detection + alert.
   - Setup 02 trigger detection + alert.
   - Setup 03 trigger detection + alert.
   - Order flow markers (delta divergence, absorption, footprint flip).
   - Bias panel (top-right table).
2. Webhook payload format matching each setup's § 12 schema.
3. Replay test report over 30 historical sessions: fire counts,
   true-positive estimate.

**Exit criterion:**

- Indicator runs without Pine CPU warnings.
- ≥ 70% true-positive rate on manual review of 30 fires per setup.
- Webhook delivery validated against a sample receiver.

**Build steps (ordered):**

1. Scaffold indicator + level plotting (no setup detection yet).
2. Add Setup 01 detector + alert.
3. Add order flow classification (delta + volume; full footprint in
   v0.3).
4. Add Setup 02 detector.
5. Add Setup 03 detector.
6. Add bias panel.
7. Replay test + true-positive audit.
8. Iterate parameters; commit final.

Setups 04 and 05 wait for v0.3 because they require richer LVN /
footprint logic.

---

## v0.3 — External Scanner & Alerter (Phase 2.5)

**Effort:** 2–3 weeks.

**Deliverables:**

1. Standalone service that receives TV webhooks and:
   - Validates the payload schema.
   - Logs every signal (approved + rejected) to a SQLite/Postgres
     store.
   - Forwards approved signals to Discord/Telegram with a one-click
     "approve" button (Phase 3 prep).
   - Runs the pre-trade gate from
     `automation/execution_safety_rules.md` (read-only — no orders).
2. Footprint feed integration (e.g., Sierra Chart, Bookmap API, or
   custom):
   - Per-bar delta, CVD, 3:1 imbalance flags.
   - Feed staleness watchdog.
3. Setup 04 and Setup 05 detection (now possible with richer LVN
   identification and footprint data).
4. Bias engine and regime classifier as nightly batch jobs writing
   to the journal store.

**Exit criterion:**

- 14 days of paper-mode operation with all 5 setups detecting and
  alerting.
- 0 schema validation failures.
- Footprint feed staleness < 5s for 99% of bar-close moments.
- Pre-trade gate rejection log readable + auditable.

---

## v0.4 — Semi-Auto Execution (Phase 3)

**Effort:** 3–4 weeks.

**Deliverables:**

1. Broker integration (Tradovate / Rithmic / Apex / TopstepX / etc.):
   - Bracket order submission (entry + stop + T1 OCO).
   - Position fetch on startup (crash recovery).
   - Order status webhook handler.
2. Position sizing live (per `risk/prop_firm_risk_rules.md` formula).
3. Pre-trade gate hard-enforced (no signal reaches the broker without
   approval).
4. Operator UI (web or Discord-button):
   - Approve / reject button per signal.
   - One-click size override (halve only — never increase).
   - Manual kill switch.
   - Account state dashboard (daily P/L, mode, DD buffer, kill state).
5. Position management:
   - T1 partial fill triggers stop-to-entry.
   - T2 trail logic.
   - Time-stop daemon.
   - Invalidation watchers per setup.

**Exit criterion:**

- 60 signals processed live (operator-approved on a funded account).
- 0 broker submission failures unhandled.
- Operator approval rate matches the system grade calibration
  (≥ 80% on A+, ≤ 40% on B).
- 4 weeks of stable operation.
- 20-trade rolling expectancy ≥ +0.4R.

---

## v0.5 — Auto-Execution of A+ Only (Phase 4)

**Effort:** 2–3 weeks (mostly hardening, not net-new code).

**Deliverables:**

1. Auto-submit path enabled **only for A+ grade** signals.
2. All circuit breakers and kill switches programmatically enforced
   (per `risk/daily_loss_protection.md` and
   `automation/execution_safety_rules.md`).
3. Lockout enforcement (no manual override of LOCKED state).
4. Daily report generator (PDF/email) summarizing trades, P/L,
   rejections, kill switches.
5. Crash-recovery validated: stop and restart the engine mid-session
   without losing positions or open orders.

**Exit criterion:**

- 60 days of Phase 4 live operation.
- 0 rule violations.
- 0 unintended kill-switch fires.
- Expectancy ≥ +0.5R over the window.

---

## v1.0 — Production Release

**Effort:** ongoing.

**Deliverables:**

1. Multi-account state management.
2. Risk dashboard across accounts.
3. Strategy performance tracker (live per-setup expectancy).
4. Account health monitor with email/SMS alerts on:
   - Trailing DD buffer < 30%.
   - LOCKED state hit.
   - Kill switch fire.
   - Tier-down applied.
5. Weekly performance review auto-populated.
6. Versioned playbook with parameter change history.

**Exit criterion:**

- 30 days of stable v1.0 operation.
- Every rule in `risk/prop_firm_risk_rules.md` enforced
  programmatically.
- Operator can demonstrate the system enforces each rule via test
  cases.

---

## Cross-Cutting Tasks (parallel to all versions)

| Task | Cadence | Output |
|------|---------|--------|
| Daily journal completion | Daily | Per-session file |
| Weekly performance review | Weekly (Sunday) | Per-week file |
| Quarterly threshold review | Quarterly | Updated parameters with backtest evidence |
| Replay test on parameter changes | Per change | 30-trade backtest before live |

---

## Risk-Aware Versioning

A version is **not** promoted if:

- The prior version had any rule violation in its exit-criterion
  window.
- The prior version had a `LOCKED` session not caused by an
  external/structural event.
- The operator cannot articulate every system behavior from the docs.

Rollback to the prior version is the **default response** to any
unexpected behavior.

---

## Tools & Stack (recommended)

| Layer | Choice |
|-------|--------|
| Indicator | Pine v5 on TradingView |
| Webhook receiver | Python/FastAPI or Node/Fastify |
| Broker integration | Tradovate API, Rithmic API, or platform-specific |
| Footprint feed | Sierra Chart bridge / Bookmap API |
| Storage | SQLite locally → Postgres at scale |
| Journal viewer | Static-site generator over markdown |
| Monitoring | Healthcheck endpoint + email alerts |

These are recommendations; the markdown spec is implementation-agnostic.

---

## Anti-Goals (intentionally NOT built in v1)

- **Strategy optimization frameworks.** No genetic algorithms, no
  walk-forward optimizers. Parameter changes are operator-decided
  with backtest evidence, not search.
- **High-frequency execution.** Bar-close decisioning only.
- **Cross-asset arbitrage.** ES and NQ only; no options, no other
  futures.
- **Discretionary overrides.** The system either executes the rule
  or stands down — no "trader feel" overrides.

---

## First Concrete Next Step

After this commit, **the first build task** is:

> **Convert Setup 01 (Liquidity Sweep Reversal) into the v0.2
> TradingView indicator** — level detection + sweep + reclaim + alert
> webhook. This is the most mechanically detectable setup and produces
> the cleanest first proof-of-concept for the full automation
> pipeline.

Why Setup 01 first:
1. It's the most documented and most automation-friendly.
2. Sweep detection is purely mechanical (level + buffer).
3. Reclaim is purely mechanical (close back through level).
4. It surfaces the most A+ opportunities in `BALANCE` regimes (the
   most common regime).
5. It tests the full pipeline: detection → grade → payload → webhook.

Once Setup 01 is reliably alerting in Phase 2, Setups 02 and 03
follow on the same scaffolding. Setups 04 and 05 wait for the v0.3
footprint integration.
