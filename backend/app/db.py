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
