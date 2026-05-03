"""End-to-end pipeline test using the FakeDataSource."""

from datetime import date, timedelta

from scanner.config import ScannerConfig, UniverseConfig
from scanner.runner import ScannerRunner

from .conftest import FakeDataSource, make_chain, make_history, near_future_date


def _seed_pipeline_data() -> FakeDataSource:
    fake = FakeDataSource()

    # Benchmark + sector ETFs
    fake.histories["SPY"] = make_history(days=400, drift=0.0001, vol=0.01, seed=1)
    fake.histories["XLK"] = make_history(
        days=400, drift=0.0, vol=0.012, volume=2_000_000, seed=2,
        recent_trend_pct=0.08, recent_trend_days=30,
    )
    fake.histories["XLU"] = make_history(
        days=400, drift=0.0, vol=0.008, volume=500_000, seed=3,
        recent_trend_pct=-0.03, recent_trend_days=30,
    )

    # Strong tech mid-cap that should pass everything.
    fake.histories["GOOD"] = make_history(
        days=400, drift=0.0, vol=0.018, volume=3_000_000, seed=20,
        recent_trend_pct=0.12, recent_trend_days=30,
    )
    fake.infos["GOOD"] = {"sector": "Technology", "marketCap": 1_500_000_000}
    expiry = near_future_date(35)
    fake.expirations["GOOD"] = [expiry]
    underlying_good = float(fake.histories["GOOD"]["Close"].iloc[-1])
    chain = make_chain(underlying_good, iv=0.22, volume=2_000, open_interest=1_500)
    fake.chains[("GOOD", expiry)] = (chain, chain.copy())

    # Weak utility — should be screened out by sector + momentum.
    fake.histories["MEH"] = make_history(
        days=400, drift=0.0, vol=0.012, volume=300_000, seed=21,
        recent_trend_pct=-0.05, recent_trend_days=30,
    )
    fake.infos["MEH"] = {"sector": "Utilities", "marketCap": 1_000_000_000}
    fake.expirations["MEH"] = [expiry]
    fake.chains[("MEH", expiry)] = (chain.copy(), chain.copy())

    return fake


def test_full_pipeline_returns_winners_only():
    fake = _seed_pipeline_data()

    cfg = ScannerConfig()
    cfg.universe = UniverseConfig(
        benchmark="SPY",
        sector_etfs={"Technology": "XLK", "Utilities": "XLU"},
    )
    cfg.data.history_days = 400
    cfg.sector_engine.top_n_sectors = 1  # Only the best sector survives
    cfg.options_engine.iv_rank.max = 100  # don't reject on IV rank in this synthetic test

    runner = ScannerRunner(cfg, data_source=fake)
    result = runner.run(tickers=["GOOD", "MEH"], restrict_to_top_sectors=True)

    assert result.universe_size == 2
    tickers = [c.ticker for c in result.candidates]
    assert "GOOD" in tickers
    assert "MEH" not in tickers
    # Composite score must be non-negative and bounded
    for c in result.candidates:
        assert 0.0 <= c.composite_score <= 100.0
