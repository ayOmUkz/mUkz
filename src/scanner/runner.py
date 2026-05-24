"""End-to-end scanner orchestrator.

Wires the four engines together so callers (CLI, notebook, or scheduler)
can run a full scan with a single function call.
"""

from __future__ import annotations

import logging
from dataclasses import asdict

from .config import ScannerConfig
from .data_sources import DataSource, YFinanceDataSource
from .models import Candidate, ScanResult, SectorScore
from .options_engine import OptionsEngine
from .ranking_engine import RankingEngine
from .sector_engine import SectorEngine
from .stock_engine import StockEngine
from .universe import resolve_universe

logger = logging.getLogger(__name__)


class ScannerRunner:
    def __init__(
        self,
        config: ScannerConfig,
        data_source: DataSource | None = None,
    ) -> None:
        self._config = config
        self._data = data_source or YFinanceDataSource(
            cache_ttl_minutes=config.data.cache_ttl_minutes,
            request_timeout=config.data.request_timeout_seconds,
        )
        self._sector = SectorEngine(
            self._data,
            config.universe,
            config.sector_engine,
            config.data.history_days,
        )
        self._stock = StockEngine(
            self._data,
            config.universe,
            config.stock_engine,
            config.data.history_days,
            lookback_days=config.sector_engine.lookback_days,
        )
        self._options = OptionsEngine(self._data, config.options_engine)
        self._ranking = RankingEngine(config.ranking)

    def run(
        self,
        tickers: list[str] | None = None,
        restrict_to_top_sectors: bool = True,
    ) -> ScanResult:
        # 1. Top-down — rank sectors.
        sector_scores = self._sector.rank()
        sector_strength = {s.sector: s.composite for s in sector_scores}
        top_sector_names = (
            set(self._sector.top_sectors(sector_scores))
            if restrict_to_top_sectors
            else None
        )

        # 2. Bottom-up — screen candidate universe.
        universe = resolve_universe(tickers, self._config.universe.default_tickers)
        logger.info("scanning universe of %d tickers", len(universe))

        passing_stocks, rejections = self._stock.screen(
            universe, allowed_sectors=top_sector_names
        )
        logger.info(
            "stock filter: %d / %d passed (%d rejected)",
            len(passing_stocks),
            len(universe),
            len(rejections),
        )

        # 3. Options mispricing — evaluate options on each survivor.
        candidates: list[Candidate] = []
        for stock in passing_stocks:
            snapshot = self._data.get_snapshot(stock.ticker, self._config.data.history_days)
            opt = self._options.evaluate(snapshot)
            if opt is None:
                logger.debug("%s: no options metrics", stock.ticker)
                continue
            ok, reason = self._options.passes_filters(opt)
            if not ok:
                logger.debug("%s rejected by options filter: %s", stock.ticker, reason)
                continue
            candidates.append(
                Candidate(
                    ticker=stock.ticker,
                    sector=stock.sector,
                    stock=stock,
                    options=opt,
                    sector_strength=sector_strength.get(stock.sector or "", 0.0),
                )
            )

        # 4. Rank.
        ranked = self._ranking.score(candidates)

        return ScanResult(
            sectors=sector_scores,
            candidates=ranked,
            universe_size=len(universe),
            filtered_size=len(ranked),
        )


def to_dict(result: ScanResult) -> dict:
    """Serializable view of a scan result, useful for JSON exports."""
    return {
        "sectors": [asdict(s) for s in result.sectors],
        "candidates": [_candidate_to_dict(c) for c in result.candidates],
        "universe_size": result.universe_size,
        "filtered_size": result.filtered_size,
    }


def _candidate_to_dict(c: Candidate) -> dict:
    return {
        "ticker": c.ticker,
        "sector": c.sector,
        "composite_score": c.composite_score,
        "momentum_score": c.momentum_score,
        "iv_cheapness_score": c.iv_cheapness_score,
        "liquidity_score": c.liquidity_score,
        "sector_strength_score": c.sector_strength_score,
        "stock": asdict(c.stock),
        "options": _serialize_options(c),
        "notes": c.notes,
    }


def _serialize_options(c: Candidate) -> dict:
    d = asdict(c.options)
    if d.get("expiry") is not None:
        d["expiry"] = d["expiry"].isoformat()
    return d


# Convenience entry point so callers can just ``run_scan()``.
def run_scan(
    config: ScannerConfig,
    tickers: list[str] | None = None,
    data_source: DataSource | None = None,
    restrict_to_top_sectors: bool = True,
) -> ScanResult:
    return ScannerRunner(config, data_source=data_source).run(
        tickers=tickers, restrict_to_top_sectors=restrict_to_top_sectors
    )


def _sector_table(scores: list[SectorScore]) -> list[dict]:
    return [asdict(s) for s in scores]
