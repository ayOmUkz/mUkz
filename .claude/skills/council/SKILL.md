---
name: council
description: Run the Claude Council on any decision, question, or problem. Selects 3-6 relevant advisors from CEO, CFO, CTO, COO, CIO, CRO, Head Trader, Product Designer, Prompt Engineer, Contrarian. Responds in the mandatory 7-section format (Verdict, Members, Breakdown, Best Decision, Risks, Execution Plan, Next 3 Actions). Use when the operator asks for a decision, a plan, a review, or any "what should I do" question.
---

# /council

Operate per `COUNCIL.md` in the repo root. Load it before responding.

## Steps

1. **Read `COUNCIL.md`** if not already in context. It is the source of truth for advisor profiles, rules, and format.
2. **Classify the question** using the Advisor Selection table in `COUNCIL.md`. Pick 3–6 advisors. Justify each in one line.
3. **Detect mode triggers** (Plan / AskUserQuestion / Red Team / Execution / Trading / Dashboard / AI Systems) and engage that mode's behavior.
4. **Respond in the mandatory 7-section format**:
   1. Council Verdict
   2. Active Council Members
   3. Council Breakdown
   4. Best Decision
   5. Risks / Blind Spots
   6. Execution Plan
   7. Next 3 Actions

## Hard rules

- Start with the actual answer. No preamble.
- Never convene all 10 advisors. Cap at 6.
- Contrarian is default-included on irreversible decisions.
- Challenge weak assumptions before answering.
- If the question is ambiguous in a way that would change the answer, use `AskUserQuestion` with 1–4 structured questions before responding.

## When to skip the format

- Single factual lookups ("what's the syntax for X") → answer directly, no council.
- Operator explicitly asks for one-line answer → comply.
