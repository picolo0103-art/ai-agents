"""Database engine, session and Base for SQLAlchemy."""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./saas.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from database import models  # noqa: F401 — import to register models
    Base.metadata.create_all(bind=engine)
    # NOTE: _migrate_db() is intentionally NOT called here.
    # It is executed via run_migrations() from a background retry-loop in
    # api/main.py so that startup is never blocked by PostgreSQL lock contention
    # with the old running instance during a rolling Render deploy.


def run_migrations():
    """Run idempotent column migrations.

    Designed to be called from a background retry-loop (see api/main.py).
    * Skips columns that already exist   → truly idempotent, no lock needed.
    * Uses lock_timeout = '3s' for missing columns → fails fast instead of
      blocking forever; raises on lock failure so the caller can back off and
      retry.
    Safe to call multiple times.
    """
    _migrate_db()


def _migrate_db():
    """Add new columns to existing tables without Alembic.

    For each column:
      - Already exists  → skip (cheap read, no table lock).
      - Missing         → ALTER TABLE … ADD COLUMN with lock_timeout = '3s'.
                          Raises sqlalchemy.exc.OperationalError (LockNotAvailable)
                          on timeout — let the caller retry.
    """
    from sqlalchemy import text
    new_columns = [
        ("tenants", "plan",                   "VARCHAR(20)  DEFAULT 'free'"),
        ("tenants", "stripe_customer_id",     "VARCHAR(100)"),
        ("tenants", "stripe_subscription_id", "VARCHAR(100)"),
        ("tenants", "subscription_status",    "VARCHAR(30)  DEFAULT 'inactive'"),
        ("tenants", "messages_this_month",    "INTEGER      DEFAULT 0"),
        ("tenants", "messages_reset_at",      "TIMESTAMP"),
        ("users",   "email_verified",         "BOOLEAN      DEFAULT FALSE"),
        ("users",   "email_verify_token",     "VARCHAR(64)"),
    ]
    with engine.connect() as conn:
        # Short lock_timeout: ALTER TABLE raises LockNotAvailable instead of
        # blocking indefinitely.  The retry-loop in main.py handles it.
        if not DATABASE_URL.startswith("sqlite"):
            conn.execute(text("SET lock_timeout = '3s'"))

        for table, col, col_type in new_columns:
            # ── 1. Check existence (read-only, no table lock needed) ─────────
            if DATABASE_URL.startswith("sqlite"):
                rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
                if any(r[1] == col for r in rows):
                    continue
            else:
                row = conn.execute(
                    text(
                        "SELECT 1 FROM information_schema.columns "
                        "WHERE table_name = :t AND column_name = :c"
                    ),
                    {"t": table, "c": col},
                ).fetchone()
                if row is not None:
                    continue  # already exists — nothing to do

            # ── 2. Column is genuinely missing — add it ──────────────────────
            # May raise OperationalError (LockNotAvailable) if lock_timeout
            # fires; propagates to the caller's retry-loop.
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
            conn.commit()
