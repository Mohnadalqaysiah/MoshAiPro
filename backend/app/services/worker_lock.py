"""
Mosh AI Pro v5 - Singleton Background Task Lock
Production runs the backend with `uvicorn --workers 2` (docker-compose.prod.yml),
meaning every background task started from FastAPI's lifespan() (strategy
checker, price alert checker, ...) would otherwise run once PER worker
process — duplicating market analysis calls and, worse, sending duplicate
Telegram alerts to real users.

A Postgres advisory lock (session-scoped, tied to one live connection) lets
exactly one worker "win" and run the loop; the others skip it entirely.
The lock is released automatically if that worker's connection ever drops
(process crash/restart), so a surviving worker can pick it back up.
"""
from typing import Optional
from sqlalchemy import text
from sqlalchemy.engine import Connection
from loguru import logger

from app.database import engine


def try_acquire_singleton_lock(key: int, task_name: str) -> Optional[Connection]:
    """Tries to become the single owner of a named background task across
    all worker processes.

    Returns an open Connection on success — keep a reference for the life
    of the task and only close it on shutdown, since closing it is what
    releases the lock. Returns None if another worker already owns it and
    this process should skip running the task entirely.
    """
    conn = engine.connect()
    try:
        got_lock = conn.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": key}).scalar()
        # pg_try_advisory_lock is session-scoped, not transaction-scoped — it
        # survives this commit. Committing just avoids leaving the connection
        # sitting "idle in transaction" for the task's entire lifetime.
        conn.commit()
    except Exception as e:
        # Transient DB hiccup while checking the lock — fail open (keep the
        # connection, don't enforce exclusivity this run) rather than lose
        # monitoring entirely in every worker.
        logger.warning(f"{task_name}: advisory lock check failed ({e}) — running unlocked")
        return conn

    if not got_lock:
        conn.close()
        logger.info(f"ℹ️ {task_name}: another worker already owns this task — skipping in this process")
        return None

    logger.info(f"🔒 {task_name}: acquired singleton lock in this worker")
    return conn
