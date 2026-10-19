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
    from app.models import user, payment, market_config, affiliate, trade_journal, game_progress, telegram_broadcast, shadow_signal, signal_feature, strategy_backtest, deleted_account, review, signal_unlock  # noqa: F401
    # (2026-10-19) قفل استشاري حول create_all: عاملا uvicorn يُنشئان الجداول الجديدة معاً فيتسابقان على CREATE TABLE
    # (نفس سبب قفل 90210008 أدناه). الثاني ينتظر ثم يجدها موجودة.
    if engine.dialect.name == "postgresql":
        from sqlalchemy import text
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as _lc:
            _lc.execute(text("SELECT pg_advisory_lock(90210009)"))
            try:
                Base.metadata.create_all(bind=engine)
            finally:
                _lc.execute(text("SELECT pg_advisory_unlock(90210009)"))
    else:
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
        # (2026-10-18) عمود نسخة التحقق لصفقات الظل — create_all لا يضيف أعمدة لجدول قائم. idempotent.
        # (المرحلة 1.1) قفل استشاري: عاملا uvicorn (--workers 2) يشغّلان init_db معاً، فكان CREATE INDEX IF NOT EXISTS
        # يتسابق ويرمي "duplicate key … pg_class_relname_nsp_index" (النتيجة سليمة لكن التحذير مضلّل). القفل يسلسلهما:
        # الثاني ينتظر ثم يجد العمود والفهرس فلا يفعل شيئاً. المفتاح خاص بهذه الخطوة (90210008).
        try:
            from sqlalchemy import text
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                conn.execute(text("SELECT pg_advisory_lock(90210008)"))
                try:
                    # (2026-10-19) من حظر البوت — services/telegram_reach.py. أولاً: نموذج User يقرأه
                    # كل استعلام مستخدم (الدخول نفسه) — لا يُعلَّق على نجاح خطوة قبله
                    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS telegram_blocked_at TIMESTAMPTZ"))
                    conn.execute(text("ALTER TABLE shadow_signals ADD COLUMN IF NOT EXISTS levels_version INTEGER"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_shadow_signals_levels_version ON shadow_signals (levels_version)"))
                finally:
                    conn.execute(text("SELECT pg_advisory_unlock(90210008)"))
        except Exception as e:
            print(f"⚠️ shadow_signals.levels_version: {e}")
    print("✅ Database initialized successfully")
