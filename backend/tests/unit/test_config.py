"""Tests for configuration loading and validation."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import (
    DpssWeights,
    PrintSignificanceWeights,
    Secrets,
    Settings,
    ZoneStrengthWeights,
    load_settings,
)

REPO_SETTINGS = Path(__file__).parents[3] / "config" / "settings.yaml"


def test_repo_settings_yaml_is_valid():
    settings = load_settings(REPO_SETTINGS)
    assert settings.scoring.dpss_weights.print == 0.25
    assert settings.inference.confidence_cap < 1.0
    assert settings.discovery.limit <= 200  # API maximum for /darkpool/recent
    assert "SPY" in settings.universe.watchlist


def test_defaults_are_valid_without_yaml():
    settings = Settings()
    assert settings.zones.epsilon.atr_mult == 0.25


def test_zone_strength_weights_must_sum_to_100():
    with pytest.raises(ValidationError):
        ZoneStrengthWeights(pct_adv30=50)


def test_dpss_weights_must_sum_to_1():
    with pytest.raises(ValidationError):
        DpssWeights(print=0.5, zone=0.5, direction=0.25, relevance=0.2)


def test_print_significance_weights_must_sum_to_1():
    with pytest.raises(ValidationError):
        PrintSignificanceWeights(size_percentile=0.9)


def test_unknown_yaml_keys_are_rejected(tmp_path):
    # A typo like "watchlst" must fail loudly, not be silently ignored.
    bad = tmp_path / "settings.yaml"
    bad.write_text("universe:\n  watchlst: [SPY]\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        load_settings(bad)


def test_confidence_cap_must_stay_below_certainty(tmp_path):
    overconfident = tmp_path / "settings.yaml"
    overconfident.write_text("inference:\n  confidence_cap: 1.0\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        load_settings(overconfident)


def test_secrets_load_from_env_and_are_redacted(monkeypatch):
    monkeypatch.setenv("UW_API_TOKEN", "super-secret-token")
    secrets = Secrets(_env_file=None)
    assert secrets.uw_api_token.get_secret_value() == "super-secret-token"
    assert "super-secret-token" not in repr(secrets)
    assert "super-secret-token" not in str(secrets.uw_api_token)


def test_missing_token_fails_at_startup(monkeypatch):
    monkeypatch.delenv("UW_API_TOKEN", raising=False)
    with pytest.raises(ValidationError):
        Secrets(_env_file=None)
