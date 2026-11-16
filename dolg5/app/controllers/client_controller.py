"""Операции с clients. Значения передаются параметрами SQL."""

from app.db.session import get_cursor
from app.models.client import Client


class ClientController:
    def get_clients(self, limit: int = 100, offset: int = 0) -> list[Client]:
        """Получить страницу клиентов в порядке id."""
        if limit <= 0 or offset < 0:
            raise ValueError("Лимит должен быть положительным, смещение — неотрицательным.")
        with get_cursor() as cur:
            cur.execute(
                "SELECT id, username, password_hash, phone, email "
                "FROM public.clients ORDER BY id LIMIT %s OFFSET %s",
                (limit, offset),
            )
            rows = cur.fetchall()
        return [Client(*row) for row in rows]

    def add_client(self, client: Client) -> Client:
        """Добавить клиента с готовым хешем пароля и вернуть запись с id."""
        username = client.username.strip()
        email = client.email.strip()
        phone = client.phone.strip() if client.phone else None
        if not username or not email or not client.password_hash:
            raise ValueError("Имя, пароль и email обязательны.")
        if len(username) > 255:
            raise ValueError("Имя должно содержать не более 255 символов.")
        with get_cursor() as cur:
            cur.execute(
                "INSERT INTO public.clients (username, password_hash, phone, email) "
                "VALUES (%s, %s, %s, %s) "
                "RETURNING id, username, password_hash, phone, email",
                (username, client.password_hash, phone or None, email),
            )
            row = cur.fetchone()
        return Client(*row)

    def delete_client(self, client_id: int) -> bool:
        """Удалить клиента. False означает, что такого id нет.

        При наличии заказов PostgreSQL отклонит удаление внешним ключом.
        """
        if client_id <= 0:
            raise ValueError("ID должен быть положительным целым числом.")
        with get_cursor() as cur:
            cur.execute("DELETE FROM public.clients WHERE id = %s", (client_id,))
            deleted = cur.rowcount > 0
        return deleted
