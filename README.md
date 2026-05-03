# ACTUAL_TRADES Scanner Engine

A **repeatable scanner engine** for identifying high-probability stock + options opportunities based on momentum, volatility mispricing, and liquidity.

---

## Objective

Identify stocks that meet **all** of the following:

- Positive 1-month momentum
- Low implied volatility (IV Rank < 30)
- Market cap between **$500M–$3B**
- Options volume > **1,000 contracts/day**

---

## Project Layout

```
mUkz/
├── config/
│   └── scanner.yaml          # All thresholds (tunable, no code changes)
├── src/scanner/
│   ├── __init__.py
│   ├── __main__.py           # `python -m scanner`
│   ├── cli.py                # Typer CLI
│   ├── config.py             # pydantic-validated YAML loader
│   ├── data_sources.py       # DataSource Protocol + yfinance impl
│   ├── indicators.py         # Pure math: returns, MA, RS, RV, IV rank
│   ├── models.py             # Dataclasses: SectorScore / StockMetrics / OptionsMetrics / Candidate
│   ├── universe.py           # Default mid-cap universe + resolution
│   ├── sector_engine.py      # Top-down sector ranking
│   ├── stock_engine.py       # Bottom-up filters
│   ├── options_engine.py     # Mispricing + liquidity
│   ├── ranking_engine.py     # Composite scoring
│   └── runner.py             # End-to-end orchestrator
├── tests/
│   ├── conftest.py           # FakeDataSource + synthetic OHLCV/chains
│   ├── test_indicators.py
│   ├── test_sector_engine.py
│   ├── test_stock_engine.py
│   ├── test_options_engine.py
│   ├── test_ranking_engine.py
│   └── test_runner.py        # End-to-end pipeline test
├── pyproject.toml
├── requirements.txt
└── README.md                 # this file
```

---

## Core Engine Architecture

### 1. Top-Down Analysis — Sector Engine

**Goal:** identify sectors with the strongest participation and capital flow.

| Metric | Source |
|---|---|
| 1-month relative performance vs S&P 500 | Sector ETF return − SPY return |
| Volume expansion vs 30-day average | recent / baseline ratio |
| Institutional flow proxy | ETF volume expansion |
| Relative strength | (1 + r_sector) / (1 + r_bench) |

**Output:** Top 3–5 sectors ranked by composite score (0–100).

**Code:** `src/scanner/sector_engine.py`

### 2. Bottom-Up Scanner — Stock Engine

Within selected sectors, filter stocks using three filter banks:

#### Momentum Filter
- 1-month return > **+5%**
- Price above **20D** and **50D** moving averages
- Relative Strength (RS) > market

#### Market Cap Filter
- **$500M ≤ Market Cap ≤ $3B**

#### Liquidity Filter
- Avg daily volume > **500K shares**

**Code:** `src/scanner/stock_engine.py`

### 3. Options Mispricing Engine

For each surviving stock, the engine selects a front-month expiration in a configurable **DTE band** (default 20–60), aggregates the **5 strikes nearest ATM** for both calls and puts, and computes:

#### IV Rank Filter
- **IV Rank < 30** (cheap options)

#### Options Liquidity Filter
- Total options volume > **1,000 contracts/day**
- Open Interest > **500 per strike**
- Bid-ask spread < **15% of mid**

#### Optional Enhancements
- IV vs Realized Volatility (mispricing read)
- Call/Put skew (bullish vs defensive)

> **Note on IV history:** `yfinance` does not expose historical IV. The engine uses the **trailing 30-day realized-volatility distribution** as a transparent proxy when no paid IV-history feed is wired in. Swap in Polygon/Tradier/IBKR via the `DataSource` Protocol for true IV Rank.

**Code:** `src/scanner/options_engine.py`

### 4. Ranking Engine

Each candidate is scored with a **weighted composite (0–100)**:

```
composite = 0.40 * momentum_score
          + 0.30 * iv_cheapness_score
          + 0.15 * liquidity_score
          + 0.15 * sector_strength_score
```

| Sub-score | Range | Drivers |
|---|---|---|
| `momentum_score` | 0–100 | 1M return (cap +30%), RS excess (cap 1.30), 20D/50D MA confirmation |
| `iv_cheapness_score` | 0–100 | Inverse IV Rank, +5 bonus when IV < realized vol |
| `liquidity_score` | 0–100 | log10 options volume + log10 OI + bid-ask quality |
| `sector_strength_score` | 0–100 | Pass-through of the sector composite |

All weights live in `config/scanner.yaml → ranking.weights` and are renormalized internally so they don't need to sum to 1.

**Code:** `src/scanner/ranking_engine.py`

---

## Configuration

Every threshold is tunable in `config/scanner.yaml`. Highlights:

```yaml
sector_engine:
  lookback_days: 21          # ~1 trading month
  top_n_sectors: 5

stock_engine:
  momentum:
    min_1m_return: 0.05      # +5%
    require_above_20d_ma: true
    require_above_50d_ma: true
  market_cap:
    min_usd: 500_000_000     # $500M
    max_usd: 3_000_000_000   # $3B
  liquidity:
    min_avg_daily_volume: 500_000

options_engine:
  iv_rank:
    max: 30.0                # cheap options only
  liquidity:
    min_total_volume: 1_000  # contracts/day
    min_open_interest_per_strike: 500
    max_bid_ask_spread_pct: 0.15
  expirations:
    min_dte: 20
    max_dte: 60

ranking:
  weights:
    momentum: 0.40
    iv_cheapness: 0.30
    liquidity: 0.15
    sector_strength: 0.15
  top_n_results: 25
```

