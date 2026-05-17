# mUkz — Claude Council

This repository is the Claude Council operating system.

**When working in this repo, load `COUNCIL.md` and treat it as system doctrine.**
That file defines the advisors, the response format, the rules, and the modes.
Skills in `.claude/skills/` are the delivery surface (`/council`, `/trading-council`, `/red-team`, `/dashboard-council`, `/ai-systems-council`).

## Hard rules in this repo
- Never modify `COUNCIL.md` without explicit operator instruction. It is the source of truth.
- New skills go in `.claude/skills/<name>/SKILL.md` with `description` frontmatter.
- Stateless v1 — no journal, no memory layer. Do not add one without operator sign-off.
- All council output follows the 7-section format in `COUNCIL.md` unless the operator asks for a single-line answer.

## Repo layout
```
COUNCIL.md              # operating doctrine — source of truth
CLAUDE.md               # this file — repo-level rules
.claude/skills/         # invocation surface
  council/              # /council — generic council on any question
  trading-council/      # /trading-council — Trading Council Mode
  red-team/             # /red-team — Red Team Mode
  dashboard-council/    # /dashboard-council — Dashboard Council Mode
  ai-systems-council/   # /ai-systems-council — AI Systems Mode
```
