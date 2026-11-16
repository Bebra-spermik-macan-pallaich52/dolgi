import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.core.security import hash_password, verify_password
from app.db import database
from app.models.profile import Profile
from app.models.role import Role

logger = logging.getLogger(__name__)


def _profile_data(profile: Profile, require_password: bool) -> dict | None:
    email = profile.email
    password = profile.password
    if not isinstance(email, str) or not isinstance(password, str):
        return None
    email = email.strip()
    if not email or len(email) > 30 or email.count("@") != 1:
        return None
    local, domain = email.split("@")
    if not local or not domain or any(char.isspace() for char in email):
        return None
    if require_password and not password:
        return None
    if type(profile.role_id) is not int or profile.role_id <= 0:
        return None
    values = {"email": email, "password": password, "role_id": profile.role_id}
    for field in ("second_name", "first_name", "patronymic"):
        value = getattr(profile, field)
        if value is not None:
            if not isinstance(value, str) or len(value) > 50:
                return None
            value = value.strip() or None
        values[field] = value
    return values


class ProfileController:
    @staticmethod
    def add_profile(profile: Profile) -> Profile | None:
        values = _profile_data(profile, require_password=True)
        if values is None or profile.id_users is not None:
            return None
        try:
            with Session(database.engine) as session:
                if session.get(Role, values["role_id"]) is None:
                    return None
                duplicate = session.exec(
                    select(Profile).where(Profile.email == values["email"])
                ).first()
                if duplicate is not None:
                    return None
                values["password"] = hash_password(values["password"])
                created = Profile(**values)
                session.add(created)
                session.commit()
                session.refresh(created)
                return created
        except SQLAlchemyError:
            logger.error("Не удалось добавить профиль")
            return None

    @staticmethod
    def get_profile_by_id(profile_id: int) -> Profile | None:
        if type(profile_id) is not int or profile_id <= 0:
            return None
        try:
            with Session(database.engine) as session:
                return session.get(Profile, profile_id)
        except SQLAlchemyError:
            logger.error("Не удалось получить профиль")
            return None

    @staticmethod
    def get_all_profiles() -> list[Profile]:
        try:
            with Session(database.engine) as session:
                return list(session.exec(select(Profile).order_by(Profile.id_users)).all())
        except SQLAlchemyError:
            logger.error("Не удалось получить профили")
            return []

    @staticmethod
    def update_profile(profile_id: int, profile: Profile) -> Profile | None:
        values = _profile_data(profile, require_password=False)
        if values is None or type(profile_id) is not int or profile_id <= 0:
            return None
        try:
            with Session(database.engine) as session:
                current = session.get(Profile, profile_id)
                if current is None or session.get(Role, values["role_id"]) is None:
                    return None
                duplicate = session.exec(
                    select(Profile).where(
                        Profile.email == values["email"],
                        Profile.id_users != profile_id,
                    )
                ).first()
                if duplicate is not None:
                    return None
                password = values.pop("password")
                if password and password != current.password:
                    if not verify_password(password, current.password):
                        current.password = hash_password(password)
                for field, value in values.items():
                    setattr(current, field, value)
                session.add(current)
                session.commit()
                session.refresh(current)
                return current
        except SQLAlchemyError:
            logger.error("Не удалось изменить профиль")
            return None

    @staticmethod
    def delete_profile(profile_id: int) -> bool:
        if type(profile_id) is not int or profile_id <= 0:
            return False
        try:
            with Session(database.engine) as session:
                profile = session.get(Profile, profile_id)
                if profile is None:
                    return False
                session.delete(profile)
                session.commit()
                return True
        except SQLAlchemyError:
            logger.error("Не удалось удалить профиль")
            return False

    @staticmethod
    def authenticate(email: str, password: str) -> Profile | None:
        if not isinstance(email, str) or not isinstance(password, str) or not password:
            return None
        try:
            with Session(database.engine) as session:
                profile = session.exec(
                    select(Profile).where(Profile.email == email.strip())
                ).first()
                if profile is None or not verify_password(password, profile.password):
                    return None
                return profile
        except SQLAlchemyError:
            logger.error("Не удалось проверить профиль")
            return None

    @staticmethod
    def get_profiles_by_role(role_id: int) -> list[Profile]:
        if type(role_id) is not int or role_id <= 0:
            return []
        try:
            with Session(database.engine) as session:
                return list(
                    session.exec(
                        select(Profile)
                        .where(Profile.role_id == role_id)
                        .order_by(Profile.id_users)
                    ).all()
                )
        except SQLAlchemyError:
            logger.error("Не удалось получить профили роли")
            return []
