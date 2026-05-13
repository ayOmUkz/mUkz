# A+ Setup Checklist — Pre-Trade Gate (manual)

Before clicking BUY or SELL — even when the system surfaces a signal —
the operator runs this checklist. Any unchecked box means **do not
trade**. This list mirrors the programmatic gate in
`automation/execution_safety_rules.md` and serves as the manual
backstop.

The whole list should take **≤ 30 seconds** at the chart.

---

## Universal 10-Box Pre-Trade Gate

- [ ] **1. Setup is in the playbook** — one of the 5 documented setups.
- [ ] **2. Setup is allowed in current regime** — not on today's
      banned list.
- [ ] **3. Time-of-day is in an allowed window** for this setup.
- [ ] **4. Daily bias aligns** with the trade side, **OR** the trade
      is a documented counter-bias A+ (see setup's § 10).
- [ ] **5. Order flow confirms** (MIN_CONFIRM for A/B, STRONG_CONFIRM
      for A+).
- [ ] **6. R:R to T1 ≥ 2.0R** (or 1.8R for Setup 02, 2.5R for Setup 03).
- [ ] **7. Stop placement is structural** — beyond the trigger
      extreme by the setup's buffer, not arbitrary.
- [ ] **8. Position size respects mode caps** (per `risk/risk_modes.md`).
- [ ] **9. Daily P/L state allows the entry** (not LOCKED / not
      A_PLUS_ONLY for non-A+).
- [ ] **10. No news event** within ±2 min (MEDIUM) or ±5 min (HIGH).

If all 10 are checked → **trade is approved**.
If any unchecked → **do not place the order.**

---

## Grade Confirmation (5-Box A+ Check)

For A+ grade specifically (per setup file § 10, plus universals):

- [ ] Multi-level confluence (≥ 2 levels at the entry zone).
- [ ] Daily bias confidence ≥ 50 AND aligned.
- [ ] STRONG_CONFIRM order flow (≥ 2 OF signals).
- [ ] Setup fires in 09:30–10:30 ET window (or setup-specific prime).
- [ ] Regime is in the setup's `allowed_regimes` list **clean**
      (not transitioning).

5/5 → **A+**.
4/5 → **A**.
3/5 → **B (half size)**.
≤ 2/5 → **skip**.

---

## Pre-Click Stop & Target Sanity

Before clicking:

- [ ] Stop is **at least** the setup's minimum buffer beyond the
      trigger extreme (Setup 01: 2 ES / 4 NQ ticks; Setup 02: 3/5;
      Setup 03: 4/8; Setup 04: 2/4; Setup 05: 2/4).
- [ ] Stop is **not arbitrary** (round-number stops are usually
      wrong).
- [ ] T1 corresponds to the setup's defined T1 location (not a guess).
- [ ] T2 corresponds to the setup's defined T2 location.
- [ ] R:R math checks: `(T1 - entry) / (entry - stop) ≥ R:R_floor`.

---

## Pre-Click Risk Sanity

- [ ] Account equity: $____________
- [ ] Mode-allowed risk %: ____  → risk-$ = $____
- [ ] Stop distance: ____ ticks
- [ ] Tick value: $____ (ES $12.50 / NQ $5.00)
- [ ] Computed size: ____ contracts
- [ ] Size cap for mode: ____ contracts → **min** of computed and cap
- [ ] B grade → halve size: Yes / No
- [ ] Correlated open exposure check: open exposure $____ + new $____
      ≤ correlated cap $____ ? Yes / No

---

## Pre-Click Behavioral Check

- [ ] **No revenge entry** — last losing close was > 5 min ago.
- [ ] **No fatigue trade** — operator is not on trade #5 of the day
      (cap is 4).
- [ ] **No FOMO trade** — the level was on the bias card this morning.
- [ ] **No off-playbook trade** — trigger sequence is documented.
- [ ] **No oversize** — the size matches the formula, not an inflated
      number.
- [ ] **Operator state** — calm, focused, not chasing.

If any behavioral box is unchecked → **walk away from the desk** for
5 minutes before re-evaluating.

---

## The 30-Second Sentence

After the checklist, the operator says one sentence aloud:

> "I am trading Setup ____ on ____ , entry at ____ , stop at ____ ,
>  T1 at ____ , size ____ contracts, risk ____% ,
>  because [one-sentence thesis]."

If the sentence can't be said cleanly, the trade is not yet ready.

---

## Post-Click

- [ ] Bracket order submitted (entry + stop + T1 atomically).
- [ ] T2 stored as a follow-up limit to be activated on T1 fill.
- [ ] Timer started for the time stop (15 min default; setup-specific
      values apply).
- [ ] Journal entry started (date, instrument, setup, grade, entry,
      stop, T1, T2, size, thesis sentence).
