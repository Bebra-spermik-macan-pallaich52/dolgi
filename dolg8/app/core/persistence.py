from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session


def save(entity, session: Session):
    try:
        session.add(entity)
        session.commit()
        session.refresh(entity)
        return entity
    except SQLAlchemyError:
        session.rollback()
        raise
