"""Configuration loading and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


class SectorWeights(BaseModel):
    relative_performance: float = 0.50
    volume_expansion: float = 0.25
    relative_strength: float = 0.25


class SectorEngineConfig(BaseModel):
    lookback_days: int = 21
    volume_lookback_days: int = 30
    top_n_sectors: int = 5
    weights: SectorWeights = Field(default_factory=SectorWeights)


class MomentumConfig(BaseModel):
    min_1m_return: float = 0.05
    require_above_20d_ma: bool = True
    require_above_50d_ma: bool = True
    min_relative_strength: float = 1.0


class MarketCapConfig(BaseModel):
    min_usd: float = 500_000_000
    max_usd: float = 3_000_000_000


class LiquidityConfig(BaseModel):
    min_avg_daily_volume: int = 500_000


class StockEngineConfig(BaseModel):
    momentum: MomentumConfig = Field(default_factory=MomentumConfig)
    market_cap: MarketCapConfig = Field(default_factory=MarketCapConfig)
    liquidity: LiquidityConfig = Field(default_factory=LiquidityConfig)


class IVRankConfig(BaseModel):
    max: float = 30.0
    lookback_days: int = 252


class OptionsLiquidityConfig(BaseModel):
    min_total_volume: int = 1_000
    min_open_interest_per_strike: int = 500
    max_bid_ask_spread_pct: float = 0.15


class ExpirationsConfig(BaseModel):
    min_dte: int = 20
    max_dte: int = 60


class OptionsEngineConfig(BaseModel):
    iv_rank: IVRankConfig = Field(default_factory=IVRankConfig)
    liquidity: OptionsLiquidityConfig = Field(default_factory=OptionsLiquidityConfig)
    expirations: ExpirationsConfig = Field(default_factory=ExpirationsConfig)


class RankingWeights(BaseModel):
    momentum: float = 0.40
    iv_cheapness: float = 0.30
    liquidity: float = 0.15
    sector_strength: float = 0.15

    @field_validator("momentum", "iv_cheapness", "liquidity", "sector_strength")
    @classmethod
    def _non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("ranking weights must be non-negative")
        return v


class RankingConfig(BaseModel):
    weights: RankingWeights = Field(default_factory=RankingWeights)
    top_n_results: int = 25


class UniverseConfig(BaseModel):
    benchmark: str = "SPY"
    sector_etfs: dict[str, str] = Field(default_factory=dict)
    default_tickers: list[str] = Field(default_factory=list)


class DataConfig(BaseModel):
    cache_enabled: bool = True
    cache_ttl_minutes: int = 60
    request_timeout_seconds: int = 30
    history_days: int = 400


class ScannerConfig(BaseModel):
    universe: UniverseConfig = Field(default_factory=UniverseConfig)
    sector_engine: SectorEngineConfig = Field(default_factory=SectorEngineConfig)
    stock_engine: StockEngineConfig = Field(default_factory=StockEngineConfig)
    options_engine: OptionsEngineConfig = Field(default_factory=OptionsEngineConfig)
    ranking: RankingConfig = Field(default_factory=RankingConfig)
    data: DataConfig = Field(default_factory=DataConfig)


def _default_config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "scanner.yaml"


def load_config(path: str | Path | None = None) -> ScannerConfig:
    target = Path(path) if path else _default_config_path()
    if not target.exists():
        return ScannerConfig()
    with target.open("r", encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f) or {}
    return ScannerConfig(**raw)
