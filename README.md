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

Milestones **M0** (scaffold + core contracts) and **M1** (ingest & trust)
are complete:

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

Run it (with `.env` filled in):

```bash
cd backend
python -m app.jobs.ingest --backfill-days 14   # the M1 exit criterion
python -m app.jobs.probes                      # answers the plan §2 unknowns
```

Next: **M2 — Enrich & classify** (candles/VWAP/ATR, per-symbol size
distributions, print classification). Roadmap in `docs/PLAN.md` §19.

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
