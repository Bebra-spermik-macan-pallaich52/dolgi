from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlmodel import Session

from app.controllers.role_controller import RoleController
from app.db.session import get_session
from app.models.role import RoleCreate, RoleRead

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.post("/", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
def add_role(role: RoleCreate, session: Session = Depends(get_session)):
    return RoleController.add_role(role, session)


@router.get("/", response_model=list[RoleRead])
def get_all_roles(session: Session = Depends(get_session)):
    return RoleController.get_all_roles(session)


@router.delete("/")
def delete_all_roles(session: Session = Depends(get_session)):
    return {"deleted": RoleController.delete_all_roles(session)}


@router.get("/count")
def count_roles(session: Session = Depends(get_session)):
    return {"count": RoleController.count_roles(session)}


@router.get("/by-name", response_model=RoleRead)
def get_role_by_name(
    name_role: str = Query(min_length=1, max_length=30),
    session: Session = Depends(get_session),
):
    role = RoleController.get_role_by_name(name_role, session)
    if role is None:
        raise HTTPException(status_code=404, detail="Роль не найдена")
    return role


@router.get("/page", response_model=list[RoleRead])
def get_roles_paginated(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    session: Session = Depends(get_session),
):
    return RoleController.get_roles_paginated(session, offset=offset, limit=limit)


@router.get("/search", response_model=list[RoleRead])
def search_roles(
    substring: str = Query(min_length=1),
    session: Session = Depends(get_session),
):
    return RoleController.search_roles(substring, session)


@router.get("/sorted", response_model=list[RoleRead])
def get_roles_sorted(
    descending: bool = False, session: Session = Depends(get_session)
):
    return RoleController.get_roles_sorted(session, descending=descending)


@router.get("/{role_id}", response_model=RoleRead)
def get_role_by_id(
    role_id: int = Path(gt=0), session: Session = Depends(get_session)
):
    role = RoleController.get_role_by_id(role_id, session)
    if role is None:
        raise HTTPException(status_code=404, detail="Роль не найдена")
    return role


@router.put("/{role_id}", response_model=RoleRead)
def update_role(
    role: RoleCreate,
    role_id: int = Path(gt=0),
    session: Session = Depends(get_session),
):
    updated = RoleController.update_role(role_id, role, session)
    if updated is None:
        raise HTTPException(status_code=404, detail="Роль не найдена")
    return updated


@router.delete("/{role_id}")
def delete_role(
    role_id: int = Path(gt=0), session: Session = Depends(get_session)
):
    if not RoleController.delete_role(role_id, session):
        raise HTTPException(status_code=404, detail="Роль не найдена")
    return {"message": "Роль удалена"}
