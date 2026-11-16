from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.core.exceptions import ConflictError, NotFoundError
from app.core.persistence import save
from app.models.client import Client
from app.models.tarif import (
    Tarif,
    TarifClientCount,
    TarifCreate,
    TarifUpdate,
    TarifWithClientCount,
)


def _get_tarif(id_tarif: int, session: Session) -> Tarif:
    tarif = session.get(Tarif, id_tarif)
    if tarif is None:
        raise NotFoundError("Тариф не найден")
    return tarif


class TarifController:
    @staticmethod
    def get_all_tarifs(session: Session) -> list[Tarif]:
        return list(session.exec(select(Tarif).order_by(Tarif.id_tarif)).all())

    @staticmethod
    def get_tarif_by_client(phone: str, session: Session) -> Tarif:
        query = (
            select(Tarif)
            .join(Client, Client.id_tarif == Tarif.id_tarif)
            .where(Client.number_phone == phone)
        )
        tarif = session.exec(query).first()
        if tarif is None:
            raise NotFoundError("Тариф клиента не найден")
        return tarif

    @staticmethod
    def get_client_counts(session: Session) -> list[TarifClientCount]:
        return [
            TarifClientCount(tarif_name=tarif.tarif_name, client_count=tarif.client_count)
            for tarif in TarifController.get_tarifs_with_client_count(session)
        ]

    @staticmethod
    def count_clients_for_tarif(id_tarif: int, session: Session) -> int:
        _get_tarif(id_tarif, session)
        query = select(func.count(Client.number_phone)).where(Client.id_tarif == id_tarif)
        return int(session.exec(query).one())

    @staticmethod
    def update_tarif(id_tarif: int, tarif: TarifUpdate, session: Session) -> Tarif:
        current = _get_tarif(id_tarif, session)
        for field, value in tarif.model_dump(exclude_unset=True).items():
            setattr(current, field, value)
        return save(current, session)

    @staticmethod
    def add_tarif(tarif: TarifCreate, session: Session) -> Tarif:
        return save(Tarif(**tarif.model_dump()), session)

    @staticmethod
    def delete_tarif(id_tarif: int, session: Session) -> None:
        current = _get_tarif(id_tarif, session)
        linked = session.exec(
            select(Client.number_phone).where(Client.id_tarif == id_tarif).limit(1)
        ).first()
        if linked is not None:
            raise ConflictError("Нельзя удалить тариф, подключённый клиентам")
        try:
            session.delete(current)
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise

    @staticmethod
    def get_tarifs_with_client_count(session: Session) -> list[TarifWithClientCount]:
        query = (
            select(Tarif, func.count(Client.number_phone))
            .outerjoin(Client, Client.id_tarif == Tarif.id_tarif)
            .group_by(
                Tarif.id_tarif,
                Tarif.tarif_name,
                Tarif.internet,
                Tarif.count_minutes,
                Tarif.count_sms,
                Tarif.salary,
            )
            .order_by(Tarif.id_tarif)
        )
        return [
            TarifWithClientCount(**tarif.model_dump(), client_count=int(count))
            for tarif, count in session.exec(query).all()
        ]