---

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Or install as a package:

```bash
pip install -e .
```

---

## Usage

### CLI

```bash
# Scan the built-in mid-cap universe with default config (rich table)
python -m scanner

# Scan a custom ticker list
python -m scanner --tickers SMCI,SHAK,WAL,STAG

# Use a custom universe file (one ticker per line, # for comments)
python -m scanner --universe-file my_watchlist.txt

# JSON output for downstream tooling
python -m scanner --format json > scan.json

# Disable the top-sector restriction (scan everything)
python -m scanner --no-restrict-sectors

# Verbose logging (shows rejection reasons per ticker)
python -m scanner --verbose
```

### Programmatic

```python
from scanner.config import load_config
from scanner.runner import ScannerRunner

cfg = load_config()                       # or load_config("path/to/scanner.yaml")
runner = ScannerRunner(cfg)
result = runner.run(tickers=["SMCI", "WAL", "STAG"])

for c in result.candidates:
    print(f"{c.ticker:<6} score={c.composite_score:5.1f}  notes={c.notes}")
```

### Output (table format)

```
┌────────────────────── Top-Down: Sector Strength ──────────────────────┐
│  # │ Sector          │ ETF │ Rel. Perf. │ Vol. Exp. │  RS  │ Composite│
│  1 │ Technology      │ XLK │   +4.20%   │   1.18x   │ 1.04 │   82.4   │
│  2 │ Industrials     │ XLI │   +2.10%   │   1.05x   │ 1.02 │   65.1   │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────── Ranked Candidates  (5 of 138 screened) ──────────────────────┐
│  # │ Ticker │ Sector       │ 1M Ret │  MCap   │  IV  │ IV Rank │ Score │
│  1 │ SMCI   │ Technology   │ +12.4% │ $2,150M │ 28%  │  18.3   │  84.2 │
│  2 │ WAL    │ Financials   │  +8.1% │ $1,720M │ 24%  │  15.5   │  78.6 │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Data Sources

The engine consumes data through a `DataSource` **Protocol** (`src/scanner/data_sources.py`), so the underlying provider is swappable:

| Provider | Status | Notes |
|---|---|---|
| `YFinanceDataSource` | **default** | Free, with TTL cache. No historical IV. |
| Polygon | hook ready | Implement the 3-method Protocol |
| Tradier | hook ready | Implement the 3-method Protocol |
| IBKR | hook ready | Implement the 3-method Protocol |

`Protocol` interface:

```python
class DataSource(Protocol):
    def get_history(self, ticker: str, days: int) -> pd.DataFrame: ...
    def get_snapshot(self, ticker: str, history_days: int) -> TickerSnapshot: ...
    def get_options_chain(self, ticker: str, expiration: str) -> tuple[pd.DataFrame, pd.DataFrame]: ...
```

---

## Testing

```bash
pytest                  # all 33 tests
pytest -v               # verbose
pytest tests/test_runner.py   # end-to-end pipeline only
```

The full suite runs **offline** via the `FakeDataSource` fixture in `tests/conftest.py`. Each engine has a dedicated test file plus an end-to-end test that exercises the whole pipeline with a "winner" and a "loser" stock.

| Test file | Coverage |
|---|---|
| `test_indicators.py` | Pure math: returns, MA, RS, RV, IV rank, normalization |
| `test_sector_engine.py` | Sector ranking, top-N selection, missing-data fallback |
| `test_stock_engine.py` | Each filter rejection reason + happy path |
| `test_options_engine.py` | DTE selection, IV/volume/OI filters |
| `test_ranking_engine.py` | Sub-score monotonicity + composite bounds |
| `test_runner.py` | Full pipeline winners-only assertion |

---

## Pipeline Flow

```
   ┌────────────────┐
   │ Sector ETFs +  │
   │ SPY benchmark  │  ──►  SectorEngine  ──►  top N sectors
   └────────────────┘                              │
                                                   ▼
   ┌────────────────┐                       ┌────────────────┐
   │  Universe      │  ──►  StockEngine ──► │ Surviving      │
   │  (default mid- │       (momentum +     │ stock metrics  │
   │   cap or CLI)  │        mcap + liq)    └────────┬───────┘
   └────────────────┘                                ▼
                                              OptionsEngine
                                              (IV rank + liq)
                                                    │
                                                    ▼
                                              RankingEngine
                                              (composite 0-100)
                                                    │
                                                    ▼
                                              Top-N Candidates
```

---

## Extending

### Add a new filter

1. Add the threshold to `config/scanner.yaml` under the relevant engine.
2. Add a corresponding pydantic field in `config.py`.
3. Implement the check in the engine's `_reject_reason` (stocks) or `passes_filters` (options).
4. Add a unit test in `tests/`.

### Swap to a paid data feed

1. Implement the `DataSource` Protocol from `data_sources.py`.
2. Pass an instance to `ScannerRunner(cfg, data_source=my_source)`.
3. The four engines work unchanged.

### Tune the ranking

Edit `ranking.weights` in `config/scanner.yaml` (e.g. push `iv_cheapness` to 0.50 if you only care about volatility mispricing). Weights are renormalized internally — they don't need to sum to 1.

---

## Branch

All development lives on `claude/build-scanner-engine-QefUX`.

```bash
git log --oneline
# b0a6711 Build ACTUAL_TRADES scanner engine
# 5a34dbf Initialize repository
```
