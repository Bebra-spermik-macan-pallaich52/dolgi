"""DOLG7_TEST_DATABASE_URL выбирает отдельную БД: таблицы roles и profiles пересоздаются."""

import json
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from app.controllers.role_controller import RoleController
from app.core.security import verify_password
from app.db import database
from app.main import main_app
from app.models.profile import Profile


class ApiTests(unittest.TestCase):
    def setUp(self):
        url = os.getenv("DOLG7_TEST_DATABASE_URL", "sqlite://")
        options = {}
        if url.startswith("sqlite"):
            options = {
                "connect_args": {"check_same_thread": False},
                "poolclass": StaticPool,
            }
        self.engine = create_engine(url, **options)
        self.addCleanup(self.engine.dispose)
        if url.startswith("sqlite"):
            event.listen(
                self.engine,
                "connect",
                lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"),
            )
        self.addCleanup(SQLModel.metadata.drop_all, self.engine)
        SQLModel.metadata.drop_all(self.engine)
        engine_patch = patch.object(database, "engine", self.engine)
        engine_patch.start()
        self.addCleanup(engine_patch.stop)
        self.client = TestClient(main_app, raise_server_exceptions=False)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def request(self, method, path, **kwargs):
        return self.client.request(method, "/api/v1" + path, **kwargs)

    def add_role(self, name="reader"):
        response = self.request("POST", "/roles/", json={"name_role": name})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def add_profile(self, role_id, email="one@example.test", **changes):
        data = {
            "email": email,
            "password": "Secret123!",
            "role_id": role_id,
            "first_name": "Иван",
            "second_name": "Иванов",
        }
        data.update(changes)
        response = self.request("POST", "/profiles/", json=data)
        self.assertEqual(response.status_code, 201, response.text)
        self.assert_public(response.json())
        return response.json()

    def assert_public(self, value):
        if isinstance(value, dict):
            self.assertNotIn("password", value)
            self.assertNotIn("password_hash", value)
            for item in value.values():
                self.assert_public(item)
        elif isinstance(value, list):
            for item in value:
                self.assert_public(item)
        self.assertNotIn("$argon2", json.dumps(value, ensure_ascii=False))

    def saved_hash(self, profile_id):
        with Session(self.engine) as session:
            return session.get(Profile, profile_id).password

    def authenticate(self, email, password):
        return self.request(
            "POST", "/profiles/authenticate", json={"email": email, "password": password}
        )

    def test_role_crud_and_missing_ids(self):
        role = self.add_role("admin")
        role_id = role["id_role"]
        self.assertEqual(self.request("GET", f"/roles/{role_id}").json(), role)
        updated = self.request("PUT", f"/roles/{role_id}", json={"name_role": "manager"})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json(), {"id_role": role_id, "name_role": "manager"})
        self.assertEqual(self.request("DELETE", f"/roles/{role_id}").status_code, 200)
        for method in ("GET", "DELETE"):
            self.assertEqual(self.request(method, f"/roles/{role_id}").status_code, 404)
        self.assertEqual(
            self.request("PUT", f"/roles/{role_id}", json={"name_role": "missing"}).status_code,
            404,
        )
        self.assertEqual(self.request("GET", "/roles/").json(), [])

    def test_role_duplicates_and_update_to_own_name(self):
        admin = self.add_role("admin")
        user = self.add_role("user")
        self.assertEqual(self.request("POST", "/roles/", json={"name_role": "admin"}).status_code, 409)
        unchanged = self.request("PUT", f"/roles/{admin['id_role']}", json={"name_role": "admin"})
        self.assertEqual(unchanged.status_code, 200)
        conflict = self.request("PUT", f"/roles/{user['id_role']}", json={"name_role": "admin"})
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(self.request("GET", "/roles/count").json(), {"count": 2})
        self.assertEqual(self.request("GET", f"/roles/{user['id_role']}").json()["name_role"], "user")
        self.assertEqual(self.add_role("next")["name_role"], "next")

    def test_role_queries_and_bulk_delete(self):
        names = ["viewer", "admin", "editor", "reviewer"]
        for name in names:
            self.add_role(name)
        self.assertEqual([r["name_role"] for r in self.request("GET", "/roles/").json()], names)
        self.assertEqual(self.request("GET", "/roles/count").json(), {"count": 4})
        found = self.request("GET", "/roles/by-name", params={"name_role": "admin"})
        self.assertEqual(found.status_code, 200)
        self.assertEqual(found.json()["name_role"], "admin")
        self.assertEqual(
            self.request("GET", "/roles/by-name", params={"name_role": "missing"}).status_code,
            404,
        )
        page = self.request("GET", "/roles/page", params={"offset": 1, "limit": 2})
        self.assertEqual([r["name_role"] for r in page.json()], ["admin", "editor"])
        self.assertEqual(self.request("GET", "/roles/page", params={"offset": 9}).json(), [])
        search = self.request("GET", "/roles/search", params={"substring": "view"})
        self.assertEqual([r["name_role"] for r in search.json()], ["viewer", "reviewer"])
        for descending in (False, True):
            sorted_roles = self.request("GET", "/roles/sorted", params={"descending": descending})
            self.assertEqual(
                [r["name_role"] for r in sorted_roles.json()],
                sorted(names, reverse=descending),
            )
        self.assertEqual(self.request("DELETE", "/roles/").json(), {"deleted": 4})
        self.assertEqual(self.request("DELETE", "/roles/").json(), {"deleted": 0})
        self.assertEqual(self.request("GET", "/roles/count").json(), {"count": 0})

    def test_role_validation(self):
        for data in ({"name_role": ""}, {"name_role": "   "}, {"name_role": "x" * 31},
                     {"name_role": "reader", "id_role": 100}, {}):
            with self.subTest(data=data):
                self.assertEqual(self.request("POST", "/roles/", json=data).status_code, 422)
        role = self.add_role("  reader  ")
        self.assertEqual(role["name_role"], "reader")
        for path in ("/roles/0", "/roles/page?offset=-1", "/roles/page?limit=0",
                     "/roles/page?limit=101", "/roles/search?substring="):
            with self.subTest(path=path):
                self.assertEqual(self.request("GET", path).status_code, 422)

    def test_linked_role_and_atomic_bulk_delete(self):
        used = self.add_role("used")
        self.add_role("unused")
        profile = self.add_profile(used["id_role"])
        self.assertEqual(self.request("DELETE", f"/roles/{used['id_role']}").status_code, 409)
        self.assertEqual(self.request("DELETE", "/roles/").status_code, 409)
        self.assertEqual(self.request("GET", "/roles/count").json(), {"count": 2})
        self.assertEqual(self.request("GET", f"/profiles/{profile['id_users']}").status_code, 200)
        self.assertEqual(self.request("DELETE", f"/profiles/{profile['id_users']}").status_code, 200)
        self.assertEqual(self.request("DELETE", "/roles/").json(), {"deleted": 2})

    def test_profile_crud_and_role_filter_hide_password(self):
        reader = self.add_role("reader")
        admin = self.add_role("admin")
        one = self.add_profile(reader["id_role"])
        two = self.add_profile(admin["id_role"], email="two@example.test")
        profile_id = one["id_users"]
        fetched = self.request("GET", f"/profiles/{profile_id}")
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.json(), one)
        self.assert_public(fetched.json())
        profiles = self.request("GET", "/profiles/")
        self.assertEqual([p["id_users"] for p in profiles.json()], [profile_id, two["id_users"]])
        self.assert_public(profiles.json())
        filtered = self.request("GET", f"/profiles/by-role/{reader['id_role']}")
        self.assertEqual(filtered.json(), [one])
        self.assert_public(filtered.json())
        self.assertEqual(self.request("GET", "/profiles/by-role/99999").json(), [])
        self.assertEqual(self.request("DELETE", f"/profiles/{profile_id}").status_code, 200)
        for method in ("GET", "DELETE"):
            self.assertEqual(self.request(method, f"/profiles/{profile_id}").status_code, 404)
        self.assertEqual(self.request("PUT", f"/profiles/{profile_id}", json={
            "email": one["email"], "role_id": reader["id_role"],
        }).status_code, 404)

    def test_profile_duplicate_email_and_unknown_role(self):
        role = self.add_role()
        one = self.add_profile(role["id_role"])
        duplicate = self.request("POST", "/profiles/", json={
            "role_id": role["id_role"], "email": one["email"], "password": "Secret123!",
        })
        self.assertEqual(duplicate.status_code, 409)
        missing = self.request("POST", "/profiles/", json={
            "role_id": 99999, "email": "missing@example.test", "password": "Secret123!",
        })
        self.assertEqual(missing.status_code, 409)
        self.assertEqual(len(self.request("GET", "/profiles/").json()), 1)
        self.assertEqual(self.add_profile(role["id_role"], email="next@example.test")["email"], "next@example.test")

    def test_authentication_and_salted_argon2_hashes(self):
        role = self.add_role()
        one = self.add_profile(role["id_role"])
        two = self.add_profile(role["id_role"], email="two@example.test")
        first_hash = self.saved_hash(one["id_users"])
        self.assertTrue(first_hash.startswith("$argon2"))
        self.assertTrue(verify_password("Secret123!", first_hash))
        self.assertNotEqual(first_hash, self.saved_hash(two["id_users"]))
        authenticated = self.authenticate(one["email"], "Secret123!")
        self.assertEqual(authenticated.status_code, 200)
        self.assertEqual(authenticated.json(), one)
        self.assert_public(authenticated.json())
        for email, password in ((one["email"], "wrong"), ("missing@example.test", "Secret123!")):
            self.assertEqual(self.authenticate(email, password).status_code, 401)

    def test_profile_update_changes_fields_and_password(self):
        reader = self.add_role("reader")
        admin = self.add_role("admin")
        one = self.add_profile(reader["id_role"])
        profile_id = one["id_users"]
        old_hash = self.saved_hash(profile_id)
        updated = self.request("PUT", f"/profiles/{profile_id}", json={
            "email": "new@example.test", "role_id": admin["id_role"],
            "first_name": "Анна", "second_name": "Петрова", "patronymic": "Ивановна",
            "password": "NewPassword123!",
        })
        self.assertEqual(updated.status_code, 200, updated.text)
        data = updated.json()
        self.assertEqual((data["first_name"], data["second_name"], data["patronymic"]),
                         ("Анна", "Петрова", "Ивановна"))
        self.assertEqual(data["role_id"], admin["id_role"])
        self.assert_public(data)
        self.assertNotEqual(self.saved_hash(profile_id), old_hash)
        self.assertEqual(self.authenticate(one["email"], "Secret123!").status_code, 401)
        self.assertEqual(self.authenticate(data["email"], "Secret123!").status_code, 401)
        self.assertEqual(self.authenticate(data["email"], "NewPassword123!").status_code, 200)

    def test_profile_update_preserves_password_when_omitted_or_null(self):
        role = self.add_role()
        one = self.add_profile(role["id_role"])
        profile_id = one["id_users"]
        old_hash = self.saved_hash(profile_id)
        for extra in ({}, {"password": None}, {"password": "Secret123!"}):
            payload = {"email": one["email"], "role_id": role["id_role"], "first_name": "Анна", **extra}
            updated = self.request("PUT", f"/profiles/{profile_id}", json=payload)
            self.assertEqual(updated.status_code, 200, updated.text)
            self.assert_public(updated.json())
            self.assertEqual(self.saved_hash(profile_id), old_hash)
        self.assertEqual(self.authenticate(one["email"], "Secret123!").status_code, 200)

    def test_profile_update_conflicts_preserve_data(self):
        role = self.add_role()
        one = self.add_profile(role["id_role"])
        two = self.add_profile(role["id_role"], email="two@example.test")
        old_hash = self.saved_hash(one["id_users"])
        for changes in ({"email": two["email"]}, {"role_id": 99999}):
            payload = {"email": one["email"], "role_id": role["id_role"], "password": "Changed123!", **changes}
            self.assertEqual(self.request("PUT", f"/profiles/{one['id_users']}", json=payload).status_code, 409)
        self.assertEqual(self.request("GET", f"/profiles/{one['id_users']}").json(), one)
        self.assertEqual(self.saved_hash(one["id_users"]), old_hash)
        self.assertEqual(self.authenticate(one["email"], "Secret123!").status_code, 200)

    def test_profile_validation(self):
        role = self.add_role()
        for changes in ({"email": ""}, {"email": "invalid"}, {"email": "a b@example.test"},
                        {"email": "x" * 31 + "@x.test"}, {"password": ""}, {"password": "x" * 201},
                        {"first_name": "x" * 51}, {"second_name": "x" * 51},
                        {"patronymic": "x" * 51}, {"role_id": 0}, {"id_users": 99}):
            payload = {"email": "one@example.test", "password": "Secret123!", "role_id": role["id_role"], **changes}
            with self.subTest(fields=tuple(changes)):
                self.assertEqual(self.request("POST", "/profiles/", json=payload).status_code, 422)
        self.assertEqual(self.request("GET", "/profiles/").json(), [])
        self.assertEqual(self.request("GET", "/profiles/0").status_code, 422)
        self.assertEqual(self.request("GET", "/profiles/by-role/0").status_code, 422)
        response = self.request("POST", "/profiles/", json={
            "password": "validation-marker-private", "role_id": role["id_role"],
        })
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("validation-marker-private", response.text)

    def test_mounted_documentation_and_public_response_schema(self):
        docs = self.client.get("/api/v1/docs")
        self.assertEqual(docs.status_code, 200)
        self.assertIn("/api/v1/openapi.json", docs.text)
        self.assertNotIn("/api/v1/api/v1/", docs.text)
        self.assertEqual(self.client.get("/api/v1/redoc").status_code, 200)
        schema = self.client.get("/api/v1/openapi.json")
        self.assertEqual(schema.status_code, 200)
        data = schema.json()
        self.assertIn("/roles/", data["paths"])
        self.assertIn("/profiles/authenticate", data["paths"])
        public = data["components"]["schemas"]["ProfileRead"]["properties"]
        self.assertNotIn("password", public)
        self.assertNotIn("password_hash", public)
        self.assertIn("id_users", public)

    def test_database_errors_have_generic_response_and_next_request_works(self):
        with patch.object(RoleController, "get_all_roles", side_effect=SQLAlchemyError("password=private-secret")):
            response = self.request("GET", "/roles/")
        self.assertEqual(response.status_code, 500)
        self.assertIsInstance(response.json().get("detail"), str)
        self.assertNotIn("private-secret", response.text)
        self.assertNotIn("password=", response.text)
        self.assertEqual(self.add_role()["name_role"], "reader")


if __name__ == "__main__":
    unittest.main()
