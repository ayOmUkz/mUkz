"""End-to-end nightly run on the recorded fixture day (fake network)."""

import json
from datetime import date, timedelta
from pathlib import Path

from app.alerts import build_digest
from app.config import Settings
from app.db import ensure_schema, make_engine
from app.jobs.nightly import run_nightly

FIXTURE = Path(__file__).parents[1] / "fixtures" / "darkpool_recent_sample.json"
TRADING_DATE = date(2026, 8, 5)
BASE_PRICES = {"TSM": 415.0, "IWM": 300.0, "SGOV": 100.44}


class FakeFullClient:
    """Implements everything ingest + enrich need for the fixture day."""

    def recent_darkpool_trades(self, **kwargs):
        return json.loads(FIXTURE.read_text(encoding="utf-8"))

    def iter_ticker_darkpool_trades(self, ticker, **kwargs):
        yield from (
            row
            for row in json.loads(FIXTURE.read_text(encoding="utf-8"))
            if row["ticker"] == ticker
        )

    def ohlc(self, ticker, candle_size, **kwargs):
        base = BASE_PRICES[ticker]
        if candle_size == "1d":
            start = TRADING_DATE - timedelta(days=19)
            return [
                {
                    "date": (start + timedelta(days=i)).isoformat(),
                    "open": base, "high": base + 2, "low": base - 2,
                    "close": base + 1, "volume": 1_000_000,
                }
                for i in range(20)
            ]
        return [
            {
                "start": f"2026-08-05T18:{30 + i}:00Z",
                "o": base, "h": base + 1, "l": base - 1, "c": base,
                "vol": 1000, "market": "r",
            }
            for i in range(3)
        ]


def test_run_nightly_full_chain(tmp_path):
    engine = make_engine("sqlite+pysqlite:///:memory:")
    ensure_schema(engine)
    settings = Settings.model_validate({"universe": {"watchlist": ["TSM", "IWM", "SGOV"]}})

    summary = run_nightly(
        engine, FakeFullClient(), settings, TRADING_DATE, report_dir=tmp_path
    )

    assert summary["ingest"]["clean"] == 3
    assert summary["analyze"]["signals"] == 3
    assert summary["reports"] == ["IWM", "SGOV", "TSM"]
    # Three quiet single-print tickers: correctly, nothing alert-worthy.
    assert summary["alerts"] == []

    for ticker in ("TSM", "IWM", "SGOV"):
        markdown = (tmp_path / f"2026-08-05_{ticker}.md").read_text(encoding="utf-8")
        assert f"# {ticker} — 2026-08-05" in markdown
        assert "## Final verdict: insufficient evidence" in markdown
        report = json.loads(
            (tmp_path / f"2026-08-05_{ticker}.json").read_text(encoding="utf-8")
        )
        assert report["dpss"] > 0

    subject, body = build_digest(TRADING_DATE, summary["alerts"])
    assert "0 alert(s)" in subject
    assert body == "No alerts today.\n"
