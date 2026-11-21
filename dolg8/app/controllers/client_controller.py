from datetime import date
from decimal import Decimal

from sqlmodel import Session, select

from app.core.exceptions import ConflictError, NotFoundError
from app.models.client import (
    Client,
    ClientBirthdayRead,
    ClientCreate,
    ClientPhoneRead,
    ClientUpdate,
    ClientWithTarif,
)
from app.models.tarif import Tarif, TarifRead


def _get_client(phone: str, session: Session) -> Client:
    client = session.get(Client, phone)
    if client is None:
        raise NotFoundError("Клиент не найден")
    return client


def _check_tarif(id_tarif: int | None, session: Session) -> None:
    if id_tarif is not None and session.get(Tarif, id_tarif) is None:
        raise NotFoundError("Тариф не найден")


def _with_tarif(rows) -> list[ClientWithTarif]:
    return [
        ClientWithTarif(
            **client.model_dump(),
            tarif=TarifRead.model_validate(tarif) if tarif is not None else None,
        )
        for client, tarif in rows
    ]


class ClientController:
    @staticmethod
    def add_client(client: ClientCreate, session: Session) -> Client:
        if session.get(Client, client.number_phone) is not None:
            raise ConflictError("Клиент с таким номером телефона уже существует")
        _check_tarif(client.id_tarif, session)
        current = Client.model_validate(client)
        session.add(current)
        session.commit()
        session.refresh(current)
        return current

    @staticmethod
    def get_clients_by_phone_code(phone: str, session: Session) -> list[ClientPhoneRead]:
        query = (
            select(Client.number_phone, Client.lastname, Client.firstname)
            .where(Client.number_phone.startswith(phone, autoescape=True))
            .order_by(Client.number_phone)
        )
        return [
            ClientPhoneRead(number_phone=number, lastname=lastname, firstname=firstname)
            for number, lastname, firstname in session.exec(query).all()
        ]

    @staticmethod
    def get_clients_sorted_by_birthday(session: Session) -> list[ClientBirthdayRead]:
        query = select(Client).order_by(Client.date_birthday, Client.number_phone)
        return [
            ClientBirthdayRead(
                full_name=" ".join(
                    name for name in (client.lastname, client.firstname, client.patronymic_name)
                    if name
                ),
                date_birthday=client.date_birthday,
            )
            for client in session.exec(query).all()
        ]

    @staticmethod
    def get_clients_by_passport_year(year: int, session: Session) -> list[Client]:
        if year >= 9999:
            return []
        query = (
            select(Client)
            .where(Client.date_issue >= date(year + 1, 1, 1))
            .order_by(Client.number_phone)
        )
        return list(session.exec(query).all())

    @staticmethod
    def get_clients_by_tarif_cost(
        min_salary: Decimal, session: Session
    ) -> list[ClientWithTarif]:
        query = (
            select(Client, Tarif)
            .join(Tarif, Client.id_tarif == Tarif.id_tarif)
            .where(Tarif.salary > min_salary)
            .order_by(Client.number_phone)
        )
        return _with_tarif(session.exec(query).all())

    @staticmethod
    def get_clients_with_tarif(session: Session) -> list[ClientWithTarif]:
        query = (
            select(Client, Tarif)
            .outerjoin(Tarif, Client.id_tarif == Tarif.id_tarif)
            .order_by(Client.number_phone)
        )
        return _with_tarif(session.exec(query).all())

    @staticmethod
    def update_client(phone: str, client: ClientUpdate, session: Session) -> Client:
        current = _get_client(phone, session)
        values = {**current.model_dump(), **client.model_dump(exclude_unset=True)}
        validated = ClientCreate.model_validate(values)
        if validated.number_phone != phone:
            duplicate = session.get(Client, validated.number_phone)
            if duplicate is not None:
                raise ConflictError("Клиент с таким номером телефона уже существует")
        _check_tarif(validated.id_tarif, session)
        for field, value in validated.model_dump().items():
            setattr(current, field, value)
        session.add(current)
        session.commit()
        session.refresh(current)
        return current

    @staticmethod
    def delete_client(phone: str, session: Session) -> None:
        client = _get_client(phone, session)
        session.delete(client)
        session.commit()

    @staticmethod
    def assign_tarif(phone: str, id_tarif: int, session: Session) -> Client:
        client = _get_client(phone, session)
        _check_tarif(id_tarif, session)
        client.id_tarif = id_tarif
        session.add(client)
        session.commit()
        session.refresh(client)
        return client
