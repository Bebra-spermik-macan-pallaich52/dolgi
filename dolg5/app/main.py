"""Консольное приложение: python -m app.main."""

import logging
import sys
from getpass import getpass

import psycopg
from psycopg.errors import ForeignKeyViolation, UniqueViolation

from app.controllers import ClientController
from app.core.utils import hash_password
from app.db.database import close_db, init_db
from app.models import Client


def _print_clients(controller: ClientController) -> None:
    # Читаем страницами, чтобы показать и записи после первых 100.
    offset = 0
    while True:
        clients = controller.get_clients(limit=100, offset=offset)
        if not clients and offset == 0:
            print("Список клиентов пуст.")
        for client in clients:
            print(f"{client.id}: {client.username} | {client.phone or '—'} | {client.email}")
        if len(clients) < 100:
            return
        offset += len(clients)


def _add_client(controller: ClientController) -> None:
    username = input("Имя пользователя: ").strip()
    password_hash = hash_password(getpass("Пароль: "))
    phone = input("Телефон (необязательно): ").strip() or None
    email = input("Email: ").strip()
    client = controller.add_client(
        Client(username=username, password_hash=password_hash, phone=phone, email=email)
    )
    print(f"Клиент добавлен. ID: {client.id}")


def _delete_client(controller: ClientController) -> None:
    try:
        client_id = int(input("ID клиента: "))
    except ValueError:
        raise ValueError("ID должен быть положительным целым числом.") from None
    if controller.delete_client(client_id):
        print("Клиент удалён.")
    else:
        print("Клиент с таким ID не найден.")


def _run_menu() -> None:
    controller = ClientController()
    while True:
        print(
            "\n1. Показать всех клиентов\n"
            "2. Добавить клиента\n"
            "3. Удалить клиента\n"
            "0. Выход"
        )
        choice = input(">>> ").strip()
        try:
            match choice:
                case "1":
                    _print_clients(controller)
                case "2":
                    _add_client(controller)
                case "3":
                    _delete_client(controller)
                case "0":
                    return
                case _:
                    print("Введите 0, 1, 2 или 3.")
        except UniqueViolation as exc:
            field = "email" if exc.diag.constraint_name == "clients_email_key" else "именем"
            print(f"Клиент с таким {field} уже существует.")
        except ForeignKeyViolation:
            print("Нельзя удалить клиента: с ним связаны заказы.")
        except ValueError as exc:
            print(exc)
        except psycopg.Error:
            print("Ошибка запроса. Проверьте соединение и импорт SQL-скрипта.")


def main() -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    try:
        init_db()
        _run_menu()
    except (EOFError, KeyboardInterrupt):
        print("\nРабота завершена.")
    except psycopg.Error:
        print(
            "Не удалось подключиться к PostgreSQL. "
            "Проверьте запуск сервера и параметры в .env.",
            file=sys.stderr,
        )
        return 1
    finally:
        close_db()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
