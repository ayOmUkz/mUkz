"""Top-down sector engine.

Ranks GICS sectors by:
    * 1-month relative performance vs benchmark
    * Volume expansion vs trailing 30-day average (institutional interest proxy)
    * Relative strength of sector ETF vs benchmark

Composite score is a weighted blend, rescaled to [0, 100].
"""

from __future__ import annotations

import logging
from typing import Iterable

import pandas as pd

from .config import SectorEngineConfig, UniverseConfig
from .data_sources import DataSource
from .indicators import (
    normalize_min_max,
    period_return,
    relative_strength,
    volume_expansion_ratio,
)
from .models import SectorScore

logger = logging.getLogger(__name__)


class SectorEngine:
    def __init__(
        self,
        data_source: DataSource,
        universe: UniverseConfig,
        config: SectorEngineConfig,
        history_days: int,
    ) -> None:
        self._data = data_source
        self._universe = universe
        self._config = config
        self._history_days = history_days

    def rank(self) -> list[SectorScore]:
        benchmark_history = self._data.get_history(
            self._universe.benchmark, self._history_days
        )
        if benchmark_history.empty:
            logger.warning("benchmark history empty for %s", self._universe.benchmark)
            return []

        rows: list[dict] = []
        for sector, etf in self._universe.sector_etfs.items():
            history = self._data.get_history(etf, self._history_days)
            if history.empty:
                logger.info("skipping sector %s: no history for %s", sector, etf)
                continue
            metrics = self._sector_metrics(history, benchmark_history)
            metrics.update({"sector": sector, "etf": etf})
            rows.append(metrics)

        if not rows:
            return []

        df = pd.DataFrame(rows)
        # Normalize each component to [0,1] then weighted blend, scaled to 0–100.
        df["n_rel_perf"] = normalize_min_max(df["relative_performance"])
        df["n_vol_exp"] = normalize_min_max(df["volume_expansion"])
        df["n_rel_str"] = normalize_min_max(df["relative_strength"])

        w = self._config.weights
        composite = (
            w.relative_performance * df["n_rel_perf"]
            + w.volume_expansion * df["n_vol_exp"]
            + w.relative_strength * df["n_rel_str"]
        )
        df["composite"] = (composite * 100.0).round(2)

        df.sort_values("composite", ascending=False, inplace=True)
        return [
            SectorScore(
                sector=row.sector,
                etf=row.etf,
                relative_performance=float(row.relative_performance),
                volume_expansion=float(row.volume_expansion),
                relative_strength=float(row.relative_strength),
                composite=float(row.composite),
            )
            for row in df.itertuples(index=False)
        ]

    def top_sectors(self, scores: Iterable[SectorScore]) -> list[str]:
        return [s.sector for s in list(scores)[: self._config.top_n_sectors]]

    # ------------------------------------------------------------------ helpers
    def _sector_metrics(
        self,
        history: pd.DataFrame,
        benchmark_history: pd.DataFrame,
    ) -> dict:
        close = _close_series(history)
        bench_close = _close_series(benchmark_history)
        volume = _volume_series(history)

        sector_ret = period_return(close, self._config.lookback_days)
        bench_ret = period_return(bench_close, self._config.lookback_days)
        rel_perf = (sector_ret - bench_ret) if pd.notna(sector_ret) and pd.notna(bench_ret) else float("nan")

        vol_exp = volume_expansion_ratio(
            volume,
            recent=max(5, self._config.lookback_days // 4),
            baseline=self._config.volume_lookback_days,
        )
        rs = relative_strength(close, bench_close, self._config.lookback_days)

        return {
            "relative_performance": _nan_to_zero(rel_perf),
            "volume_expansion": _nan_to_one(vol_exp),
            "relative_strength": _nan_to_one(rs),
        }


def _close_series(df: pd.DataFrame) -> pd.Series:
    if "Close" in df.columns:
        return df["Close"].astype(float)
    if "Adj Close" in df.columns:
        return df["Adj Close"].astype(float)
    return df.iloc[:, 0].astype(float)


def _volume_series(df: pd.DataFrame) -> pd.Series:
    if "Volume" in df.columns:
        return df["Volume"].astype(float)
    return pd.Series(dtype="float64")


def _nan_to_zero(x: float) -> float:
    return 0.0 if pd.isna(x) else float(x)


def _nan_to_one(x: float) -> float:
    return 1.0 if pd.isna(x) else float(x)
