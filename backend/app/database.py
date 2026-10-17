"""
Mosh AI Pro v5 - Database Configuration
PostgreSQL setup with SQLAlchemy ORM
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from app.config import get_settings

settings = get_settings()

# Create SQLAlchemy engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    echo=settings.DEBUG
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI to get database session
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database - create all tables"""
    # Import all models so SQLAlchemy knows about them
    from app.models import user, payment, market_config, affiliate, trade_journal, game_progress, telegram_broadcast, shadow_signal, signal_feature, strategy_backtest, deleted_account, review  # noqa: F401
    Base.metadata.create_all(bind=engine)
    # (2026-10-16) قيمة BREAKEVEN لنوع signalstatus القائم بـPostgres — create_all لا يعدّل نوع enum موجوداً.
    # ADD VALUE لا يعمل داخل معاملة بإصدارات قديمة ← اتصال autocommit. idempotent (IF NOT EXISTS).
    if engine.dialect.name == "postgresql":
        try:
            from sqlalchemy import text
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                conn.execute(text("ALTER TYPE signalstatus ADD VALUE IF NOT EXISTS 'BREAKEVEN'"))
        except Exception as e:
            print(f"⚠️ signalstatus BREAKEVEN: {e}")
    print("✅ Database initialized successfully")
