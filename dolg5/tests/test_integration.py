"""Интеграционные проверки: только на явно выбранной тестовой PostgreSQL БД.

Установите CAFE_TEST_DB=1 и DB_* перед запуском. Проверки удаляют только
созданные ими записи; исходные таблицы и данные сохраняются.
"""

import hashlib
import os
import unittest
from uuid import uuid4


RUN_DB_TESTS = os.getenv("CAFE_TEST_DB") == "1"

if RUN_DB_TESTS:
    import psycopg
    from psycopg.errors import ForeignKeyViolation, UniqueViolation

    from app.controllers.client_controller import ClientController
    from app.core.config import DATABASE_URL
    from app.core.utils import hash_password
    from app.db.database import close_db, get_engine, init_db
    from app.db.session import get_cursor
    from app.models.client import Client


@unittest.skipUnless(RUN_DB_TESTS, "Для тестовой БД установите CAFE_TEST_DB=1")
class DatabaseIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.controller = ClientController()
        cls.prefix = f"cafe_test_{uuid4().hex}_"
        cls.client_ids = set()
        cls.order_ids = set()

    @classmethod
    def tearDownClass(cls):
        try:
            with get_cursor() as cur:
                if cls.order_ids:
                    cur.execute(
                        "DELETE FROM order_items WHERE order_id = ANY(%s)",
                        (list(cls.order_ids),),
                    )
                    cur.execute(
                        "DELETE FROM orders WHERE id = ANY(%s)",
                        (list(cls.order_ids),),
                    )
                if cls.client_ids:
                    cur.execute(
                        "DELETE FROM clients WHERE id = ANY(%s)",
                        (list(cls.client_ids),),
                    )
        finally:
            close_db()

    def add_client(self, suffix=None, **changes):
        suffix = suffix or uuid4().hex
        values = {
            "username": self.prefix + suffix,
            "password_hash": "test_hash_only",
            "phone": "+79990000000",
            "email": self.prefix + suffix + "@example.test",
        }
        values.update(changes)
        result = self.controller.add_client(Client(**values))
        self.assertIsInstance(result, Client)
        self.assertIsInstance(result.id, int)
        self.client_ids.add(result.id)
        return result

    def test_add_commits_and_returns_model(self):
        client = self.add_client()
        # Отдельное соединение видит строку только после фиксации транзакции.
        with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT username, password_hash, phone, email FROM clients WHERE id=%s",
                (client.id,),
            )
            row = cur.fetchone()
        self.assertEqual(
            row,
            (client.username, client.password_hash, client.phone, client.email),
        )
        self.assertNotIn("password_hash", client.to_dict())
        self.assertEqual(client.to_dict()["id"], client.id)

    def test_pagination_preserves_order(self):
        with get_cursor() as cur:
            cur.execute("SELECT count(*) FROM clients")
            offset = cur.fetchone()[0]
        clients = [self.add_client() for _ in range(3)]
        first_page = self.controller.get_clients(limit=2, offset=offset)
        second_page = self.controller.get_clients(limit=2, offset=offset + 2)
        self.assertTrue(all(isinstance(client, Client) for client in first_page))
        self.assertEqual([client.id for client in first_page], [c.id for c in clients[:2]])
        self.assertEqual([client.id for client in second_page], [clients[2].id])
        self.assertEqual(self.controller.get_clients(limit=2, offset=offset + 3), [])

    def test_apostrophe_and_sql_text_are_plain_data(self):
        username = self.prefix + "O'Brien'); DELETE FROM clients; --"
        client = self.add_client(username=username, phone=None)
        with get_cursor() as cur:
            cur.execute("SELECT username, phone FROM clients WHERE id=%s", (client.id,))
            self.assertEqual(cur.fetchone(), (username, None))
        # Таблица остаётся доступной после строки, похожей на SQL.
        self.assertIsInstance(self.controller.get_clients(limit=1), list)

    def test_duplicate_username_rolls_back(self):
        first = self.add_client()
        with self.assertRaises(UniqueViolation):
            self.add_client(username=first.username)
        following = self.add_client()
        self.assertGreater(following.id, first.id)
        with get_cursor() as cur:
            cur.execute("SELECT count(*) FROM clients WHERE username=%s", (first.username,))
            self.assertEqual(cur.fetchone()[0], 1)

    def test_duplicate_email_rolls_back(self):
        first = self.add_client()
        with self.assertRaises(UniqueViolation):
            self.add_client(email=first.email)
        self.assertIsInstance(self.add_client().id, int)
        with get_cursor() as cur:
            cur.execute("SELECT count(*) FROM clients WHERE email=%s", (first.email,))
            self.assertEqual(cur.fetchone()[0], 1)

    def test_delete_reports_actual_result(self):
        client = self.add_client()
        self.assertIs(self.controller.delete_client(client.id), True)
        self.assertIs(self.controller.delete_client(client.id), False)
        with get_cursor() as cur:
            cur.execute("SELECT id FROM clients WHERE id=%s", (client.id,))
            self.assertIsNone(cur.fetchone())

    def test_order_prevents_deleting_client(self):
        client = self.add_client()
        with get_cursor() as cur:
            cur.execute("INSERT INTO orders(client_id) VALUES (%s) RETURNING id", (client.id,))
            order_id = cur.fetchone()[0]
            self.order_ids.add(order_id)
        with self.assertRaises(ForeignKeyViolation):
            self.controller.delete_client(client.id)
        with get_cursor() as cur:
            cur.execute("SELECT client_id FROM orders WHERE id=%s", (order_id,))
            self.assertEqual(cur.fetchone()[0], client.id)
            cur.execute("SELECT id FROM clients WHERE id=%s", (client.id,))
            self.assertEqual(cur.fetchone()[0], client.id)

    def test_exception_rolls_back_entire_transaction(self):
        name = self.prefix + uuid4().hex
        with self.assertRaisesRegex(RuntimeError, "Проверка отката"):
            with get_cursor() as cur:
                cur.execute(
                    "INSERT INTO clients(username,password_hash,email) VALUES (%s,%s,%s)",
                    (name, "test_hash", name + "@example.test"),
                )
                raise RuntimeError("Проверка отката")
        with get_cursor() as cur:
            cur.execute("SELECT id FROM clients WHERE username=%s", (name,))
            self.assertIsNone(cur.fetchone())

    def test_hash_uses_random_salt_and_matches_pbkdf2(self):
        password = "Учебный пароль с пробелами!"
        encoded = hash_password(password)
        self.assertNotEqual(encoded, hash_password(password))
        algorithm, iterations, salt, digest = encoded.split("$")
        self.assertEqual(algorithm, "pbkdf2_sha256")
        self.assertGreaterEqual(int(iterations), 100_000)
        self.assertGreaterEqual(len(bytes.fromhex(salt)), 16)
        expected = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), int(iterations)
        ).hex()
        self.assertEqual(digest, expected)
        self.assertNotIn(password, encoded)

    def test_pool_can_be_initialized_and_closed_repeatedly(self):
        pool = get_engine()
        init_db()
        self.assertIs(get_engine(), pool)
        close_db()
        close_db()
        with self.assertRaises(RuntimeError):
            get_engine()
        init_db()
        with get_cursor() as cur:
            cur.execute("SELECT 1")
            self.assertEqual(cur.fetchone(), (1,))


if __name__ == "__main__":
    unittest.main()
