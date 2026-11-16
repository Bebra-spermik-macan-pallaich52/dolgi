from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.core.exceptions import ConflictError
from app.core.security import hash_password, verify_password
from app.models.profile import Profile, ProfileCreate, ProfileUpdate
from app.models.role import Role


class ProfileController:
    @staticmethod
    def add_profile(profile: ProfileCreate, session: Session) -> Profile:
        try:
            if session.get(Role, profile.role_id) is None:
                raise ConflictError("Роль не найдена")
            duplicate = session.exec(
                select(Profile).where(Profile.email == profile.email)
            ).first()
            if duplicate is not None:
                raise ConflictError("Профиль с таким email уже существует")
            created = Profile(
                **profile.model_dump(exclude={"password"}),
                password=hash_password(profile.password),
            )
            session.add(created)
            session.commit()
            session.refresh(created)
            return created
        except SQLAlchemyError:
            session.rollback()
            raise

    @staticmethod
    def get_profile_by_id(profile_id: int, session: Session) -> Profile | None:
        return session.get(Profile, profile_id)

    @staticmethod
    def get_all_profiles(session: Session) -> list[Profile]:
        return list(session.exec(select(Profile).order_by(Profile.id_users)).all())

    @staticmethod
    def update_profile(
        profile_id: int, profile: ProfileUpdate, session: Session
    ) -> Profile | None:
        try:
            current = session.get(Profile, profile_id)
            if current is None:
                return None
            if session.get(Role, profile.role_id) is None:
                raise ConflictError("Роль не найдена")
            duplicate = session.exec(
                select(Profile).where(
                    Profile.email == profile.email,
                    Profile.id_users != profile_id,
                )
            ).first()
            if duplicate is not None:
                raise ConflictError("Профиль с таким email уже существует")
            password = profile.password
            if password is not None and password != current.password:
                if not verify_password(password, current.password):
                    current.password = hash_password(password)
            for field, value in profile.model_dump(exclude={"password"}).items():
                setattr(current, field, value)
            session.add(current)
            session.commit()
            session.refresh(current)
            return current
        except SQLAlchemyError:
            session.rollback()
            raise

    @staticmethod
    def delete_profile(profile_id: int, session: Session) -> bool:
        try:
            profile = session.get(Profile, profile_id)
            if profile is None:
                return False
            session.delete(profile)
            session.commit()
            return True
        except SQLAlchemyError:
            session.rollback()
            raise

    @staticmethod
    def authenticate(email: str, password: str, session: Session) -> Profile | None:
        profile = session.exec(
            select(Profile).where(Profile.email == email.strip())
        ).first()
        if profile is None or not verify_password(password, profile.password):
            return None
        return profile

    @staticmethod
    def get_profiles_by_role(role_id: int, session: Session) -> list[Profile]:
        return list(
            session.exec(
                select(Profile)
                .where(Profile.role_id == role_id)
                .order_by(Profile.id_users)
            ).all()
        )
