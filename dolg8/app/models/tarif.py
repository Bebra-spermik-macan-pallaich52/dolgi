from decimal import Decimal

from pydantic import ConfigDict, field_validator, model_validator
from sqlalchemy import CheckConstraint
from sqlmodel import Field, Relationship, SQLModel


class TarifBase(SQLModel):
    model_config = ConfigDict(extra="forbid")

    tarif_name: str = Field(min_length=1, max_length=100)
    internet: int = Field(ge=0)
    count_minutes: int = Field(ge=0)
    count_sms: int = Field(ge=0)
    salary: Decimal = Field(ge=0, max_digits=10, decimal_places=2)

    @field_validator("tarif_name", mode="before")
    @classmethod
    def normalize_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class Tarif(TarifBase, table=True):
    __tablename__ = "tarifs"
    __table_args__ = (
        CheckConstraint(
            "internet >= 0 AND count_minutes >= 0 AND count_sms >= 0 AND salary >= 0",
            name="tarif_nonnegative",
        ),
    )

    id_tarif: int | None = Field(default=None, primary_key=True)
    clients: list["Client"] = Relationship(
        back_populates="tarif", sa_relationship_kwargs={"passive_deletes": "all"}
    )


class TarifCreate(TarifBase):
    pass


class TarifRead(TarifBase):
    id_tarif: int


class TarifUpdate(SQLModel):
    model_config = ConfigDict(extra="forbid")

    tarif_name: str | None = Field(default=None, min_length=1, max_length=100)
    internet: int | None = Field(default=None, ge=0)
    count_minutes: int | None = Field(default=None, ge=0)
    count_sms: int | None = Field(default=None, ge=0)
    salary: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)

    @field_validator("tarif_name", mode="before")
    @classmethod
    def normalize_name(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def reject_null(self):
        if any(getattr(self, name) is None for name in self.model_fields_set):
            raise ValueError("Поля тарифа не могут быть null.")
        return self


class TarifClientCount(SQLModel):
    tarif_name: str
    client_count: int


class TarifWithClientCount(TarifRead):
    client_count: int
