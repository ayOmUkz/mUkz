"""Alembic environment.

The database URL comes from the ``DATABASE_URL`` environment variable
(see .env.example) — never from a committed file. No ORM models exist yet
(milestone M0); the first revisions arrive with M1's raw-print storage.
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine, pool

from alembic import context

# M1: point this at the SQLAlchemy metadata once models exist.
target_metadata = None


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set (see .env.example)")
    return url


def run_migrations_offline() -> None:
    context.configure(url=_database_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_database_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
