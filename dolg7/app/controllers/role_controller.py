from sqlalchemy import delete, func
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.core.exceptions import ConflictError
from app.models.profile import Profile
from app.models.role import Role, RoleCreate


def _save(role: Role, session: Session) -> Role:
    try:
        session.add(role)
        session.commit()
        session.refresh(role)
        return role
    except SQLAlchemyError:
        session.rollback()
        raise


class RoleController:
    @staticmethod
    def add_role(role: RoleCreate, session: Session) -> Role:
        name = role.name_role.strip()
        duplicate = session.exec(select(Role).where(Role.name_role == name)).first()
        if duplicate is not None:
            raise ConflictError("Роль с таким названием уже существует")
        return _save(Role(name_role=name), session)

    @staticmethod
    def get_role_by_id(role_id: int, session: Session) -> Role | None:
        return session.get(Role, role_id)

    @staticmethod
    def get_all_roles(session: Session) -> list[Role]:
        return list(session.exec(select(Role).order_by(Role.id_role)).all())

    @staticmethod
    def update_role(role_id: int, role: RoleCreate, session: Session) -> Role | None:
        current = session.get(Role, role_id)
        if current is None:
            return None
        name = role.name_role.strip()
        duplicate = session.exec(
            select(Role).where(Role.name_role == name, Role.id_role != role_id)
        ).first()
        if duplicate is not None:
            raise ConflictError("Роль с таким названием уже существует")
        current.name_role = name
        return _save(current, session)

    @staticmethod
    def delete_role(role_id: int, session: Session) -> bool:
        current = session.get(Role, role_id)
        if current is None:
            return False
        linked = session.exec(
            select(Profile.id_users).where(Profile.role_id == role_id).limit(1)
        ).first()
        if linked is not None:
            raise ConflictError("Нельзя удалить роль, связанную с профилями")
        try:
            session.delete(current)
            session.commit()
            return True
        except SQLAlchemyError:
            session.rollback()
            raise

    @staticmethod
    def get_role_by_name(name_role: str, session: Session) -> Role | None:
        return session.exec(
            select(Role).where(Role.name_role == name_role.strip())
        ).first()

    @staticmethod
    def count_roles(session: Session) -> int:
        return int(session.exec(select(func.count()).select_from(Role)).one())

    @staticmethod
    def get_roles_paginated(
        session: Session, offset: int = 0, limit: int = 10
    ) -> list[Role]:
        query = select(Role).order_by(Role.id_role).offset(offset).limit(limit)
        return list(session.exec(query).all())

    @staticmethod
    def search_roles(substring: str, session: Session) -> list[Role]:
        query = (
            select(Role)
            .where(Role.name_role.contains(substring, autoescape=True))
            .order_by(Role.id_role)
        )
        return list(session.exec(query).all())

    @staticmethod
    def get_roles_sorted(session: Session, descending: bool = False) -> list[Role]:
        order = Role.name_role.desc() if descending else Role.name_role
        return list(session.exec(select(Role).order_by(order, Role.id_role)).all())

    @staticmethod
    def delete_all_roles(session: Session) -> int:
        try:
            result = session.execute(delete(Role))
            deleted = result.rowcount
            session.commit()
            return deleted
        except SQLAlchemyError:
            session.rollback()
            raise
