"""Run the three M1 verification probes and store their results.

    python -m app.jobs.probes

Answers (into the ``api_probes`` table + stdout):
* how far back per-ticker dark-pool history goes,
* whether attached NBBO quotes are execution-time or report-time snapshots,
* which endpoints/fields actually expose float and shares outstanding.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from app.client.uw_client import UWClient
from app.config import load_config
from app.db import ensure_schema, make_engine
from app.ingestion.probes import run_all_probes
from app.ingestion.store import store_probe


def main() -> None:
    config = load_config()
    engine = make_engine(config.secrets.database_url)
    ensure_schema(engine)

    api = config.settings.api
    with UWClient(
        config.secrets.uw_api_token,
        base_url=api.base_url,
        requests_per_minute=api.requests_per_minute,
        max_retries=api.max_retries,
        backoff_seconds=tuple(api.backoff_seconds),
        timeout=api.timeout_seconds,
    ) as client:
        results = run_all_probes(client)

    now = datetime.now(UTC)
    with engine.begin() as conn:
        for name, result in results.items():
            store_probe(conn, name, result, ran_at=now)
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
