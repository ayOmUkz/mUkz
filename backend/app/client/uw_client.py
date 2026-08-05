"""Typed client for the Unusual Whales public API.

This is the ONLY module that performs network I/O. Every endpoint here was
verified against the provider's OpenAPI documentation during planning
(docs/PLAN.md §1) — do not add endpoints without verifying path and
parameters first.

Design rules:

* The API token is injected as a header once and never appears in errors,
  logs, or ``repr``.
* A token-bucket budget caps requests per minute so a bug can never hammer
  the API; HTTP 429 responses are always respected (including Retry-After).
* Retries use exponential backoff for transient failures (429/5xx/network).
* Responses shaped ``{"data": [...]}`` are unwrapped transparently.
"""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Iterator
from typing import Any

import httpx
from pydantic import SecretStr

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class UWAPIError(Exception):
    """The API returned an unrecoverable error. Never contains the token."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class UWRateLimitError(UWAPIError):
    """Rate limited and retries were exhausted."""


class _TokenBucket:
    """Requests-per-minute budget (a sliding 60-second window)."""

    def __init__(self, requests_per_minute: int) -> None:
        self.rpm = requests_per_minute
        self._stamps: deque[float] = deque()

    def acquire(self) -> None:
        now = time.monotonic()
        while self._stamps and now - self._stamps[0] > 60.0:
            self._stamps.popleft()
        if len(self._stamps) >= self.rpm:
            time.sleep(max(0.0, 60.0 - (now - self._stamps[0])) + 0.01)
        self._stamps.append(time.monotonic())


class UWClient:
    """Synchronous Unusual Whales API client (the nightly pipeline is batch)."""

    def __init__(
        self,
        token: str | SecretStr,
        *,
        base_url: str = "https://api.unusualwhales.com",
        requests_per_minute: int = 100,
        max_retries: int = 4,
        backoff_seconds: tuple[float, ...] = (2.0, 4.0, 8.0, 16.0),
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        raw_token = token.get_secret_value() if isinstance(token, SecretStr) else token
        if not raw_token or raw_token == "***":
            raise ValueError("UW API token is missing (set UW_API_TOKEN in .env)")
        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {raw_token}", "Accept": "application/json"},
            timeout=timeout,
            transport=transport,
        )
        self._bucket = _TokenBucket(requests_per_minute)
        self._max_retries = max_retries
        self._backoff = list(backoff_seconds) or [2.0]
        self._sleep = time.sleep  # seam so tests never actually sleep

    def __enter__(self) -> UWClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def __repr__(self) -> str:  # never expose headers/token
        return f"UWClient(base_url={self._client.base_url!s})"

    def close(self) -> None:
        self._client.close()

    # ------------------------------------------------------------------ core

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        query = {k: v for k, v in (params or {}).items() if v is not None}
        last_status: int | None = None
        for attempt in range(self._max_retries + 1):
            self._bucket.acquire()
            try:
                response = self._client.get(path, params=query)
            except httpx.TransportError as exc:
                if attempt < self._max_retries:
                    self._sleep(self._backoff[min(attempt, len(self._backoff) - 1)])
                    continue
                raise UWAPIError(
                    f"GET {path} failed after {attempt + 1} attempts "
                    f"(network error: {type(exc).__name__})"
                ) from exc

            last_status = response.status_code
            if response.status_code in RETRYABLE_STATUS and attempt < self._max_retries:
                delay = self._backoff[min(attempt, len(self._backoff) - 1)]
                retry_after = response.headers.get("Retry-After")
                if retry_after is not None:
                    try:
                        delay = max(delay, float(retry_after))
                    except ValueError:
                        pass
                self._sleep(delay)
                continue

            if response.status_code == 429:
                raise UWRateLimitError(
                    f"GET {path} rate-limited after {attempt + 1} attempts", status_code=429
                )
            if response.status_code >= 400:
                raise UWAPIError(
                    f"GET {path} -> HTTP {response.status_code}: {response.text[:200]}",
                    status_code=response.status_code,
                )

            body = response.json()
            if isinstance(body, dict) and "data" in body:
                return body["data"]
            return body

        raise UWAPIError(f"GET {path} exhausted retries", status_code=last_status)

    # ------------------------------------------------- dark-pool endpoints

    def recent_darkpool_trades(
        self,
        *,
        date: str | None = None,
        limit: int = 200,
        min_premium: int | None = None,
        max_premium: int | None = None,
        min_size: int | None = None,
        max_size: int | None = None,
        min_volume: int | None = None,
        max_volume: int | None = None,
        order: str | None = None,
        order_by: str | None = None,
    ) -> list[dict[str, Any]]:
        """GET /api/darkpool/recent — the whole-tape discovery scan (limit ≤ 200)."""
        return self._get(
            "/api/darkpool/recent",
            {
                "date": date,
                "limit": limit,
                "min_premium": min_premium,
                "max_premium": max_premium,
                "min_size": min_size,
                "max_size": max_size,
                "min_volume": min_volume,
                "max_volume": max_volume,
                "order": order,
                "order_by": order_by,
            },
        )

    def ticker_darkpool_trades(
        self,
        ticker: str,
        *,
        date: str | None = None,
        newer_than: str | None = None,
        older_than: str | None = None,
        limit: int = 500,
        min_premium: int | None = None,
        min_size: int | None = None,
    ) -> list[dict[str, Any]]:
        """GET /api/darkpool/{ticker} — one page of one ticker's prints (limit ≤ 500)."""
        return self._get(
            f"/api/darkpool/{ticker}",
            {
                "date": date,
                "newer_than": newer_than,
                "older_than": older_than,
                "limit": limit,
                "min_premium": min_premium,
                "min_size": min_size,
            },
        )

    def iter_ticker_darkpool_trades(
        self,
        ticker: str,
        *,
        date: str | None = None,
        page_limit: int = 500,
        min_premium: int | None = None,
        min_size: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Walk ALL of a ticker's prints for a day via ``older_than`` pagination.

        The API returns prints newest-first; each next page asks for prints
        older than the last one seen. Every print is yielded exactly once
        (deduplicated on ``tracking_id`` + ``executed_at``).
        """
        seen: set[tuple[Any, Any]] = set()
        older_than: str | None = None
        while True:
            page = self.ticker_darkpool_trades(
                ticker,
                date=date,
                older_than=older_than,
                limit=page_limit,
                min_premium=min_premium,
                min_size=min_size,
            )
            if not page:
                return
            fresh = 0
            for row in page:
                key = (row.get("tracking_id"), row.get("executed_at"))
                if key in seen:
                    continue
                seen.add(key)
                fresh += 1
                yield row
            cursor = page[-1].get("executed_at")
            if fresh == 0 or len(page) < page_limit or cursor is None:
                return
            older_than = cursor

    def darkpool_price_levels(self, ticker: str, *, date: str | None = None) -> Any:
        """GET /api/darkpool/{ticker}/price-levels — provider's own per-price buckets.

        Used as an independent cross-check of our zone aggregation (plan §9).
        """
        return self._get(f"/api/darkpool/{ticker}/price-levels", {"date": date})

    # ------------------------------------------------------ stock endpoints

    def stock_state(self, ticker: str) -> dict[str, Any]:
        """GET /api/stock/{ticker}/stock-state — last price & volume."""
        return self._get(f"/api/stock/{ticker}/stock-state")

    def ohlc(
        self,
        ticker: str,
        candle_size: str,
        *,
        timeframe: str | None = None,
        date: str | None = None,
        end_date: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """GET /api/stock/{ticker}/ohlc/{candle_size} — price candles.

        ``candle_size`` ∈ 1m/5m/10m/15m/30m/1h/4h/1d/1w; responses cap at
        2500 bars. 1d/1w bars carry only a ``date`` (no start/end time).
        Field naming varies across the provider's surfaces (``open`` vs
        ``o``), so callers must go through
        :func:`app.enrichment.candles.normalize_candles`.
        """
        return self._get(
            f"/api/stock/{ticker}/ohlc/{candle_size}",
            {"timeframe": timeframe, "date": date, "end_date": end_date, "limit": limit},
        )

    def ticker_info(self, ticker: str) -> dict[str, Any]:
        """GET /api/stock/{ticker}/info — company/ticker metadata.

        Which float / shares-outstanding fields it actually carries is what
        the M1 float-availability probe measures (docs/PLAN.md §2).
        """
        return self._get(f"/api/stock/{ticker}/info")

    def company_splits(self, ticker: str) -> list[dict[str, Any]]:
        """GET /api/companies/{ticker}/splits — stock split history.

        Feeds the split/reverse-split detector so old dark-pool zones are
        re-scaled or invalidated instead of pointing at pre-split prices.
        """
        return self._get(f"/api/companies/{ticker}/splits")

    def short_screener(
        self,
        *,
        tickers: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict[str, Any]]:
        """GET /api/short_screener — short interest, float size, days-to-cover."""
        return self._get(
            "/api/short_screener", {"tickers": tickers, "limit": limit, "offset": offset}
        )
