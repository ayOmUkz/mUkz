"""Run the intraday collector standalone (Ctrl+C to stop).

    python -m app.jobs.intraday

For the live dashboard feed, prefer running the API with
``INTRADAY_ENABLED=1`` instead — the collector then shares the process
with the ``/ws/live`` websocket. This CLI is for headless collection.
"""

from __future__ import annotations

from app.alerts.cooldown import make_cooldown_store
from app.client.uw_client import UWClient
from app.config import load_config
from app.db import ensure_schema, make_engine
from app.intraday import IntradayCollector, live_hub


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
        collector = IntradayCollector(
            engine,
            client,
            config.settings,
            live_hub,
            make_cooldown_store(config.secrets.redis_url),
        )
        try:
            collector.run_forever_blocking()
        except KeyboardInterrupt:
            print("stopped")


if __name__ == "__main__":
    main()
