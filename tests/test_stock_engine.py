from scanner.config import StockEngineConfig, UniverseConfig
from scanner.stock_engine import StockEngine

from .conftest import FakeDataSource, make_history


def _data_with(
    ticker: str,
    *,
    market_cap: float,
    volume: int,
    sector: str = "Technology",
    recent_trend_pct: float = 0.10,
) -> FakeDataSource:
    fake = FakeDataSource()
    fake.histories["SPY"] = make_history(days=300, drift=0.0001, vol=0.01, seed=1)
    fake.histories[ticker] = make_history(
        days=300,
        drift=0.0,
        vol=0.015,
        volume=volume,
        seed=7,
        recent_trend_pct=recent_trend_pct,
        recent_trend_days=30,
    )
    fake.infos[ticker] = {"sector": sector, "marketCap": market_cap}
    return fake


def test_stock_passes_full_filter_set():
    fake = _data_with("ABC", market_cap=1.5e9, volume=2_000_000, recent_trend_pct=0.12)
    engine = StockEngine(fake, UniverseConfig(), StockEngineConfig(), history_days=300, lookback_days=21)

    passing, rejections = engine.screen(["ABC"])
    assert len(passing) == 1
    assert "ABC" not in rejections
    metrics = passing[0]
    assert metrics.return_1m > 0.05
    assert metrics.above_20d_ma is True
    assert metrics.above_50d_ma is True


def test_stock_rejected_for_low_momentum():
    fake = _data_with("LOW", market_cap=1.5e9, volume=2_000_000, recent_trend_pct=-0.05)
    engine = StockEngine(fake, UniverseConfig(), StockEngineConfig(), history_days=300, lookback_days=21)
    passing, rejections = engine.screen(["LOW"])
    assert passing == []
    assert "LOW" in rejections


def test_stock_rejected_for_market_cap_out_of_band():
    # Mega cap — way above $3B
    fake = _data_with("BIG", market_cap=200e9, volume=2_000_000, recent_trend_pct=0.12)
    engine = StockEngine(fake, UniverseConfig(), StockEngineConfig(), history_days=300, lookback_days=21)
    passing, rejections = engine.screen(["BIG"])
    assert passing == []
    assert "market cap" in rejections["BIG"]


def test_stock_rejected_for_low_liquidity():
    fake = _data_with("THIN", market_cap=1.5e9, volume=100_000, recent_trend_pct=0.12)
    engine = StockEngine(fake, UniverseConfig(), StockEngineConfig(), history_days=300, lookback_days=21)
    passing, rejections = engine.screen(["THIN"])
    assert passing == []
    assert "avg volume" in rejections["THIN"]


def test_sector_restriction_filters_outside_sectors():
    fake = _data_with("OUT", market_cap=1.5e9, volume=2_000_000, sector="Utilities", recent_trend_pct=0.12)
    engine = StockEngine(fake, UniverseConfig(), StockEngineConfig(), history_days=300, lookback_days=21)
    passing, rejections = engine.screen(["OUT"], allowed_sectors={"Technology"})
    assert passing == []
    assert "Utilities" in rejections["OUT"]
