"""Одна транзакция на контекст курсора."""

from collections.abc import Iterator
from contextlib import contextmanager

from psycopg import Cursor

from app.db.database import get_engine


@contextmanager
def get_cursor() -> Iterator[Cursor]:
    """Выдать курсор; commit при успехе, rollback при исключении.

    Контекст connection() также возвращает соединение в пул.
    """
    with get_engine().connection() as conn:
        with conn.cursor() as cur:
            yield cur
