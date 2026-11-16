import logging
import sys
from getpass import getpass

from sqlalchemy.exc import SQLAlchemyError

from app.models import Profile, Role


def _number(label: str, default: int | None = None) -> int:
    value = input(f"{label}{f' [{default}]' if default is not None else ''}: ").strip()
    if not value and default is not None:
        return default
    try:
        return int(value)
    except ValueError:
        raise ValueError("Введите целое число.") from None


def _text(label: str, default: str | None = None) -> str:
    value = input(f"{label}{f' [{default}]' if default else ''}: ").strip()
    return value or default or ""


def _profile(current: Profile | None = None) -> Profile:
    return Profile(
        email=_text("Email", current.email if current else None),
        password=getpass("Новый пароль (Enter — сохранить): " if current else "Пароль: "),
        role_id=_number("ID роли", current.role_id if current else 1),
        second_name=_text("Фамилия", current.second_name if current else None) or None,
        first_name=_text("Имя", current.first_name if current else None) or None,
        patronymic=_text("Отчество", current.patronymic if current else None) or None,
    )


def _update_profile() -> Profile | None:
    from app.controllers import ProfileController

    profile_id = _number("ID профиля")
    current = ProfileController.get_profile_by_id(profile_id)
    if current is None:
        return None
    return ProfileController.update_profile(profile_id, _profile(current))


def _show(result) -> None:
    if isinstance(result, list):
        if not result:
            print("Список пуст.")
        for item in result:
            _show(item)
    elif isinstance(result, Profile):
        print(result.model_dump(exclude={"password"}))
    elif isinstance(result, Role):
        print(result.model_dump())
    elif result is None:
        print("Операция не выполнена или запись не найдена.")
    elif isinstance(result, bool):
        print("Выполнено." if result else "Операция не выполнена.")
    else:
        print(result)


def _menu(actions: dict) -> None:
    while True:
        print()
        for key, (label, _) in actions.items():
            print(f"{key}. {label}")
        print("0. Назад")
        choice = input(">>> ").strip()
        if choice == "0":
            return
        if choice not in actions:
            print("Выберите пункт меню.")
            continue
        try:
            _show(actions[choice][1]())
        except ValueError as exc:
            print(exc)


def _roles() -> None:
    from app.controllers import RoleController

    _menu({
        "1": ("Все роли", RoleController.get_all_roles),
        "2": ("Роль по ID", lambda: RoleController.get_role_by_id(_number("ID роли"))),
        "3": ("Добавить роль", lambda: RoleController.add_role(Role(name_role=_text("Название")))),
        "4": ("Изменить роль", lambda: RoleController.update_role(_number("ID роли"), Role(name_role=_text("Название")))),
        "5": ("Удалить роль", lambda: RoleController.delete_role(_number("ID роли"))),
        "6": ("Роль по названию", lambda: RoleController.get_role_by_name(_text("Название"))),
        "7": ("Количество ролей", RoleController.count_roles),
        "8": ("Страница ролей", lambda: RoleController.get_roles_paginated(_number("Смещение", 0), _number("Лимит", 10))),
        "9": ("Поиск ролей", lambda: RoleController.search_roles(_text("Часть названия"))),
        "10": ("Сортировка ролей", lambda: RoleController.get_roles_sorted(_text("По убыванию? да/нет") == "да")),
        "11": ("Удалить все роли", RoleController.delete_all_roles),
    })


def _profiles() -> None:
    from app.controllers import ProfileController

    _menu({
        "1": ("Все профили", ProfileController.get_all_profiles),
        "2": ("Профиль по ID", lambda: ProfileController.get_profile_by_id(_number("ID профиля"))),
        "3": ("Добавить профиль", lambda: ProfileController.add_profile(_profile())),
        "4": ("Изменить профиль", _update_profile),
        "5": ("Удалить профиль", lambda: ProfileController.delete_profile(_number("ID профиля"))),
        "6": ("Войти", lambda: ProfileController.authenticate(_text("Email"), getpass("Пароль: "))),
        "7": ("Профили по роли", lambda: ProfileController.get_profiles_by_role(_number("ID роли"))),
    })


def main() -> int:
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    try:
        from app.db.database import close_db, init_db
    except (SQLAlchemyError, ValueError):
        print("Некорректный DATABASE_URL в .env.", file=sys.stderr)
        return 1
    try:
        init_db()
        while True:
            print("\n1. Роли\n2. Профили\n0. Выход")
            choice = input(">>> ").strip()
            if choice == "0":
                return 0
            if choice == "1":
                _roles()
            elif choice == "2":
                _profiles()
            else:
                print("Выберите пункт меню.")
    except (EOFError, KeyboardInterrupt):
        print("\nРабота завершена.")
        return 0
    except SQLAlchemyError:
        print("Ошибка подключения к PostgreSQL. Проверьте DATABASE_URL в .env.", file=sys.stderr)
        return 1
    finally:
        close_db()


if __name__ == "__main__":
    raise SystemExit(main())
