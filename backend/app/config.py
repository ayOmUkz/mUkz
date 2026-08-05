"""Configuration for the Dark Pool Intelligence Engine.

Two sources, kept strictly separate:

* **Secrets** (API token, SMTP credentials, connection URLs) come from the
  environment / a local ``.env`` file and never appear in YAML, logs, or git.
* **Tunables** (weights, thresholds, universe) come from
  ``config/settings.yaml`` so every knob is reviewable and versioned.

Both are validated at startup: a missing token or a weight set that does not
sum to its required total fails loudly before any pipeline work begins.
"""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SETTINGS_PATH = "config/settings.yaml"


class Secrets(BaseSettings):
    """Values read from the environment (or a local .env file). Never logged."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    uw_api_token: SecretStr
    database_url: str = "postgresql+psycopg://darkpool:darkpool@localhost:5432/darkpool"
    redis_url: str = "redis://localhost:6379/0"

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: SecretStr | None = None
    alert_email_from: str | None = None
    alert_email_to: str | None = None


class StrictModel(BaseModel):
    """Base for YAML-backed models: unknown keys are an error, not a shrug."""

    model_config = ConfigDict(extra="forbid")


class UniverseConfig(StrictModel):
    watchlist: list[str] = Field(default_factory=list)


class DiscoveryConfig(StrictModel):
    min_premium: int = 1_000_000
    min_size: int = 5_000
    limit: int = Field(default=200, ge=1, le=200)  # API max for /darkpool/recent
    max_symbols_per_day: int = 150


class ColdStartNotional(StrictModel):
    """Fallback $-notional buckets while a symbol's own history is thin."""

    elevated: int = 1_000_000
    unusual: int = 5_000_000
    extreme: int = 20_000_000

    @model_validator(mode="after")
    def _ordered(self) -> ColdStartNotional:
        if not (0 < self.elevated < self.unusual < self.extreme):
            raise ValueError("cold-start notional buckets must be strictly increasing")
        return self


class SizeClassConfig(StrictModel):
    history_days: int = 60
    elevated_percentile: float = 90.0
    unusual_percentile: float = 99.0
    extreme_percentile: float = 99.9
    extreme_pct_adv30: float = 0.01
    extreme_pct_float: float = 0.0025
    min_history_prints: int = 200
    cold_start_notional: ColdStartNotional = Field(default_factory=ColdStartNotional)

    @model_validator(mode="after")
    def _percentiles_ordered(self) -> SizeClassConfig:
        ordered = (
            0.0
            < self.elevated_percentile
            < self.unusual_percentile
            < self.extreme_percentile
            < 100.0
        )
        if not ordered:
            raise ValueError("size-class percentiles must be strictly increasing, inside (0, 100)")
        return self


class LocationConfig(StrictModel):
    spread_tolerance: float = 0.10
    vwap_band_pct: float = 0.001
    late_report_seconds: int = 900


class ZoneEpsilonConfig(StrictModel):
    atr_mult: float = 0.25
    pct_of_price: float = 0.0015
    min_ticks: int = 2


class ZoneStrengthWeights(StrictModel):
    pct_adv30: int = 30
    recurrence: int = 20
    recency: int = 15
    tightness: int = 10
    concentration: int = 10
    reactions: int = 15

    @model_validator(mode="after")
    def _sums_to_100(self) -> ZoneStrengthWeights:
        total = sum(self.model_dump().values())
        if total != 100:
            raise ValueError(f"zone strength weights must sum to 100, got {total}")
        return self


class ZonesConfig(StrictModel):
    window_days: int = 20
    min_size_class: Literal["elevated", "unusual", "extreme"] = "elevated"
    epsilon: ZoneEpsilonConfig = Field(default_factory=ZoneEpsilonConfig)
    strength_weights: ZoneStrengthWeights = Field(default_factory=ZoneStrengthWeights)
    recency_half_life_sessions: int = 5
    respected_atr_mult: float = 0.5
    broken_atr_mult: float = 0.5
    reclaim_window_sessions: int = 3


class InferenceConfig(StrictModel):
    probable_net_weight: int = 4
    probable_min_items: int = 3
    possible_net_weight: int = 2
    possible_min_items: int = 2
    min_source_groups: int = 2
    # Hard cap below 1.0: this system is never certain, by design.
    confidence_cap: float = Field(default=0.85, gt=0.0, lt=1.0)


class DpssWeights(StrictModel):
    print: float = 0.25
    zone: float = 0.30
    direction: float = 0.25
    relevance: float = 0.20

    @model_validator(mode="after")
    def _sums_to_1(self) -> DpssWeights:
        total = sum(self.model_dump().values())
        if not math.isclose(total, 1.0, abs_tol=1e-9):
            raise ValueError(f"DPSS weights must sum to 1.0, got {total}")
        return self


