import math

import pandas as pd

from scanner.config import OptionsEngineConfig
from scanner.options_engine import OptionsEngine

from .conftest import FakeDataSource, make_chain, make_history, near_future_date


def _build_snapshot_data(
    ticker: str = "ABC",
    iv: float = 0.20,
    chain_volume: int = 500,
    chain_oi: int = 800,
) -> FakeDataSource:
    fake = FakeDataSource()
    fake.histories[ticker] = make_history(days=400, drift=0.001, vol=0.025, seed=11)
    expiry = near_future_date(35)
    fake.expirations[ticker] = [expiry, near_future_date(7)]

    underlying = float(fake.histories[ticker]["Close"].iloc[-1])
    chain = make_chain(
        underlying, iv=iv, volume=chain_volume, open_interest=chain_oi
    )
    fake.chains[(ticker, expiry)] = (chain, chain.copy())
    return fake


def test_options_engine_emits_metrics_for_expiration_in_band():
    fake = _build_snapshot_data(iv=0.18)
    engine = OptionsEngine(fake, OptionsEngineConfig())
    snap = fake.get_snapshot("ABC", 400)

    metrics = engine.evaluate(snap)
    assert metrics is not None
    assert metrics.dte is not None and 20 <= metrics.dte <= 60
    assert metrics.total_volume > 0
    assert metrics.avg_open_interest > 0
    assert not math.isnan(metrics.iv)


def test_options_engine_skips_when_no_expiration_in_band():
    fake = _build_snapshot_data()
    fake.expirations["ABC"] = [near_future_date(5)]   # only short-dated expiry
    engine = OptionsEngine(fake, OptionsEngineConfig())
    snap = fake.get_snapshot("ABC", 400)
    assert engine.evaluate(snap) is None


def test_iv_rank_filter_rejects_high_iv():
    """Ensure passes_filters honors the IV-rank ceiling."""
    fake = _build_snapshot_data()
    engine = OptionsEngine(fake, OptionsEngineConfig())
    snap = fake.get_snapshot("ABC", 400)
    metrics = engine.evaluate(snap)
    assert metrics is not None

    metrics.iv_rank = 80.0
    ok, reason = engine.passes_filters(metrics)
    assert ok is False
    assert "IV Rank" in reason


def test_options_liquidity_filter_rejects_low_volume():
    fake = _build_snapshot_data(chain_volume=10)
    engine = OptionsEngine(fake, OptionsEngineConfig())
    snap = fake.get_snapshot("ABC", 400)
    metrics = engine.evaluate(snap)
    assert metrics is not None
    metrics.iv_rank = 10.0  # low IV (would pass IV filter)
    ok, reason = engine.passes_filters(metrics)
    assert ok is False
    assert "options volume" in reason


def test_options_filter_rejects_thin_open_interest():
    fake = _build_snapshot_data(chain_oi=50)
    engine = OptionsEngine(fake, OptionsEngineConfig())
    snap = fake.get_snapshot("ABC", 400)
    metrics = engine.evaluate(snap)
    assert metrics is not None
    metrics.iv_rank = 10.0
    metrics.total_volume = 5_000  # well above min
    ok, reason = engine.passes_filters(metrics)
    assert ok is False
    assert "OI" in reason
