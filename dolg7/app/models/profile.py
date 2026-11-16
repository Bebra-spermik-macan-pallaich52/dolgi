from pydantic import ConfigDict, field_validator
from sqlmodel import Field, Relationship, SQLModel

from .role import Role


def _email(value: str) -> str:
    value = value.strip()
    if value.count("@") != 1 or any(char.isspace() for char in value):
        raise ValueError("Некорректный email.")
    local, domain = value.split("@")
    if not local or not domain:
        raise ValueError("Некорректный email.")
    return value


class Profile(SQLModel, table=True):
    __tablename__ = "profiles"

    id_users: int | None = Field(default=None, primary_key=True)
    first_name: str | None = Field(default=None, max_length=50)
    second_name: str | None = Field(default=None, max_length=50)
    patronymic: str | None = Field(default=None, max_length=50)
    role_id: int = Field(default=1, foreign_key="roles.id_role")
    email: str = Field(max_length=30, unique=True)
    password: str = Field(max_length=200, repr=False)
    role: Role | None = Relationship(back_populates="profiles")


class ProfileBase(SQLModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str | None = Field(default=None, max_length=50)
    second_name: str | None = Field(default=None, max_length=50)
    patronymic: str | None = Field(default=None, max_length=50)
    role_id: int = Field(default=1, gt=0)
    email: str = Field(min_length=3, max_length=30)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _email(value)

    @field_validator("first_name", "second_name", "patronymic", mode="before")
    @classmethod
    def normalize_name(cls, value):
        return value.strip() or None if isinstance(value, str) else value


class ProfileCreate(ProfileBase):
    password: str = Field(min_length=1, max_length=200, repr=False)


class ProfileUpdate(ProfileBase):
    password: str | None = Field(default=None, min_length=1, max_length=200, repr=False)


class ProfileRead(ProfileBase):
    id_users: int


class ProfileLogin(SQLModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=30)
    password: str = Field(min_length=1, max_length=200, repr=False)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _email(value)
