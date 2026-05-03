import math

import numpy as np
import pandas as pd
import pytest

from scanner.indicators import (
    above_ma,
    iv_rank,
    normalize_min_max,
    period_return,
    realized_volatility,
    relative_strength,
    volume_expansion_ratio,
)


def test_period_return_basic():
    prices = pd.Series([100.0, 101, 102, 103, 110])
    # 4-period return: from 100 -> 110
    assert period_return(prices, 4) == pytest.approx(0.10)


def test_period_return_insufficient_history():
    prices = pd.Series([100.0])
    assert math.isnan(period_return(prices, 5))


def test_above_ma():
    rising = pd.Series(range(1, 51), dtype="float64")
    assert above_ma(rising, 20) is True

    falling = pd.Series(range(50, 0, -1), dtype="float64")
    assert above_ma(falling, 20) is False


def test_relative_strength_outperformance():
    asset = pd.Series([100, 105, 110, 115, 120], dtype="float64")
    bench = pd.Series([100, 101, 102, 103, 104], dtype="float64")
    rs = relative_strength(asset, bench, 4)
    assert rs > 1.0


def test_relative_strength_nan_when_undefined():
    short = pd.Series([100.0])
    bench = pd.Series([100.0])
    assert math.isnan(relative_strength(short, bench, 5))


def test_realized_volatility_positive():
    rng = np.random.default_rng(0)
    prices = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.02, 100))))
    rv = realized_volatility(prices, 30)
    assert 0.05 < rv < 1.5  # sane annualized range


def test_volume_expansion_ratio():
    base = [1_000] * 30
    spike = [3_000] * 5
    series = pd.Series(base + spike, dtype="float64")
    # recent (5) much higher than baseline (30) should give >1
    assert volume_expansion_ratio(series, recent=5, baseline=30) > 1.5


def test_iv_rank_min_max():
    history = pd.Series([0.10, 0.20, 0.30, 0.40, 0.50])
    assert iv_rank(0.10, history) == pytest.approx(0.0)
    assert iv_rank(0.50, history) == pytest.approx(100.0)
    assert iv_rank(0.30, history) == pytest.approx(50.0)


def test_iv_rank_degenerate_history():
    flat = pd.Series([0.25, 0.25, 0.25])
    assert math.isnan(iv_rank(0.25, flat))


def test_normalize_min_max():
    s = pd.Series([1.0, 2, 3, 4, 5])
    out = normalize_min_max(s)
    assert out.iloc[0] == pytest.approx(0.0)
    assert out.iloc[-1] == pytest.approx(1.0)


def test_normalize_min_max_constant():
    s = pd.Series([3.0, 3, 3])
    out = normalize_min_max(s)
    assert (out == 0.5).all()
