from collections.abc import Iterator

from sqlmodel import Session

from app.db import database


def get_session() -> Iterator[Session]:
    with Session(database.engine) as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
