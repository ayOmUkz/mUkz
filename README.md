# Dark Pool Intelligence Engine

Turns raw dark-pool prints from the Unusual Whales API into careful,
probabilistic market intelligence: where institutions *may* be accumulating or
distributing, which price levels *may* matter, which prints are genuinely
unusual — always with supporting evidence, contradicting evidence, a
confidence score, and explicit invalidation conditions.

**Guiding principle:** a dark-pool print never proves direction by itself.
Every trade has a buyer *and* a seller, and the tape does not say who
initiated. Nothing in this codebase labels a print bullish or bearish from
its size or location alone.

The full design — API assessment, field dictionary, architecture, scoring
formulas, backtesting methodology — lives in [`docs/PLAN.md`](docs/PLAN.md).

## Status

Milestones **M0** (scaffold + core contracts), **M1** (ingest & trust),
**M2** (enrich & classify), **M3** (zones & inference), **M4** (scanner,
alerts, reports) and **M5** (dashboard) are complete:

- `backend/app/config.py` — validated configuration: secrets from `.env`,
  every tunable weight/threshold from `config/settings.yaml` (unknown keys
  and weight sets that don't sum correctly fail at startup).
- `backend/app/client/uw_client.py` — the only module that touches the
  network: verified endpoints, retries with backoff, rate-limit budget,
  `older_than` pagination, token never appears in logs or errors.
- `backend/app/models/print.py` — the typed `DarkPoolPrint` contract with
  derived metrics (mid, spread, report delay, %ADV) and data-quality flags.
- `backend/app/db.py` + alembic `0001` — symbols, `raw_prints` (verbatim,
  never mutated), `prints` (validated only), `data_quality_log`,
  `api_probes`, `ingest_runs`; TimescaleDB hypertables when available.
- `backend/app/validation/` — the quality gate: fatal flags quarantine a
  print, quote problems only downgrade its `location_confidence`.
- `backend/app/ingestion/` — hybrid discovery + per-ticker deep fetch with
  idempotent re-runs, plus the three verification probes (historical depth,
  NBBO timing, float availability).
- `backend/app/enrichment/` — candles (shape-tolerant normalizer), session
  VWAP, ATR(14), prior-day levels into `symbol_days`; each symbol's rolling
  dark-print size distribution (median/MAD/percentiles) into `symbol_stats`.
- `backend/app/analytics/classify.py` — pure classification rules: size
  class vs the symbol's *own* history (cold-start notional fallback marked
  provisional), NBBO location bucket, Eastern-Time timing bucket, and
  hedged liquidity character. Location is a feature, never a verdict.
- `GET /tape?ticker=…&date=…` — the classified dark-pool tape (FastAPI).
- `backend/app/analytics/zones.py` — ATR-scaled 1-D clustering of
  elevated+ prints into zones, per-zone metrics, a 0–100 strength score
  with a visible component breakdown, and a daily-candle status machine
  (untested → tested → respected, broken → reclaimed) with events.
- `backend/app/analytics/inference.py` — the evidence ledger: items across
  independent source groups (dark-pool structure, price behavior, volume
  asymmetry; options confirmation arrives with M4 context), six-state
  verdicts, confidence hard-capped at 0.85, machine-generated invalidation
  conditions.
- `backend/app/analytics/scoring.py` + `analyze.py` — print significance,
  data quality (a multiplicative gate), trade relevance, DPSS; one
  immutable signal per ticker-day in `signals` (re-runs never rewrite
  history), plus the provider price-levels cross-check.

- `backend/app/analytics/context.py` — market/sector trend from stored
  candles; confirmation labels (market/sector/technically confirmed,
  conflicting, isolated). Context never creates a signal.
- `backend/app/scanner/` — the ten ranked categories, each row with a
  plain-English "why". Options-confirmed stays empty until evidence
  group D (options context) is wired — an empty category is honest.
- `backend/app/alerts/` — rule evaluation with DB-backed dedup, cooldowns
  and a per-symbol daily cap (Redis joins at the intraday upgrade), plus
  the one-email nightly digest.
- `backend/app/reports/` — the per-ticker Phase-12 report (JSON +
  markdown): summary, interpretation with both evidence columns, levels,
  scenario map, and one of the five verdicts. Never a guaranteed
  prediction.
- API: `GET /scan`, `GET /alerts`, `GET /report/{ticker}`, `GET /status`,
  `GET /symbol/{ticker}` (plus the tape).
- `web/` — the Next.js dashboard: overview (scanner + alerts + data-quality
  banner), symbol detail (price chart with zone/VWAP/invalidation lines and
  print markers, score breakdown, evidence side-by-side), and the tape —
  with plain-language glossary tooltips on every technical term.

Run it (with `.env` filled in):

```bash
cd backend
python -m app.jobs.ingest --backfill-days 14   # the M1 exit criterion
python -m app.jobs.probes                      # answers the plan §2 unknowns
python -m app.jobs.enrich --backfill-days 14   # M2: context + classification
python -m app.jobs.analyze --backfill-days 14 --crosscheck  # M3: zones + signals
python -m app.jobs.nightly                     # M4: the whole chain + alerts + reports
python -m app.jobs.report --ticker NVDA        # one Phase-12 report to stdout
uvicorn app.api.main:app --reload              # /tape /scan /alerts /report/{ticker}
```

Schedule `python -m app.jobs.nightly` after the close (cron / systemd
timer / Task Scheduler); every stage is idempotent, so re-runs are safe.

Or run everything with Docker:

```bash
cp .env.example .env && $EDITOR .env
docker compose up --build    # dashboard :3000, API :8000
```

Next: **M6 — Backtesting** (the signals table has been immutable since M3
precisely for this), then **M7 — Intraday** (websocket ingestion, Redis
cooldowns, options-flow evidence). Roadmap in `docs/PLAN.md` §19.

## Quickstart

```bash
cp .env.example .env          # then fill in UW_API_TOKEN
docker compose up --build     # TimescaleDB + Redis + backend (health: :8000/healthz)
```

Development without Docker:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e .[dev]
pytest -q                     # run the test suite
ruff check .                  # lint
```

## Layout

```
config/settings.yaml   every tunable knob (weights, thresholds, universe)
.env.example           secrets template — copy to .env, never commit .env
backend/               Python: client, models, config, (soon) pipeline
web/                   Next.js dashboard (arrives in milestone M5)
docs/PLAN.md           the approved design document
```

## Security

- No credentials in code, YAML, logs, or fixtures — secrets live only in
  `.env` (gitignored) and are wrapped in `SecretStr`.
- The dashboard never sees the API token; only the backend talks to the
  Unusual Whales API.
