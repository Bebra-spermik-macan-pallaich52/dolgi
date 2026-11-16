from sqlmodel import SQLModel, create_engine

import app.models
from app.core.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={"connect_timeout": 5} if DATABASE_URL.startswith("postgresql") else {},
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def close_db() -> None:
    engine.dispose()
