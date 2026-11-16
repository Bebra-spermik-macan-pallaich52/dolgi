from sqlmodel import Field, Relationship, SQLModel


class Role(SQLModel, table=True):
    __tablename__ = "roles"

    id_role: int | None = Field(default=None, primary_key=True)
    name_role: str = Field(max_length=30, unique=True, index=True)
    profiles: list["Profile"] = Relationship(
        back_populates="role", sa_relationship_kwargs={"passive_deletes": "all"}
    )