class PrintSignificanceWeights(StrictModel):
    size_percentile: float = 0.40
    pct_adv30: float = 0.25
    character: float = 0.20
    timing: float = 0.15

    @model_validator(mode="after")
    def _sums_to_1(self) -> PrintSignificanceWeights:
        total = sum(self.model_dump().values())
        if not math.isclose(total, 1.0, abs_tol=1e-9):
            raise ValueError(f"print significance weights must sum to 1.0, got {total}")
        return self


class ScoringConfig(StrictModel):
    dpss_weights: DpssWeights = Field(default_factory=DpssWeights)
    print_significance_weights: PrintSignificanceWeights = Field(
        default_factory=PrintSignificanceWeights
    )
    etf_discount: float = Field(default=0.5, ge=0.0, le=1.0)


class AlertsConfig(StrictModel):
    min_dpss: int = 60
    cooldown_hours: int = 24
    max_alerts_per_symbol_per_day: int = 5
    email_digest: bool = True
    email_per_alert_min_class: Literal["elevated", "unusual", "extreme"] = "extreme"
    min_zone_notional: int = 50_000_000   # cumulative-notional alert threshold
    stale_sessions: int = 5               # directional signal with no refresh -> stale


class ScannerConfig(StrictModel):
    min_dpss: int = 40
    strong_zone_strength: int = 60        # "strong+" for reclaim/reject/level scans
    near_price_atr: float = 1.0           # "likely to matter today" distance
    approach_pct: float = 0.02            # historical zones within 2% of price
    recent_sessions: int = 2              # window for reclaim/reject events
    limit_per_category: int = 20


class ApiConfig(StrictModel):
    base_url: str = "https://api.unusualwhales.com"
    requests_per_minute: int = Field(default=100, ge=1)
    max_retries: int = Field(default=4, ge=0)
    backoff_seconds: list[float] = Field(default_factory=lambda: [2.0, 4.0, 8.0, 16.0])
    timeout_seconds: float = 30.0


class EnrichmentConfig(StrictModel):
    daily_history_days: int = 60   # daily candle window for ATR / prior levels
    atr_period: int = 14
    minute_candle_size: str = "1m"


class BacktestConfig(StrictModel):
    # Sessions after entry whose close is measured (entry = next session's
    # OPEN after the signal date — no look-ahead by construction).
    horizons: list[int] = Field(default_factory=lambda: [1, 3, 5, 20])
    bootstrap_samples: int = 1000
    seed: int = 7               # bootstrap is deterministic given the seed
    min_cohort_n: int = 5       # below this, a cohort is reported as "too thin"

    @model_validator(mode="after")
    def _horizons_valid(self) -> BacktestConfig:
        if not self.horizons or any(h < 1 for h in self.horizons):
            raise ValueError("horizons must be positive session counts")
        if sorted(self.horizons) != self.horizons:
            raise ValueError("horizons must be sorted ascending")
        return self

    @property
    def max_horizon(self) -> int:
        return self.horizons[-1]


class PipelineConfig(StrictModel):
    run_after_close_et: str = "17:30"
    timezone: str = "America/New_York"


class Settings(StrictModel):
    """The full, validated contents of config/settings.yaml."""

    universe: UniverseConfig = Field(default_factory=UniverseConfig)
    discovery: DiscoveryConfig = Field(default_factory=DiscoveryConfig)
    size_classes: SizeClassConfig = Field(default_factory=SizeClassConfig)
    location: LocationConfig = Field(default_factory=LocationConfig)
    zones: ZonesConfig = Field(default_factory=ZonesConfig)
    enrichment: EnrichmentConfig = Field(default_factory=EnrichmentConfig)
    inference: InferenceConfig = Field(default_factory=InferenceConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    scanner: ScannerConfig = Field(default_factory=ScannerConfig)
    alerts: AlertsConfig = Field(default_factory=AlertsConfig)
    backtest: BacktestConfig = Field(default_factory=BacktestConfig)
    api: ApiConfig = Field(default_factory=ApiConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)


def load_settings(path: str | Path | None = None) -> Settings:
    """Load and validate settings.yaml (path defaults to $SETTINGS_PATH)."""
    resolved = Path(path or os.environ.get("SETTINGS_PATH", DEFAULT_SETTINGS_PATH))
    raw = yaml.safe_load(resolved.read_text(encoding="utf-8")) or {}
    return Settings.model_validate(raw)


class AppConfig(BaseModel):
    """Everything the application needs, validated, in one object."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    settings: Settings
    secrets: Secrets


def load_config(settings_path: str | Path | None = None) -> AppConfig:
    return AppConfig(settings=load_settings(settings_path), secrets=Secrets())
