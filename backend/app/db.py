"""Database schema and access helpers.

Tables are defined with SQLAlchemy Core (not ORM) because the two big
time-series tables become TimescaleDB hypertables, which cannot carry the
surrogate primary keys the ORM insists on. Dedup is enforced by unique
indexes that include the time column (a hypertable requirement).

Three storage rules from the plan (docs/PLAN.md §6, §8):

* ``raw_prints`` stores every API row verbatim and is never mutated.
* ``prints`` holds only rows that passed validation; quality problems that
  are survivable (e.g. a crossed quote) travel along in ``quality_flags``.
* every rejected row leaves a trace in ``data_quality_log``.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.engine import Connection, Engine

metadata = sa.MetaData()

#: JSON that becomes JSONB on PostgreSQL and plain JSON elsewhere (tests).
JsonB = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

symbols = sa.Table(
    "symbols",
    metadata,
    sa.Column("ticker", sa.Text, primary_key=True),
    sa.Column("sector", sa.Text),
    sa.Column("issue_type", sa.Text),
    sa.Column("avg30_volume", sa.Numeric(20, 4)),
    # Nullable until the M1 float probe confirms availability (plan §1).
    sa.Column("shares_outstanding", sa.Numeric(20, 0)),
    sa.Column("float_shares", sa.Numeric(20, 0)),
    sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
)

raw_prints = sa.Table(
    "raw_prints",
    metadata,
    sa.Column("ticker", sa.Text, nullable=False),
    sa.Column("tracking_id", sa.BigInteger),
    sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("payload", JsonB, nullable=False),
    sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
    sa.UniqueConstraint("ticker", "tracking_id", "executed_at", name="uq_raw_prints_identity"),
)

prints = sa.Table(
    "prints",
    metadata,
    # --- fields straight from the API (typed) ---
    sa.Column("ticker", sa.Text, nullable=False),
    sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("trf_executed_at", sa.DateTime(timezone=True)),
    sa.Column("price", sa.Numeric(18, 6), nullable=False),
    sa.Column("size", sa.BigInteger, nullable=False),
    sa.Column("premium", sa.Numeric(20, 4), nullable=False),
    sa.Column("market_center", sa.Text),
    sa.Column("sale_cond_codes", sa.Text),
    sa.Column("trade_code", sa.Text),
    sa.Column("ext_hour_sold_codes", sa.Text),
    sa.Column("trade_settlement", sa.Text),
    sa.Column("nbbo_bid", sa.Numeric(18, 6)),
    sa.Column("nbbo_ask", sa.Numeric(18, 6)),
    sa.Column("nbbo_bid_quantity", sa.BigInteger),
    sa.Column("nbbo_ask_quantity", sa.BigInteger),
    sa.Column("volume", sa.BigInteger),
    sa.Column("avg30_volume", sa.Numeric(20, 4)),
    sa.Column("tracking_id", sa.BigInteger),
    sa.Column("sector", sa.Text),
    sa.Column("issue_type", sa.Text),
    # --- derived at ingest time (plan §3 "Derivable") ---
    sa.Column("mid", sa.Numeric(18, 6)),
    sa.Column("spread_bps", sa.Float),
    sa.Column("price_vs_mid_bps", sa.Float),
    sa.Column("report_delay_s", sa.Float, nullable=False),
    sa.Column("pct_adv30", sa.Float),
    sa.Column("pct_day_volume", sa.Float),
    # --- data quality (plan §8) ---
    sa.Column("quality_flags", JsonB, nullable=False),
    sa.Column("location_confidence", sa.Text, nullable=False),  # ok | low | none
    sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
    # --- M2 classification (plan §7); filled by the enrich job ---
    sa.Column("size_class", sa.Text),        # normal | elevated | unusual | extreme
    sa.Column("size_percentile", sa.Float),  # estimated, vs the symbol's own history
    sa.Column("size_confidence", sa.Text),   # historical | provisional (cold start)
    sa.Column("location_bucket", sa.Text),   # at_bid ... above_ask (None if no quote)
    sa.Column("vwap_position", sa.Text),     # above | near | below (vs session VWAP)
    sa.Column("timing_bucket", sa.Text),     # premarket ... after_hours | late_report
    sa.Column("character", sa.Text),         # liquidity character (plan §7)
    sa.UniqueConstraint("ticker", "tracking_id", "executed_at", name="uq_prints_identity"),
)

#: Classification columns added in M2 (migration 0002 guards on their absence).
PRINT_CLASSIFICATION_COLUMNS = (
    "size_class",
    "size_percentile",
    "size_confidence",
    "location_bucket",
    "vwap_position",
    "timing_bucket",
    "character",
)

candles = sa.Table(
    "candles",
    metadata,
    sa.Column("ticker", sa.Text, nullable=False),
    sa.Column("candle_size", sa.Text, nullable=False),  # 1m | 1d | ...
    sa.Column("ts", sa.DateTime(timezone=True), nullable=False),  # bar start (UTC)
    sa.Column("open", sa.Numeric(18, 6), nullable=False),
    sa.Column("high", sa.Numeric(18, 6), nullable=False),
    sa.Column("low", sa.Numeric(18, 6), nullable=False),
    sa.Column("close", sa.Numeric(18, 6), nullable=False),
    sa.Column("volume", sa.BigInteger),
    sa.Column("session", sa.Text),  # r | pre | post when the API provides it
    sa.UniqueConstraint("ticker", "candle_size", "ts", name="uq_candles_identity"),
)

symbol_days = sa.Table(
    "symbol_days",
    metadata,
    sa.Column("ticker", sa.Text, nullable=False),
    sa.Column("trading_date", sa.Date, nullable=False),
    sa.Column("session_vwap", sa.Numeric(18, 6)),
    sa.Column("atr14", sa.Float),
    sa.Column("prior_high", sa.Numeric(18, 6)),
    sa.Column("prior_low", sa.Numeric(18, 6)),
    sa.Column("prior_close", sa.Numeric(18, 6)),
    sa.Column("minute_bars", sa.Integer),  # VWAP coverage (0 = no minute data)
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    sa.UniqueConstraint("ticker", "trading_date", name="uq_symbol_days_identity"),
)

zones = sa.Table(
    "zones",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("ticker", sa.Text, nullable=False),
    sa.Column("as_of_date", sa.Date, nullable=False),
    sa.Column("window_start", sa.Date, nullable=False),
    sa.Column("window_end", sa.Date, nullable=False),
    sa.Column("price_low", sa.Numeric(18, 6), nullable=False),
    sa.Column("price_high", sa.Numeric(18, 6), nullable=False),
    sa.Column("wavg_price", sa.Numeric(18, 6), nullable=False),
    sa.Column("total_shares", sa.BigInteger, nullable=False),
    sa.Column("total_notional", sa.Numeric(20, 4), nullable=False),
    sa.Column("print_count", sa.Integer, nullable=False),
    sa.Column("unique_days", sa.Integer, nullable=False),
    sa.Column("first_print_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("last_print_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("pct_adv30", sa.Float),
    sa.Column("pct_dark_volume", sa.Float),
    sa.Column("tightness_atr", sa.Float),
    sa.Column("strength_score", sa.Float, nullable=False),
    sa.Column("strength_class", sa.Text, nullable=False),  # weak..exceptional
    sa.Column("status", sa.Text, nullable=False),  # untested..broken/reclaimed
    sa.Column("respected_touches", sa.Integer, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Index("ix_zones_ticker_asof", "ticker", "as_of_date"),
)

zone_events = sa.Table(
    "zone_events",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("zone_id", sa.Integer, nullable=False),
    sa.Column("session_date", sa.Date, nullable=False),
    sa.Column("event", sa.Text, nullable=False),  # touch | reject | break | reclaim
    sa.Column("close", sa.Numeric(18, 6)),
    sa.Index("ix_zone_events_zone", "zone_id"),
)

signals = sa.Table(
    "signals",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("ticker", sa.Text, nullable=False),
    sa.Column("as_of_date", sa.Date, nullable=False),
    sa.Column("classification", sa.Text, nullable=False),  # 6-state (plan §10)
    sa.Column("confidence", sa.Float, nullable=False),
    sa.Column("dpss", sa.Float, nullable=False),
    sa.Column("sub_scores", JsonB, nullable=False),
    sa.Column("evidence", JsonB, nullable=False),  # {supporting, contradicting}
    sa.Column("invalidation", JsonB, nullable=False),
    sa.Column("top_zone", JsonB),  # self-contained snapshot (zones get rebuilt)
    sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
    # Immutable once written (backtest integrity): re-runs insert-ignore.
    sa.UniqueConstraint("ticker", "as_of_date", name="uq_signals_identity"),
)

alerts = sa.Table(
    "alerts",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("rule", sa.Text, nullable=False),
    sa.Column("ticker", sa.Text, nullable=False),
    sa.Column("as_of_date", sa.Date, nullable=False),
    # Stable identity of what is being alerted about (rule:ticker:level...).
    # Dedup/cooldown queries key on this, not on the row id.
    sa.Column("base_key", sa.Text, nullable=False),
    sa.Column("payload", JsonB, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("delivered", JsonB),  # channels this alert went out on
    sa.Index("ix_alerts_base_key", "base_key", "created_at"),
    sa.Index("ix_alerts_asof", "as_of_date"),
)

backtest_runs = sa.Table(
    "backtest_runs",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("start_date", sa.Date),
    sa.Column("end_date", sa.Date),
    sa.Column("config", JsonB, nullable=False),
    sa.Column("config_hash", sa.Text, nullable=False),
    sa.Column("summary", JsonB, nullable=False),
)

backtest_events = sa.Table(
    "backtest_events",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("run_id", sa.Integer, nullable=False),
    sa.Column("ticker", sa.Text, nullable=False),
    sa.Column("signal_date", sa.Date, nullable=False),
    sa.Column("direction", sa.Integer, nullable=False),  # +1 acc / -1 dist
    sa.Column("classification", sa.Text, nullable=False),
    sa.Column("confidence", sa.Float, nullable=False),
    sa.Column("dpss", sa.Float, nullable=False),
    sa.Column("overlapping", sa.Boolean, nullable=False),
    sa.Column("unmeasurable", sa.Text),  # reason, when no entry price exists
    sa.Column("entry_date", sa.Date),
    sa.Column("entry_price", sa.Float),
    sa.Column("returns", JsonB),  # per horizon: {raw, market_adj, vol_adj}
    sa.Column("mfe", sa.Float),
    sa.Column("mae", sa.Float),
    sa.Column("invalidated_at_session", sa.Integer),
    sa.Column("segments", JsonB, nullable=False),
    sa.Index("ix_backtest_events_run", "run_id"),
)

backtest_results = sa.Table(
    "backtest_results",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("run_id", sa.Integer, nullable=False),
    sa.Column("cohort", sa.Text, nullable=False),
    sa.Column("horizon", sa.Integer, nullable=False),
    sa.Column("metrics", JsonB, nullable=False),
    sa.Index("ix_backtest_results_run", "run_id"),
)

symbol_stats = sa.Table(
    "symbol_stats",
    metadata,
    sa.Column("ticker", sa.Text, nullable=False),
    sa.Column("as_of_date", sa.Date, nullable=False),
    sa.Column("sample_size", sa.Integer, nullable=False),
    sa.Column("p50", sa.Float),
    sa.Column("p90", sa.Float),
    sa.Column("p99", sa.Float),
    sa.Column("p999", sa.Float),
    sa.Column("mad", sa.Float),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    sa.UniqueConstraint("ticker", "as_of_date", name="uq_symbol_stats_identity"),
)

data_quality_log = sa.Table(
    "data_quality_log",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("ticker", sa.Text),
    sa.Column("tracking_id", sa.BigInteger),
    sa.Column("executed_at", sa.DateTime(timezone=True)),
    sa.Column("stage", sa.Text, nullable=False),  # raw | parse | quality
    sa.Column("reasons", JsonB, nullable=False),
    sa.Column("payload", JsonB, nullable=False),
    sa.Column("logged_at", sa.DateTime(timezone=True), nullable=False),
)

api_probes = sa.Table(
    "api_probes",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("probe", sa.Text, nullable=False),
    sa.Column("ran_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("result", JsonB, nullable=False),
)

ingest_runs = sa.Table(
    "ingest_runs",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("run_date", sa.Date, nullable=False),
    sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("finished_at", sa.DateTime(timezone=True)),
    sa.Column("stats", JsonB),
)

#: Tables that become hypertables on TimescaleDB, with their time column.
HYPERTABLES: dict[str, str] = {
    "raw_prints": "executed_at",
    "prints": "executed_at",
    "candles": "ts",
}


def make_engine(database_url: str) -> Engine:
    if database_url.startswith("sqlite") and ":memory:" in database_url:
        # A single shared connection, usable across threads — without this an
        # in-memory database is empty in every new connection/thread (tests,
        # FastAPI TestClient worker threads).
        return sa.create_engine(
            database_url,
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=sa.pool.StaticPool,
        )
    return sa.create_engine(database_url, future=True)


def ensure_schema(engine: Engine) -> None:
    """Create any missing tables (idempotent) and hypertables where possible.

    Production deployments should run ``alembic upgrade head`` instead; this
    exists so tests, notebooks, and first runs work without ceremony. Both
    paths share the same metadata, so they cannot drift apart.
    """
    metadata.create_all(engine)
    with engine.begin() as conn:
        maybe_create_hypertables(conn)


def maybe_create_hypertables(conn: Connection) -> bool:
    """Convert time-series tables to hypertables when TimescaleDB is present.

    On plain PostgreSQL or SQLite this is a no-op — everything still works,
    just without Timescale's partitioning. Returns True if hypertables exist.
    """
    if conn.dialect.name != "postgresql":
        return False
    conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
    installed = conn.execute(
        sa.text("SELECT count(*) FROM pg_extension WHERE extname = 'timescaledb'")
    ).scalar()
    if not installed:
        return False
    for table, time_column in HYPERTABLES.items():
        conn.execute(
            sa.text(
                "SELECT create_hypertable(:table, :col, if_not_exists => TRUE, "
                "migrate_data => TRUE)"
            ),
            {"table": table, "col": time_column},
        )
    return True


def insert_ignore(conn: Connection, table: sa.Table, rows: list[dict]) -> int:
    """Insert rows, silently skipping ones that violate a unique constraint.

    This is what makes re-fetching (pagination overlap, re-runs of a day)
    idempotent instead of double-counting prints (plan §8, "Duplicates").
    Returns the number of rows actually inserted.
    """
    if not rows:
        return 0
    dialect = conn.dialect.name
    if dialect == "postgresql":
        statement = postgresql.insert(table).values(rows).on_conflict_do_nothing()
    elif dialect == "sqlite":
        statement = sqlite.insert(table).values(rows).on_conflict_do_nothing()
    else:  # best effort for other dialects
        statement = table.insert().values(rows)
    result = conn.execute(statement)
    return int(result.rowcount or 0)
