from pydantic import ConfigDict, field_validator
from sqlmodel import Field, Relationship, SQLModel


class Role(SQLModel, table=True):
    __tablename__ = "roles"

    id_role: int | None = Field(default=None, primary_key=True)
    name_role: str = Field(max_length=30, unique=True, index=True)
    profiles: list["Profile"] = Relationship(
        back_populates="role", sa_relationship_kwargs={"passive_deletes": "all"}
    )


class RoleCreate(SQLModel):
    model_config = ConfigDict(extra="forbid")

    name_role: str = Field(min_length=1, max_length=30)

    @field_validator("name_role", mode="before")
    @classmethod
    def normalize_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class RoleRead(RoleCreate):
    id_role: int
