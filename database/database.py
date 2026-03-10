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
    _migrate_db()


def _migrate_db():
    """Add new columns to existing tables without Alembic (idempotent)."""
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
        # Prevent indefinite blocking if another process holds a table lock.
        # With lock_timeout, ALTER TABLE fails fast instead of waiting forever.
        if not DATABASE_URL.startswith("sqlite"):
            try:
                conn.execute(text("SET lock_timeout = '5s'"))
            except Exception:
                pass
        for table, col, col_type in new_columns:
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                conn.commit()
            except Exception:
                conn.rollback()  # column already exists or lock timeout — safe to ignore
