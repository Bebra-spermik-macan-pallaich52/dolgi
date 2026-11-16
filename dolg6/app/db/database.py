from sqlmodel import SQLModel, create_engine

import app.models
from app.core.config import database_url

engine = create_engine(database_url, pool_pre_ping=True, pool_recycle=3600)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def close_db() -> None:
    engine.dispose()
