from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlmodel import Session

from app.controllers.client_controller import ClientController
from app.db.session import get_session
from app.models.client import (
    ClientBirthdayRead,
    ClientCreate,
    ClientPhoneRead,
    ClientRead,
    ClientUpdate,
    ClientWithTarif,
)

router = APIRouter(prefix="/clients", tags=["Clients"])
PhonePath = Annotated[str, Path(pattern=r"^\+?[0-9]{7,15}$")]


@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
def add_client(client: ClientCreate, session: Session = Depends(get_session)):
    return ClientController.add_client(client, session)


@router.get("", response_model=list[ClientWithTarif])
def get_clients_with_tarif(session: Session = Depends(get_session)):
    return ClientController.get_clients_with_tarif(session)


@router.get("/search/phone", response_model=list[ClientPhoneRead])
def get_clients_by_phone_code(
    phone: Annotated[str, Query(pattern=r"^\+?[0-9]{1,15}$")],
    session: Session = Depends(get_session),
):
    return ClientController.get_clients_by_phone_code(phone, session)


@router.get("/sorted-by-birthday", response_model=list[ClientBirthdayRead])
def get_clients_sorted_by_birthday(session: Session = Depends(get_session)):
    return ClientController.get_clients_sorted_by_birthday(session)


@router.get("/search/passport-year", response_model=list[ClientRead])
def get_clients_by_passport_year(
    year: Annotated[int, Query(ge=1, le=9999)], session: Session = Depends(get_session)
):
    return ClientController.get_clients_by_passport_year(year, session)


@router.get("/search/tarif-cost", response_model=list[ClientWithTarif])
def get_clients_by_tarif_cost(
    min_salary: Annotated[Decimal, Query(alias="minSalary", ge=0)],
    session: Session = Depends(get_session),
):
    return ClientController.get_clients_by_tarif_cost(min_salary, session)


@router.patch("/tarif")
def assign_tarif(
    phone: Annotated[str, Query(pattern=r"^\+?[0-9]{7,15}$")],
    id_tarif: Annotated[int, Query(gt=0)],
    session: Session = Depends(get_session),
):
    ClientController.assign_tarif(phone, id_tarif, session)
    return {"message": "Тариф клиента изменён"}


@router.put("/{phone}", response_model=ClientRead)
def update_client(phone: PhonePath, client: ClientUpdate, session: Session = Depends(get_session)):
    return ClientController.update_client(phone, client, session)


@router.delete("/{phone}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(phone: PhonePath, session: Session = Depends(get_session)) -> Response:
    ClientController.delete_client(phone, session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
