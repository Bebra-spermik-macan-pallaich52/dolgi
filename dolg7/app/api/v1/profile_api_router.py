from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlmodel import Session

from app.controllers.profile_controller import ProfileController
from app.db.session import get_session
from app.models.profile import ProfileCreate, ProfileLogin, ProfileRead, ProfileUpdate

router = APIRouter(prefix="/profiles", tags=["Profiles"])
SessionDep = Annotated[Session, Depends(get_session)]
ProfileId = Annotated[int, Path(gt=0)]


@router.get("/", response_model=list[ProfileRead], summary="Все профили")
def get_all_profiles(session: SessionDep):
    return ProfileController.get_all_profiles(session)


@router.post(
    "/",
    response_model=ProfileRead,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить профиль",
)
def add_profile(profile: ProfileCreate, session: SessionDep):
    return ProfileController.add_profile(profile, session)


@router.post("/authenticate", response_model=ProfileRead, summary="Проверить пароль")
def authenticate(profile: ProfileLogin, session: SessionDep):
    found = ProfileController.authenticate(profile.email, profile.password, session)
    if found is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )
    return found


@router.get(
    "/by-role/{role_id}", response_model=list[ProfileRead], summary="Профили по роли"
)
def get_profiles_by_role(role_id: Annotated[int, Path(gt=0)], session: SessionDep):
    return ProfileController.get_profiles_by_role(role_id, session)


@router.get("/{profile_id}", response_model=ProfileRead, summary="Профиль по ID")
def get_profile_by_id(profile_id: ProfileId, session: SessionDep):
    profile = ProfileController.get_profile_by_id(profile_id, session)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль не найден")
    return profile


@router.put("/{profile_id}", response_model=ProfileRead, summary="Изменить профиль")
def update_profile(profile_id: ProfileId, profile: ProfileUpdate, session: SessionDep):
    updated = ProfileController.update_profile(profile_id, profile, session)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль не найден")
    return updated


@router.delete("/{profile_id}", summary="Удалить профиль")
def delete_profile(profile_id: ProfileId, session: SessionDep):
    if not ProfileController.delete_profile(profile_id, session):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль не найден")
    return {"message": "Профиль удалён"}
