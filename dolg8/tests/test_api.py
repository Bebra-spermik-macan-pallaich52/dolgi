"""DOLG8_TEST_DATABASE_URL выбирает отдельную БД: таблицы clients и tarifs пересоздаются."""

import os
import unittest
from decimal import Decimal
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine

from app.db import database
from app.main import main_app


class ApiTests(unittest.TestCase):
    def setUp(self):
        url = os.getenv("DOLG8_TEST_DATABASE_URL", "sqlite://")
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
        return self.client.request(method, "/api/v1" + path, follow_redirects=False, **kwargs)

    def add_tarif(self, name="Стандарт", salary="600.00", **changes):
        data = {
            "tarif_name": name,
            "internet": 50,
            "count_minutes": 500,
            "count_sms": 100,
            "salary": salary,
        }
        data.update(changes)
        response = self.request("POST", "/tarifs", json=data)
        self.assertEqual(response.status_code, 201, response.text)
        result = response.json()
        self.assertIsInstance(result["id_tarif"], int)
        self.assertEqual(Decimal(str(result["salary"])), Decimal(str(data["salary"])))
        return result

    def client_data(self, phone="+79000000001", tarif_id=None, **changes):
        data = {
            "number_phone": phone,
            "id_tarif": tarif_id,
            "lastname": "Иванов",
            "firstname": "Иван",
            "patronymic_name": "Иванович",
            "date_birthday": "1990-05-15",
            "pasport_serial": "0012",
            "pasport_number": "000123",
            "date_issue": "2015-12-31",
        }
        data.update(changes)
        return data

    def add_client(self, phone="+79000000001", tarif_id=None, **changes):
        data = self.client_data(phone, tarif_id, **changes)
        response = self.request("POST", "/clients", json=data)
        self.assertEqual(response.status_code, 201, response.text)
        result = response.json()
        self.assertEqual(result["number_phone"], data["number_phone"])
        self.assertEqual(result["pasport_serial"], data["pasport_serial"])
        self.assertEqual(result["pasport_number"], data["pasport_number"])
        return result

    def clients_by_phone(self):
        response = self.request("GET", "/clients")
        self.assertEqual(response.status_code, 200, response.text)
        return {client["number_phone"]: client for client in response.json()}

    def test_tarif_crud_and_partial_update(self):
        tarif = self.add_tarif()
        tarif_id = tarif["id_tarif"]
        listed = self.request("GET", "/tarifs")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json(), [tarif])
        updated = self.request("PATCH", f"/tarifs/{tarif_id}", json={"salary": "700.25"})
        self.assertEqual(updated.status_code, 200, updated.text)
        expected = {**tarif, "salary": updated.json()["salary"]}
        self.assertEqual(updated.json(), expected)
        self.assertEqual(Decimal(str(updated.json()["salary"])), Decimal("700.25"))
        deleted = self.request("DELETE", f"/tarifs/{tarif_id}")
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(deleted.content, b"")
        self.assertEqual(self.request("GET", "/tarifs").json(), [])
        self.assertEqual(self.request("DELETE", f"/tarifs/{tarif_id}").status_code, 404)
        self.assertEqual(self.request("PATCH", f"/tarifs/{tarif_id}", json={"internet": 10}).status_code, 404)
        self.assertEqual(self.request("GET", f"/tarifs/{tarif_id}/client-count").status_code, 404)

    def test_counts_include_empty_and_separate_duplicate_named_tarifs(self):
        first = self.add_tarif("Одинаковый")
        second = self.add_tarif("Одинаковый")
        empty = self.add_tarif("Пустой")
        self.add_client("+79000000001", first["id_tarif"])
        self.add_client("+79000000002", first["id_tarif"])
        self.add_client("+79000000003", second["id_tarif"])
        stats = self.request("GET", "/tarifs/stats/client-count")
        self.assertEqual(stats.status_code, 200, stats.text)
        self.assertEqual(stats.json(), [
            {"tarif_name": "Одинаковый", "client_count": 2},
            {"tarif_name": "Одинаковый", "client_count": 1},
            {"tarif_name": "Пустой", "client_count": 0},
        ])
        with_counts = self.request("GET", "/tarifs/with-client-count")
        self.assertEqual(with_counts.status_code, 200, with_counts.text)
        by_id = {item["id_tarif"]: item for item in with_counts.json()}
        for tarif, count in ((first, 2), (second, 1), (empty, 0)):
            self.assertEqual(by_id[tarif["id_tarif"]], {**tarif, "client_count": count})
            counted = self.request("GET", f"/tarifs/{tarif['id_tarif']}/client-count")
            self.assertEqual(counted.status_code, 200)
            self.assertEqual(counted.json(), {"tarif_id": tarif["id_tarif"], "count": count})

    def test_tarif_lookup_and_assignment_by_phone(self):
        first = self.add_tarif("Первый")
        second = self.add_tarif("Второй")
        client = self.add_client()
        phone = client["number_phone"]
        self.assertEqual(self.request("GET", f"/tarifs/by-client/{phone}").status_code, 404)
        assigned = self.request("PATCH", "/clients/tarif", params={"phone": phone, "id_tarif": first["id_tarif"]})
        self.assertEqual(assigned.status_code, 200, assigned.text)
        self.assertIsInstance(assigned.json().get("message"), str)
        self.assertEqual(self.request("GET", f"/tarifs/by-client/{phone}").json(), first)
        replaced = self.request("PATCH", "/clients/tarif", params={"phone": phone, "id_tarif": second["id_tarif"]})
        self.assertEqual(replaced.status_code, 200)
        self.assertEqual(self.request("GET", f"/tarifs/by-client/{phone}").json(), second)
        self.assertEqual(self.request("GET", f"/tarifs/{first['id_tarif']}/client-count").json()["count"], 0)
        self.assertEqual(self.request("GET", f"/tarifs/{second['id_tarif']}/client-count").json()["count"], 1)
        missing = self.request("PATCH", "/clients/tarif", params={"phone": phone, "id_tarif": 99999})
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(self.request("GET", f"/tarifs/by-client/{phone}").json(), second)
        self.assertEqual(self.request("GET", "/tarifs/by-client/+79999999999").status_code, 404)
        self.assertEqual(self.request("PATCH", "/clients/tarif", params={"phone": "+79999999999", "id_tarif": first["id_tarif"]}).status_code, 404)

    def test_referenced_tarif_cannot_be_deleted(self):
        tarif = self.add_tarif()
        client = self.add_client(tarif_id=tarif["id_tarif"])
        self.assertEqual(self.request("DELETE", f"/tarifs/{tarif['id_tarif']}").status_code, 409)
        self.assertIn(client["number_phone"], self.clients_by_phone())
        self.assertEqual(len(self.request("GET", "/tarifs").json()), 1)
        deleted = self.request("DELETE", f"/clients/{client['number_phone']}")
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(deleted.content, b"")
        self.assertEqual(self.request("DELETE", f"/tarifs/{tarif['id_tarif']}").status_code, 204)
        self.assertEqual(self.request("GET", "/tarifs").json(), [])

    def test_phone_prefix_search_has_documented_projection(self):
        first = self.add_client("+79000000001")
        second = self.add_client("+79000000002", lastname="Петров")
        foreign = self.add_client("+441234567890")
        national = self.add_client("89000000001")
        response = self.request("GET", "/clients/search/phone", params={"phone": "+7"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [
            {field: client[field] for field in ("number_phone", "lastname", "firstname")}
            for client in (first, second)
        ])
        response = self.request("GET", "/clients/search/phone", params={"phone": "8"})
        self.assertEqual([item["number_phone"] for item in response.json()], [national["number_phone"]])
        response = self.request("GET", "/clients/search/phone", params={"phone": "+44"})
        self.assertEqual([item["number_phone"] for item in response.json()], [foreign["number_phone"]])
        self.assertEqual(self.request("GET", "/clients/search/phone", params={"phone": "+99"}).json(), [])

    def test_birthday_sort_and_full_names(self):
        self.add_client("+79000000003", lastname="Молодов", firstname="Максим", date_birthday="1995-01-01")
        self.add_client("+79000000002", lastname="Второй", firstname="Пётр", date_birthday="1980-01-01")
        self.add_client("+79000000001", lastname="Первый", firstname="Иван", patronymic_name=None, date_birthday="1980-01-01")
        response = self.request("GET", "/clients/sorted-by-birthday")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [
            {"full_name": "Первый Иван", "date_birthday": "1980-01-01"},
            {"full_name": "Второй Пётр Иванович", "date_birthday": "1980-01-01"},
            {"full_name": "Молодов Максим Иванович", "date_birthday": "1995-01-01"},
        ])

    def test_passport_year_excludes_the_whole_given_year(self):
        self.add_client("+79000000001", date_issue="2015-12-31")
        after = self.add_client("+79000000002", date_issue="2016-01-01")
        later = self.add_client("+79000000003", date_issue="2017-06-01")
        response = self.request("GET", "/clients/search/passport-year", params={"year": 2015})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([client["number_phone"] for client in response.json()], [after["number_phone"], later["number_phone"]])
        self.assertEqual(self.request("GET", "/clients/search/passport-year", params={"year": 2016}).json(), [later])
        self.assertEqual(self.request("GET", "/clients/search/passport-year", params={"year": 9999}).json(), [])

    def test_clients_join_includes_unassigned_clients(self):
        tarif = self.add_tarif()
        assigned = self.add_client("+79000000001", tarif["id_tarif"])
        unassigned = self.add_client("+79000000002")
        by_phone = self.clients_by_phone()
        self.assertEqual(by_phone[assigned["number_phone"]], {**assigned, "tarif": tarif})
        self.assertEqual(by_phone[unassigned["number_phone"]], {**unassigned, "tarif": None})

    def test_tarif_cost_is_strict_and_preserves_decimal_boundary(self):
        cheap = self.add_tarif("Дешёвый", salary="100.00")
        boundary = self.add_tarif("Граница", salary="100.01")
        expensive = self.add_tarif("Дорогой", salary="100.02")
        self.add_client("+79000000001", cheap["id_tarif"])
        above_boundary = self.add_client("+79000000002", boundary["id_tarif"])
        above = self.add_client("+79000000003", expensive["id_tarif"])
        self.add_client("+79000000004")
        response = self.request("GET", "/clients/search/tarif-cost", params={"minSalary": "100.01"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), [{**above, "tarif": expensive}])
        response = self.request("GET", "/clients/search/tarif-cost", params={"minSalary": "100.00"})
        self.assertEqual(response.json(), [
            {**above_boundary, "tarif": boundary}, {**above, "tarif": expensive},
        ])

    def test_client_partial_update_preserves_fields_and_can_change_phone(self):
        tarif = self.add_tarif()
        client = self.add_client(tarif_id=tarif["id_tarif"])
        phone = client["number_phone"]
        updated = self.request("PUT", f"/clients/{phone}", json={"lastname": "Петров"})
        self.assertEqual(updated.status_code, 200, updated.text)
        expected = {**client, "lastname": "Петров"}
        self.assertEqual(updated.json(), expected)
        changed = self.request("PUT", f"/clients/{phone}", json={"number_phone": "+79000000009"})
        self.assertEqual(changed.status_code, 200, changed.text)
        expected["number_phone"] = "+79000000009"
        self.assertEqual(changed.json(), expected)
        self.assertEqual(self.request("GET", f"/tarifs/by-client/{phone}").status_code, 404)
        self.assertEqual(self.request("GET", "/tarifs/by-client/+79000000009").json(), tarif)
        self.assertNotIn(phone, self.clients_by_phone())
        deleted = self.request("DELETE", "/clients/+79000000009")
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(deleted.content, b"")
        self.assertEqual(self.request("DELETE", "/clients/+79000000009").status_code, 404)
        self.assertEqual(self.request("PUT", "/clients/+79000000009", json={"lastname": "Петров"}).status_code, 404)

    def test_duplicate_phones_conflict_and_next_request_works(self):
        first = self.add_client()
        self.assertEqual(self.request("POST", "/clients", json=self.client_data()).status_code, 409)
        second = self.add_client("+79000000002", lastname="Второй")
        update = self.request("PUT", f"/clients/{first['number_phone']}", json={"number_phone": second["number_phone"], "lastname": "Изменён"})
        self.assertEqual(update.status_code, 409)
        listed = self.clients_by_phone()
        self.assertEqual(listed[first["number_phone"]]["lastname"], first["lastname"])
        self.assertEqual(listed[second["number_phone"]]["lastname"], second["lastname"])

    def test_cross_field_validation_is_atomic(self):
        client = self.add_client()
        phone = client["number_phone"]
        for changes in (
            {"date_birthday": "2020-01-01", "lastname": "Изменён"},
            {"date_issue": "1985-01-01"},
            {"pasport_serial": "123"},
        ):
            response = self.request("PUT", f"/clients/{phone}", json=changes)
            self.assertEqual(response.status_code, 422, response.text)
            expected = {**client, "tarif": None}
            self.assertEqual(self.clients_by_phone()[phone], expected)
        missing_tarif = self.request("PUT", f"/clients/{phone}", json={"id_tarif": 99999, "lastname": "Изменён"})
        self.assertEqual(missing_tarif.status_code, 404)
        self.assertEqual(self.clients_by_phone()[phone]["lastname"], client["lastname"])
        self.assertEqual(self.request("POST", "/clients", json=self.client_data("+79000000003", tarif_id=99999)).status_code, 404)

    def test_nullable_client_fields_and_rejected_tarif_nulls(self):
        tarif = self.add_tarif()
        client = self.add_client(tarif_id=tarif["id_tarif"])
        phone = client["number_phone"]
        detached = self.request("PUT", f"/clients/{phone}", json={"id_tarif": None, "patronymic_name": None})
        self.assertEqual(detached.status_code, 200)
        self.assertIsNone(detached.json()["id_tarif"])
        self.assertIsNone(detached.json()["patronymic_name"])
        self.assertEqual(self.request("GET", f"/tarifs/{tarif['id_tarif']}/client-count").json()["count"], 0)
        for changes in ({"firstname": None}, {"date_birthday": None}):
            self.assertEqual(self.request("PUT", f"/clients/{phone}", json=changes).status_code, 422)
        for changes in ({"salary": None}, {"tarif_name": None}):
            self.assertEqual(self.request("PATCH", f"/tarifs/{tarif['id_tarif']}", json=changes).status_code, 422)
        self.assertEqual(self.request("GET", "/tarifs").json(), [tarif])

    def test_client_validation_and_safe_error_output(self):
        invalid = (
            {"number_phone": "invalid"}, {"number_phone": "+7"},
            {"lastname": ""}, {"firstname": "x" * 51},
            {"patronymic_name": "x" * 51}, {"pasport_serial": "123"},
            {"pasport_number": "12345"}, {"date_birthday": "9999-01-01"},
            {"date_issue": "9999-01-01"}, {"date_issue": "1980-01-01"},
            {"id_tarif": 0}, {"unexpected": "value"},
        )
        for changes in invalid:
            with self.subTest(fields=tuple(changes)):
                response = self.request("POST", "/clients", json=self.client_data(**changes))
                self.assertEqual(response.status_code, 422, response.text)
        payload = self.client_data()
        del payload["lastname"]
        response = self.request("POST", "/clients", json=payload)
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("000123", response.text)
        self.assertEqual(self.request("GET", "/clients").json(), [])

    def test_tarif_and_query_validation(self):
        base = {"tarif_name": "Стандарт", "internet": 50, "count_minutes": 500, "count_sms": 100, "salary": "600.00"}
        invalid = (
            {"tarif_name": "   "}, {"tarif_name": "x" * 101},
            {"internet": -1}, {"count_minutes": -1}, {"count_sms": -1},
            {"count_minutes": 1.5}, {"salary": "-1.00"},
            {"salary": "0.001"}, {"id_tarif": 999},
        )
        for changes in invalid:
            with self.subTest(fields=tuple(changes)):
                self.assertEqual(self.request("POST", "/tarifs", json={**base, **changes}).status_code, 422)
        for path in (
            "/clients/search/phone?phone=%25", "/clients/search/phone",
            "/clients/search/passport-year?year=0", "/clients/search/passport-year?year=10000",
            "/clients/search/tarif-cost?minSalary=-1", "/clients/search/tarif-cost?minSalary=wrong",
            "/clients/search/tarif-cost", "/tarifs/0/client-count",
        ):
            with self.subTest(path=path):
                self.assertEqual(self.request("GET", path).status_code, 422)
        self.assertEqual(self.request("PATCH", "/clients/tarif", params={"phone": "+7", "id_tarif": 1}).status_code, 422)
        self.assertEqual(self.request("GET", "/tarifs").json(), [])

    def test_mounted_documentation_and_routes(self):
        docs = self.client.get("/api/v1/docs")
        self.assertEqual(docs.status_code, 200)
        self.assertIn("/api/v1/openapi.json", docs.text)
        self.assertNotIn("/api/v1/api/v1/", docs.text)
        self.assertEqual(self.client.get("/api/v1/redoc").status_code, 200)
        response = self.client.get("/api/v1/openapi.json")
        self.assertEqual(response.status_code, 200)
        paths = response.json()["paths"]
        for path in ("/tarifs", "/tarifs/stats/client-count", "/tarifs/with-client-count",
                     "/clients/search/phone", "/clients/sorted-by-birthday",
                     "/clients/search/passport-year", "/clients/search/tarif-cost", "/clients/tarif"):
            self.assertIn(path, paths)
        parameters = paths["/clients/search/tarif-cost"]["get"]["parameters"]
        self.assertIn("minSalary", [item["name"] for item in parameters])

    def test_database_error_is_generic_and_next_request_succeeds(self):
        with patch("app.db.session.Session", side_effect=SQLAlchemyError("passport=private-passport-marker")):
            response = self.request("GET", "/tarifs")
        self.assertEqual(response.status_code, 500)
        self.assertIsInstance(response.json().get("detail"), str)
        self.assertNotIn("private-passport-marker", response.text)
        self.assertEqual(self.add_tarif()["tarif_name"], "Стандарт")


if __name__ == "__main__":
    unittest.main()
