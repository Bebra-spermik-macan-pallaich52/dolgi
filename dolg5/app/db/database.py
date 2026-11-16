"""Создание и закрытие пула соединений PostgreSQL."""

import logging

from psycopg_pool import ConnectionPool

from app.core.config import DATABASE_URL

logger = logging.getLogger(__name__)
_pool: ConnectionPool | None = None


def init_db() -> None:
    """Создать пул и дождаться первого соединения с базой."""
    global _pool
    if _pool is not None:
        return
    pool = ConnectionPool(
        conninfo=DATABASE_URL, min_size=1, max_size=10,
        timeout=5, open=False,
    )
    try:
        pool.open(wait=True, timeout=5)
    except BaseException:
        pool.close()
        raise
    _pool = pool
    logger.info("Пул соединений создан")


def close_db() -> None:
    """Закрыть пул; повторный вызов безопасен."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
        logger.info("Пул соединений закрыт")


def get_engine() -> ConnectionPool:
    """Вернуть инициализированный пул для session.py."""
    if _pool is None:
        raise RuntimeError("Пул не инициализирован. Сначала вызовите init_db().")
    return _pool
