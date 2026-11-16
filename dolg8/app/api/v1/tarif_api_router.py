from typing import Annotated

from fastapi import APIRouter, Depends, Path, Response, status
from sqlmodel import Session

from app.controllers.tarif_controller import TarifController
from app.db.session import get_session
from app.models.tarif import (
    TarifClientCount,
    TarifCreate,
    TarifRead,
    TarifUpdate,
    TarifWithClientCount,
)

router = APIRouter(prefix="/tarifs", tags=["Tarifs"])
SessionDep = Annotated[Session, Depends(get_session)]
TarifId = Annotated[int, Path(gt=0)]
Phone = Annotated[str, Path(pattern=r"^\+?[0-9]{7,15}$")]


@router.get("", response_model=list[TarifRead], summary="Список тарифов")
def get_all_tarifs(session: SessionDep):
    return TarifController.get_all_tarifs(session)


@router.post(
    "", response_model=TarifRead, status_code=status.HTTP_201_CREATED,
    summary="Добавить тариф",
)
def add_tarif(tarif: TarifCreate, session: SessionDep):
    return TarifController.add_tarif(tarif, session)


@router.get(
    "/by-client/{phone}", response_model=TarifRead, summary="Тариф клиента"
)
def get_tarif_by_client(phone: Phone, session: SessionDep):
    return TarifController.get_tarif_by_client(phone, session)


@router.get(
    "/stats/client-count", response_model=list[TarifClientCount],
    summary="Количество клиентов на каждом тарифе",
)
def get_client_counts(session: SessionDep):
    return TarifController.get_client_counts(session)


@router.get(
    "/with-client-count", response_model=list[TarifWithClientCount],
    summary="Тарифы с количеством клиентов",
)
def get_tarifs_with_client_count(session: SessionDep):
    return TarifController.get_tarifs_with_client_count(session)


@router.get(
    "/{id_tarif}/client-count", response_model=dict[str, int],
    summary="Количество клиентов тарифа",
)
def count_clients_for_tarif(id_tarif: TarifId, session: SessionDep):
    return {
        "tarif_id": id_tarif,
        "count": TarifController.count_clients_for_tarif(id_tarif, session),
    }


@router.patch("/{id_tarif}", response_model=TarifRead, summary="Изменить тариф")
def update_tarif(id_tarif: TarifId, tarif: TarifUpdate, session: SessionDep):
    return TarifController.update_tarif(id_tarif, tarif, session)


@router.delete(
    "/{id_tarif}", status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response, summary="Удалить тариф",
)
def delete_tarif(id_tarif: TarifId, session: SessionDep) -> Response:
    TarifController.delete_tarif(id_tarif, session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
