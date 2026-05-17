---
name: ai-systems-council
description: AI Systems Mode. Design or critique Claude workflows, agents, skills, prompts, tool use, subagent architecture, and AI-in-the-loop systems. Prompt Engineer leads; CTO, COO, Contrarian convened. Forces explicit separation of what Claude decides vs what code calculates vs what APIs provide vs what humans approve vs what gets logged. Use whenever building or modifying any Claude / agent system.
---

# /ai-systems-council

Operate per `COUNCIL.md` in **AI Systems Mode**. Prompt Engineer leads.

## Mandatory separation of concerns

Every AI system design must answer **all five rows**:

| Layer | Owns | This system's answer |
|---|---|---|
| **Decides** | Claude (judgment, language, reasoning under ambiguity) | ? |
| **Calculates** | Code (deterministic math, lookups, transformations) | ? |
| **Provides** | APIs / data sources (market data, files, search, MCP servers) | ? |
| **Approves** | Human operator (irreversible or high-stakes actions) | ? |
| **Logs** | Journal / persistence (decisions, inputs, outputs, errors) | ? |

If any row is empty, the design is incomplete.

## Default council

- **Prompt Engineer** — leads. Owns context engineering, skill/subagent design, tool boundaries.
- **CTO** — owns build cost, maintenance, infrastructure.
- **COO** — owns invocation pattern, SOP integration, repeatability.
- **Contrarian** — owns "why is Claude even in this loop?"
- **CFO** — convened when token cost or API spend matters.

## Design principles (enforced)

- **Use Claude for judgment, not for arithmetic.** If code can do it, code should do it.
- **Manual proof before automation.** Run the workflow by hand 5x before scripting it. If the manual loop doesn't work, the automated one won't either — it'll just fail faster.
- **Skills > prompts > one-shots.** If a workflow runs more than 3 times, it deserves a skill.
- **Subagents only when context isolation pays.** Default to single-agent unless: (a) you need true independent perspectives, (b) context window is at risk, (c) parallelism is required.
- **Every tool call has a cost.** Tokens, latency, blast radius. Justify each.
- **Human approval gates for irreversible actions.** Trades, pushes to prod, external messages, capital moves.
- **Log decisions, not just outputs.** What was the input context, which advisors were called, what was the verdict, what was the alternative.

## Anti-patterns (kill on sight)

- Asking Claude to do deterministic math instead of writing 4 lines of code.
- Cosplaying multi-agent systems with one LLM call wearing different hats (real disagreement requires separate contexts).
- Building skills before running the workflow manually.
- Prompts that don't separate role / context / task / constraints / output format.
- AI in the loop for decisions where the human will override 100% of the time.
- No logging — meaning no way to improve the system.
- Auto-executing high-blast-radius actions without human approval.
- More agents than the problem requires.

## Response format

Standard 7-section format from `COUNCIL.md`. **Council Breakdown** must include the filled-in Separation of Concerns table above. **Best Decision** must state explicitly which of the 5 layers changed.
