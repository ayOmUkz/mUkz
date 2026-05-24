"""Command-line entry point.

Examples
--------
::

    # Scan the built-in universe with default config
    python -m scanner

    # Scan a custom ticker list
    python -m scanner --tickers SMCI,SHAK,WAL,STAG

    # JSON export for downstream tooling
    python -m scanner --format json > scan.json

    # Disable the top-sector restriction
    python -m scanner --no-restrict-sectors
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .config import load_config
from .models import Candidate, ScanResult
from .runner import ScannerRunner, to_dict

app = typer.Typer(add_completion=False, help="ACTUAL_TRADES Scanner Engine.")
console = Console()


@app.command()
def main(
    config: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Path to scanner.yaml. Defaults to packaged config."
    ),
    tickers: Optional[str] = typer.Option(
        None, "--tickers", "-t", help="Comma-separated tickers (overrides config)."
    ),
    universe_file: Optional[Path] = typer.Option(
        None, "--universe-file", help="Newline-separated tickers file."
    ),
    fmt: str = typer.Option(
        "table", "--format", "-f", help="Output format: table | json", case_sensitive=False
    ),
    restrict_sectors: bool = typer.Option(
        True,
        "--restrict-sectors/--no-restrict-sectors",
        help="Filter to top-N sectors from the sector engine.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging."),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    cfg = load_config(config)

    explicit: list[str] | None = None
    if tickers:
        explicit = [t.strip() for t in tickers.split(",") if t.strip()]
    elif universe_file:
        explicit = [
            line.strip()
            for line in universe_file.read_text().splitlines()
            if line.strip() and not line.startswith("#")
        ]

    runner = ScannerRunner(cfg)
    result = runner.run(tickers=explicit, restrict_to_top_sectors=restrict_sectors)

    if fmt.lower() == "json":
        json.dump(to_dict(result), sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
        return

    _print_summary(result)


# ---------------------------------------------------------------- presentation
def _print_summary(result: ScanResult) -> None:
    sector_table = Table(title="Top-Down: Sector Strength", show_lines=False)
    sector_table.add_column("#", justify="right")
    sector_table.add_column("Sector")
    sector_table.add_column("ETF")
    sector_table.add_column("Rel. Perf.", justify="right")
    sector_table.add_column("Vol. Exp.", justify="right")
    sector_table.add_column("RS", justify="right")
    sector_table.add_column("Composite", justify="right")
    for i, s in enumerate(result.sectors, start=1):
        sector_table.add_row(
            str(i),
            s.sector,
            s.etf,
            f"{s.relative_performance:+.2%}",
            f"{s.volume_expansion:.2f}x",
            f"{s.relative_strength:.2f}",
            f"{s.composite:.1f}",
        )
    console.print(sector_table)

    cand_table = Table(
        title=f"Ranked Candidates  ({result.filtered_size} of {result.universe_size} screened)",
        show_lines=False,
    )
    cand_table.add_column("#", justify="right")
    cand_table.add_column("Ticker")
    cand_table.add_column("Sector")
    cand_table.add_column("1M Ret", justify="right")
    cand_table.add_column("MCap", justify="right")
    cand_table.add_column("IV", justify="right")
    cand_table.add_column("IV Rank", justify="right")
    cand_table.add_column("Opt Vol", justify="right")
    cand_table.add_column("Score", justify="right")
    cand_table.add_column("Notes")

    for i, c in enumerate(result.candidates, start=1):
        cand_table.add_row(
            str(i),
            c.ticker,
            c.sector or "-",
            f"{c.stock.return_1m:+.2%}",
            f"${c.stock.market_cap/1e6:,.0f}M",
            f"{c.options.iv:.1%}" if c.options.iv == c.options.iv else "n/a",
            f"{c.options.iv_rank:.1f}" if c.options.iv_rank == c.options.iv_rank else "n/a",
            f"{c.options.total_volume:,}",
            f"{c.composite_score:.1f}",
            "; ".join(c.notes) if c.notes else "",
        )
    console.print(cand_table)

    if not result.candidates:
        console.print(
            "[yellow]No candidates passed all filters. "
            "Loosen thresholds in config/scanner.yaml or pass --no-restrict-sectors."
            "[/yellow]"
        )


def _candidate_one_liner(c: Candidate) -> str:
    return (
        f"{c.ticker:<6} score={c.composite_score:5.1f} "
        f"mom={c.momentum_score:5.1f} iv={c.iv_cheapness_score:5.1f} "
        f"liq={c.liquidity_score:5.1f} sec={c.sector_strength_score:5.1f}"
    )


if __name__ == "__main__":  # pragma: no cover
    app()
