from scanner.config import SectorEngineConfig, UniverseConfig
from scanner.sector_engine import SectorEngine

from .conftest import FakeDataSource, make_history


def _build_data() -> FakeDataSource:
    fake = FakeDataSource()
    # Benchmark: ~flat
    fake.histories["SPY"] = make_history(days=300, drift=0.0001, vol=0.01, seed=1)
    # Strong sector
    fake.histories["XLK"] = make_history(days=300, drift=0.005, vol=0.012, volume=2_000_000, seed=2)
    # Weak sector
    fake.histories["XLU"] = make_history(days=300, drift=-0.002, vol=0.008, volume=500_000, seed=3)
    return fake


def test_sector_engine_ranks_strong_sector_higher():
    fake = _build_data()
    universe = UniverseConfig(
        benchmark="SPY",
        sector_etfs={"Technology": "XLK", "Utilities": "XLU"},
    )
    engine = SectorEngine(fake, universe, SectorEngineConfig(), history_days=300)

    scores = engine.rank()
    assert len(scores) == 2
    assert scores[0].sector == "Technology"
    assert scores[1].sector == "Utilities"
    assert scores[0].composite >= scores[1].composite
    assert 0.0 <= scores[0].composite <= 100.0


def test_top_sectors_returns_top_n():
    fake = _build_data()
    fake.histories["XLF"] = make_history(days=300, drift=0.001, vol=0.012, seed=4)
    universe = UniverseConfig(
        benchmark="SPY",
        sector_etfs={"Technology": "XLK", "Utilities": "XLU", "Financials": "XLF"},
    )
    cfg = SectorEngineConfig()
    cfg.top_n_sectors = 2
    engine = SectorEngine(fake, universe, cfg, history_days=300)

    scores = engine.rank()
    top = engine.top_sectors(scores)
    assert len(top) == 2
    assert top == [s.sector for s in scores[:2]]


def test_sector_engine_handles_missing_benchmark():
    fake = FakeDataSource()  # no benchmark history
    universe = UniverseConfig(benchmark="SPY", sector_etfs={"Technology": "XLK"})
    engine = SectorEngine(fake, universe, SectorEngineConfig(), history_days=300)
    assert engine.rank() == []
