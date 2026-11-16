from sqlmodel import Field, Relationship, SQLModel

from app.models.role import Role


class Profile(SQLModel, table=True):
    __tablename__ = "profiles"

    id_users: int | None = Field(default=None, primary_key=True)
    second_name: str | None = Field(default=None, max_length=50)
    first_name: str | None = Field(default=None, max_length=50)
    patronymic: str | None = Field(default=None, max_length=50)
    role_id: int = Field(default=1, foreign_key="roles.id_role")
    email: str = Field(max_length=30, unique=True)
    password: str = Field(default="", max_length=200, repr=False)
    role: Role | None = Relationship(back_populates="profiles")
