import logging

from sqlalchemy import delete, func
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.db import database
from app.models.profile import Profile
from app.models.role import Role

logger = logging.getLogger(__name__)


class RoleController:
    @staticmethod
    def add_role(role: Role) -> Role | None:
        name = role.name_role.strip() if isinstance(role.name_role, str) else ""
        if role.id_role is not None or not name or len(name) > 30:
            return None
        try:
            with Session(database.engine) as session:
                duplicate = session.exec(select(Role).where(Role.name_role == name)).first()
                if duplicate is not None:
                    return None
                created = Role(name_role=name)
                session.add(created)
                session.commit()
                session.refresh(created)
                return created
        except SQLAlchemyError:
            logger.error("Не удалось добавить роль")
            return None

    @staticmethod
    def get_role_by_id(role_id: int) -> Role | None:
        if role_id <= 0:
            return None
        try:
            with Session(database.engine) as session:
                return session.get(Role, role_id)
        except SQLAlchemyError:
            logger.error("Не удалось найти роль")
            return None

    @staticmethod
    def get_all_roles() -> list[Role]:
        try:
            with Session(database.engine) as session:
                return list(session.exec(select(Role).order_by(Role.id_role)).all())
        except SQLAlchemyError:
            logger.error("Не удалось получить роли")
            return []

    @staticmethod
    def update_role(role_id: int, role: Role) -> Role | None:
        name = role.name_role.strip() if isinstance(role.name_role, str) else ""
        if role_id <= 0 or not name or len(name) > 30:
            return None
        try:
            with Session(database.engine) as session:
                current = session.get(Role, role_id)
                if current is None:
                    return None
                duplicate = session.exec(
                    select(Role).where(Role.name_role == name, Role.id_role != role_id)
                ).first()
                if duplicate is not None:
                    return None
                current.name_role = name
                session.commit()
                session.refresh(current)
                return current
        except SQLAlchemyError:
            logger.error("Не удалось изменить роль")
            return None

    @staticmethod
    def delete_role(role_id: int) -> bool:
        if role_id <= 0:
            return False
        try:
            with Session(database.engine) as session:
                current = session.get(Role, role_id)
                if current is None:
                    return False
                linked = session.exec(
                    select(Profile.id_users).where(Profile.role_id == role_id).limit(1)
                ).first()
                if linked is not None:
                    return False
                session.delete(current)
                session.commit()
                return True
        except SQLAlchemyError:
            logger.error("Не удалось удалить роль")
            return False

    @staticmethod
    def get_role_by_name(name_role: str) -> Role | None:
        name = name_role.strip()
        if not name:
            return None
        try:
            with Session(database.engine) as session:
                return session.exec(select(Role).where(Role.name_role == name)).first()
        except SQLAlchemyError:
            logger.error("Не удалось найти роль")
            return None

    @staticmethod
    def count_roles() -> int:
        try:
            with Session(database.engine) as session:
                return int(session.exec(select(func.count()).select_from(Role)).one())
        except SQLAlchemyError:
            logger.error("Не удалось подсчитать роли")
            return 0

    @staticmethod
    def get_roles_paginated(offset: int = 0, limit: int = 10) -> list[Role]:
        if offset < 0 or limit < 0:
            return []
        try:
            with Session(database.engine) as session:
                query = select(Role).order_by(Role.id_role).offset(offset).limit(limit)
                return list(session.exec(query).all())
        except SQLAlchemyError:
            logger.error("Не удалось получить страницу ролей")
            return []

    @staticmethod
    def search_roles(substring: str) -> list[Role]:
        try:
            with Session(database.engine) as session:
                query = select(Role).where(
                    Role.name_role.contains(substring, autoescape=True)
                ).order_by(Role.id_role)
                return list(session.exec(query).all())
        except SQLAlchemyError:
            logger.error("Не удалось найти роли")
            return []

    @staticmethod
    def get_roles_sorted(descending: bool = False) -> list[Role]:
        try:
            with Session(database.engine) as session:
                name_order = Role.name_role.desc() if descending else Role.name_role
                query = select(Role).order_by(name_order, Role.id_role)
                return list(session.exec(query).all())
        except SQLAlchemyError:
            logger.error("Не удалось отсортировать роли")
            return []

    @staticmethod
    def delete_all_roles() -> int:
        try:
            with Session(database.engine) as session:
                result = session.execute(delete(Role))
                deleted = result.rowcount
                session.commit()
                return deleted
        except SQLAlchemyError:
            logger.error("Не удалось удалить роли")
            return 0
