import json
import os
from datetime import date, timedelta
from getpass import getpass
from pathlib import Path

import requests

BASE_URL = "https://partner.agentapp.ru/v1"
ROOT = Path(__file__).resolve().parent
results = []


def request(session, method, path, **kwargs):
    response = session.request(method, BASE_URL + path, timeout=30, **kwargs)
    print(method, path, response.status_code)
    data = response.json() if response.content else None
    if "obtain-token" not in path:
        results.append({"method": method, "path": path,
                        "status": response.status_code, "response": data})
    if not response.ok:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    response.raise_for_status()
    return data


def person_id(record):
    person = record["person"]
    return person["id"] if isinstance(person, dict) else person


def main():
    data = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))
    username = os.getenv("API_LOGIN") or input("Логин API: ")
    password = os.getenv("API_PASSWORD") or getpass("Пароль API: ")
    with requests.Session() as session:
        auth = request(session, "POST", "/users/obtain-token",
                       json={"username": username, "password": password})
        session.headers["Authorization"] = "Token " + auth["token"]

        driver = request(session, "POST", "/insured_objects/drivers", json=data["driver"])
        request(session, "GET", f"/insured_objects/drivers/{driver['id']}")

        owner = request(session, "POST", "/insured_objects/owners/natural_persons", json=data["owner"])
        owner_path = f"/insured_objects/owners/{person_id(owner)}"
        request(session, "GET", owner_path)
        request(session, "PATCH", owner_path, json=data["owner"])

        insurant = request(session, "POST", "/insured_objects/insurants/natural_persons", json=data["insurant"])
        insurant_path = f"/insured_objects/insurants/{person_id(insurant)}"
        request(session, "GET", insurant_path)
        request(session, "PATCH", insurant_path, json=data["insurant"])

        car = request(session, "POST", "/insured_objects/cars", json=data["car"])
        car_path = f"/insured_objects/cars/{car['id']}"
        request(session, "GET", car_path)
        request(session, "PATCH", car_path, json={"seats_count": 5, "color": "black"})

        insured = request(session, "POST", "/insured_objects/", json={
            "drivers": [driver["id"]], "owner": person_id(owner),
            "insurant": person_id(insurant), "car": car["id"],
        })
        request(session, "GET", f"/insured_objects/{insured['id']}")

        request(session, "GET", "/agreements/", params={"page": 1})

        start = date.today() + timedelta(days=7)
        try:
            end = start.replace(year=start.year + 1) - timedelta(days=1)
        except ValueError:
            end = start.replace(year=start.year + 1, day=28) - timedelta(days=1)
        agreement = request(session, "POST", "/agreements/calculations", json={
            "insured_object": insured["id"], "drivers_ids": [driver["id"]],
            "valid_from": start.isoformat(), "valid_to": end.isoformat(),
            "insurance_period": 8, "target_of_using": "PERSONAL",
            "is_car_without_registration": False, "engine_power": data["car"]["engine_power"],
            "has_car_trailer": False, "car_type": "B", "periods": [],
            "owner_registration": {key: value for key, value in data["owner"]["address"][0].items()
                                   if key != "address_type"},
        })
        request(session, "PATCH", f"/agreements/{agreement['id']}",
                json={"insured_object": insured["id"]})
        print("Готово. Ответы сохранены в results.json")


if __name__ == "__main__":
    try:
        main()
    except (requests.RequestException, ValueError, KeyError) as error:
        print("Запросы остановлены:", error)
        raise SystemExit(1)
    finally:
        (ROOT / "results.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
