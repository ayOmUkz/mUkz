"""The intraday collector (plan M7).

Polls ``/darkpool/recent`` every ``poll_seconds`` — the plan's sanctioned
fallback; the provider's websocket (``wss://api.unusualwhales.com/socket``,
channel ``off_lit_trades``) requires the Advanced plan and can replace the
poll loop later without touching anything downstream.

Each poll: store raw (idempotent), validate, store prints, classify new
prints on the fly against the latest *stored nightly* size distribution,
publish them to the live hub, and raise cooldown-guarded alerts for prints
of the configured class. Classification columns in the DB stay owned by
the nightly enrich job (single writer, deterministic re-runs); the
on-the-fly class here only drives alerts and the live feed.
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

import sqlalchemy as sa
from sqlalchemy.engine import Engine

from app.alerts.cooldown import CooldownStore
from app.analytics.classify import size_classification
from app.config import Settings
from app.db import alerts as alerts_table
from app.db import symbol_stats
from app.ingestion import store
from app.intraday.hub import LiveHub
from app.validation import validate_rows

CLASS_RANK = {"normal": 0, "elevated": 1, "unusual": 2, "extreme": 3}


class RecentSource(Protocol):
    def recent_darkpool_trades(self, **kwargs: Any) -> list[dict[str, Any]]: ...


class IntradayCollector:
    def __init__(
        self,
        engine: Engine,
        client: RecentSource,
        settings: Settings,
        hub: LiveHub,
        cooldowns: CooldownStore,
        *,
        now_fn=lambda: datetime.now(UTC),
    ) -> None:
        self._engine = engine
        self._client = client
        self._settings = settings
        self._hub = hub
        self._cooldowns = cooldowns
        self._now_fn = now_fn
        self._seen: set[tuple[Any, Any]] = set()
        self._stats_cache: dict[str, dict[str, Any] | None] = {}

    # ------------------------------------------------------------ helpers

    def _symbol_stats(self, conn, ticker: str) -> dict[str, Any] | None:
        if ticker not in self._stats_cache:
            row = conn.execute(
                sa.select(symbol_stats)
                .where(symbol_stats.c.ticker == ticker)
                .order_by(symbol_stats.c.as_of_date.desc())
                .limit(1)
            ).mappings().first()
            self._stats_cache[ticker] = dict(row) if row else None
        return self._stats_cache[ticker]

    # --------------------------------------------------------------- poll

    def poll_once(self) -> dict[str, Any]:
        cfg = self._settings.intraday
        now = self._now_fn()
        rows = self._client.recent_darkpool_trades(
            limit=cfg.batch_limit,
            min_premium=cfg.min_premium,
            min_size=cfg.min_size,
        )
        fresh = []
        for row in rows:
            key = (row.get("tracking_id"), row.get("executed_at"))
            if key not in self._seen:
                self._seen.add(key)
                fresh.append(row)

        alerts_fired = 0
        published = 0
        clean_count = rejected_count = 0
        if fresh:
            with self._engine.begin() as conn:
                store.store_raw(conn, fresh, ingested_at=now)
                result = validate_rows(fresh, as_of=now + timedelta(minutes=1))
                clean_count = len(result.clean)
                rejected_count = len(result.rejected)
                store.store_prints(
                    conn,
                    result.clean,
                    late_report_seconds=self._settings.location.late_report_seconds,
                    ingested_at=now,
                )
                store.log_rejections(conn, result.rejected, logged_at=now)

                for validated in result.clean:
                    print_ = validated.print
                    stats = self._symbol_stats(conn, print_.ticker)
                    size_class, size_pct, _ = size_classification(
                        size=print_.size,
                        premium=print_.premium,
                        pct_adv30=print_.pct_adv30,
                        stats=stats,
                        config=self._settings.size_classes,
                    )
                    message = {
                        "type": "print",
                        "ticker": print_.ticker,
                        "executed_at": print_.executed_at.isoformat(),
                        "price": float(print_.price),
                        "size": print_.size,
                        "premium": float(print_.premium),
                        "size_class": size_class,
                        "size_percentile": size_pct,
                    }
                    self._hub.publish(message)
                    published += 1

                    if CLASS_RANK[size_class] >= CLASS_RANK[cfg.alert_min_class]:
                        cooldown_key = f"intraday:{print_.ticker}:{cfg.alert_min_class}"
                        if self._cooldowns.acquire(
                            cooldown_key, cfg.alert_cooldown_minutes * 60
                        ):
                            conn.execute(
                                alerts_table.insert().values(
                                    rule="intraday_extreme_print",
                                    ticker=print_.ticker,
                                    as_of_date=now.date(),
                                    base_key=(
                                        f"intraday_extreme_print:{print_.ticker}:"
                                        f"{print_.tracking_id}"
                                    ),
                                    payload={
                                        "price": float(print_.price),
                                        "size": print_.size,
                                        "premium": float(print_.premium),
                                        "size_class": size_class,
                                    },
                                    created_at=now,
                                    delivered=["dashboard", "live"],
                                )
                            )
                            self._hub.publish({**message, "type": "alert",
                                               "rule": "intraday_extreme_print"})
                            alerts_fired += 1

        return {
            "fetched": len(rows),
            "new": len(fresh),
            "clean": clean_count,
            "rejected": rejected_count,
            "published": published,
            "alerts": alerts_fired,
        }

    # ---------------------------------------------------------- lifecycle

    async def run(self, *, stop_event: asyncio.Event) -> None:
        """Poll until stopped; API errors wait one interval and retry."""
        cfg = self._settings.intraday
        while not stop_event.is_set():
            try:
                await asyncio.to_thread(self.poll_once)
            except Exception:  # noqa: BLE001 — the loop must survive bad polls
                pass
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=cfg.poll_seconds)
            except TimeoutError:
                continue

    def run_forever_blocking(self, *, print_stats: bool = True) -> None:
        """Synchronous loop for the CLI runner."""
        cfg = self._settings.intraday
        while True:
            stats = self.poll_once()
            if print_stats:
                print(stats, flush=True)
            time.sleep(cfg.poll_seconds)
