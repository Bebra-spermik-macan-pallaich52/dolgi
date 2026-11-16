import re
from datetime import date

from pydantic import ConfigDict, field_validator, model_validator
from sqlalchemy import CheckConstraint
from sqlmodel import Field, Relationship, SQLModel

from .tarif import Tarif, TarifRead


def _phone(value: str) -> str:
    value = value.strip()
    if re.fullmatch(r"\+?[0-9]{7,15}", value) is None:
        raise ValueError("Номер должен содержать от 7 до 15 цифр и необязательный +.")
    return value


def _passport(value: str, length: int) -> str:
    if re.fullmatch(rf"[0-9]{{{length}}}", value) is None:
        raise ValueError(f"Ожидается {length} цифр.")
    return value


class ClientBase(SQLModel):
    model_config = ConfigDict(extra="forbid")

    number_phone: str = Field(min_length=7, max_length=16)
    id_tarif: int | None = Field(default=None, gt=0)
    lastname: str = Field(min_length=1, max_length=50)
    firstname: str = Field(min_length=1, max_length=50)
    patronymic_name: str | None = Field(default=None, max_length=50)
    date_birthday: date
    pasport_serial: str = Field(min_length=4, max_length=4)
    pasport_number: str = Field(min_length=6, max_length=6)
    date_issue: date

    @field_validator("number_phone")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        return _phone(value)

    @field_validator("lastname", "firstname", mode="before")
    @classmethod
    def normalize_name(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("patronymic_name", mode="before")
    @classmethod
    def normalize_patronymic(cls, value):
        return value.strip() or None if isinstance(value, str) else value

    @field_validator("pasport_serial")
    @classmethod
    def validate_serial(cls, value: str) -> str:
        return _passport(value, 4)

    @field_validator("pasport_number")
    @classmethod
    def validate_number(cls, value: str) -> str:
        return _passport(value, 6)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.date_birthday > date.today() or self.date_issue > date.today():
            raise ValueError("Дата не может быть в будущем.")
        if self.date_issue < self.date_birthday:
            raise ValueError("Дата выдачи паспорта не может быть раньше даты рождения.")
        return self


class Client(ClientBase, table=True):
    __tablename__ = "clients"
    __table_args__ = (
        CheckConstraint("date_issue >= date_birthday", name="client_dates_order"),
    )

    number_phone: str = Field(primary_key=True, max_length=16)
    id_tarif: int | None = Field(default=None, foreign_key="tarifs.id_tarif", gt=0)
    tarif: Tarif | None = Relationship(back_populates="clients")


class ClientCreate(ClientBase):
    pass


class ClientRead(ClientBase):
    pass


class ClientUpdate(SQLModel):
    model_config = ConfigDict(extra="forbid")

    number_phone: str | None = Field(default=None, min_length=7, max_length=16)
    id_tarif: int | None = Field(default=None, gt=0)
    lastname: str | None = Field(default=None, min_length=1, max_length=50)
    firstname: str | None = Field(default=None, min_length=1, max_length=50)
    patronymic_name: str | None = Field(default=None, max_length=50)
    date_birthday: date | None = None
    pasport_serial: str | None = Field(default=None, min_length=4, max_length=4)
    pasport_number: str | None = Field(default=None, min_length=6, max_length=6)
    date_issue: date | None = None

    @field_validator("number_phone")
    @classmethod
    def normalize_phone(cls, value):
        return _phone(value) if value is not None else value

    @field_validator("lastname", "firstname", mode="before")
    @classmethod
    def normalize_name(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("patronymic_name", mode="before")
    @classmethod
    def normalize_patronymic(cls, value):
        return value.strip() or None if isinstance(value, str) else value

    @field_validator("pasport_serial")
    @classmethod
    def validate_serial(cls, value):
        return _passport(value, 4) if value is not None else value

    @field_validator("pasport_number")
    @classmethod
    def validate_number(cls, value):
        return _passport(value, 6) if value is not None else value

    @model_validator(mode="after")
    def reject_null(self):
        required = self.model_fields_set - {"id_tarif", "patronymic_name"}
        if any(getattr(self, name) is None for name in required):
            raise ValueError("Обязательные поля клиента не могут быть null.")
        return self


class ClientPhoneRead(SQLModel):
    number_phone: str
    lastname: str
    firstname: str


class ClientBirthdayRead(SQLModel):
    full_name: str
    date_birthday: date


class ClientWithTarif(ClientRead):
    tarif: TarifRead | None
