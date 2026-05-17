---
name: dashboard-council
description: Dashboard Council Mode. Design or critique operator-facing surfaces (trading dashboards, command centers, journals, radar/intel views, pattern-recognition layouts) for decision speed and low cognitive load. Product Designer leads; CTO, COO, and Head Trader (if trading) convened. Default test - "tired operator at 2am." Use whenever building, redesigning, or reviewing a dashboard or UI.
---

# /dashboard-council

Operate per `COUNCIL.md` in **Dashboard Council Mode**. Product Designer leads.

## The frame (every dashboard decision must answer)

1. **What decision does this surface enable?** Name it in one sentence. If you can't, the dashboard is decoration.
2. **In how many seconds should it enable that decision?** Sub-2s for command-center / live trading. Sub-30s for daily ops. Sub-5min for weekly review.
3. **What cognitive load does it require?** Tired-operator test: can the 2am version of the operator act on this without re-reading?
4. **What does it intentionally NOT show?** A dashboard's value is what it cuts, not what it adds.

## Default council

- **Product Designer** — leads. Owns hierarchy, glance-ability, what to cut.
- **CTO** — owns data sources, refresh cadence, build cost.
- **COO** — owns the workflow the dashboard fits inside (no orphan dashboards).
- **Head Trader** — convened for trading dashboards. Decides what tape-reading data must surface.
- **Contrarian** — convened on any "let's add another widget" decision.

## Design principles (enforced)

- **One primary decision per view.** If a view enables three decisions, it enables zero.
- **Visual hierarchy = decision hierarchy.** The most important number is the largest. Period.
- **Default state must be useful.** Filters off, no scrolling, no clicks — there should already be signal.
- **Color is for meaning, not decoration.** Reserve red/green/yellow for state changes that demand action.
- **Numbers need context.** Raw values without comparison (vs. prior, vs. target, vs. benchmark) are noise.
- **Every panel must answer "so what?"** If a panel can't change a decision, kill it.

## Anti-patterns (kill on sight)

- Dashboards built before the operator has run the loop manually.
- Adding widgets because data is available, not because decisions require it.
- More than 7±2 distinct elements in a single view.
- Trading dashboards without invalidation levels visible.
- Journals that require typing more than 3 fields.
- "Pretty" over scannable.
- Refresh cadences faster than the decision cadence (CPU/eyeball tax for no value).

## Response format

Standard 7-section format from `COUNCIL.md`. **Council Breakdown** must explicitly include answers to the four frame questions above.
