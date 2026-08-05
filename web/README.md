# Dashboard

Next.js (pages router, TypeScript, no CSS framework) — three pages backed
entirely by the FastAPI service. The Unusual Whales token never reaches the
browser; the dashboard only talks to our own backend.

- **Overview** (`/`) — scanner categories with plain-English "why" strings,
  the alert feed, and a data-quality banner (last run, clean vs quarantined).
- **Symbol detail** (`/symbol/NVDA`) — lightweight-charts daily chart with
  dark-pool zone lines, VWAP, invalidation levels and print markers; the
  score breakdown ("show your work"); bullish / bearish / contradictory
  evidence side by side; important levels and the scenario map; the tape.
- **Tape** (`/tape`) — the raw classified print table for any symbol.

Every technical term gets a plain-language tooltip from
`src/lib/glossary.ts` (hover anything dotted-underlined).

## Develop

```bash
npm install
npm run dev          # http://localhost:3000, expects the API on :8000
```

Set `NEXT_PUBLIC_API_URL` if the backend lives elsewhere. In Docker
Compose the `web` service builds and serves the production bundle.
