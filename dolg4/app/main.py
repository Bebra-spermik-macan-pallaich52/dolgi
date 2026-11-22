import json
from getpass import getpass

import requests

from .controllers.cars_controller import CARS
from .controllers.drivers_controller import DRIVERS
from .controllers.insured_objects_controller import (
    AGREEMENTS, OBJECTS, calculate, create_object, list_agreements,
)
from .controllers.owner_controller import INSURANTS, OWNERS, person_id
from .controllers.users_controller import Api, ApiError
from .models.cars import car_data
from .models.drivers import driver_data
from .models.insured_objects import agreement_data, read_drivers, read_id
from .models.owner import person_data
from .models.users import read_text


def show(result):
    print(json.dumps(result, ensure_ascii=False, indent=2) if result is not None else "Готово.")


def created_id(result):
    record_id = result.get("id") if isinstance(result, dict) else None
    if not record_id:
        raise ApiError("API не вернул ID записи. Проверьте результат перед повтором.")
    print(f"Создана запись {record_id}")
    return record_id


def read_patch():
    try:
        body = json.loads(read_text('Изменяемые поля в JSON, например {"last_name":"Иванова"}'))
    except json.JSONDecodeError as error:
        raise ValueError("Введите корректный JSON в одну строку.") from error
    if not isinstance(body, dict) or not body:
        raise ValueError("Нужен JSON-объект с полями для изменения.")
    return body


def manage_record(api, path, build_data, records, *, editable=True, natural_person=False):
    print("1. Создать\n2. Посмотреть")
    if editable:
        print("3. Изменить")
    action = read_text("Действие")
    if action == "1":
        create_path = path + "/natural_persons" if natural_person else path
        result = api.request("POST", create_path, build_data())
        records[path] = {"id": created_id(result)}
        if natural_person:
            reference = person_id(result)
            records[path]["person"] = reference
            if reference:
                print(f"ID физлица для объекта страхования {reference}")
        return
    if action not in ({"2", "3"} if editable else {"2"}):
        raise ValueError("Выберите действие из меню.")
    record_id = read_id("UUID записи", records.get(path, {}).get("id"))
    item_path = path + "/" + record_id
    if action == "2":
        show(api.request("GET", item_path))
    else:
        show(api.request("PATCH", item_path, read_patch()))


def manage_object(api, records):
    print("1. Связать записи\n2. Посмотреть объект")
    action = read_text("Действие")
    if action == "2":
        record_id = read_id("UUID объекта страхования", records.get(OBJECTS, {}).get("id"))
        show(api.request("GET", OBJECTS + "/" + record_id))
        return
    if action != "1":
        raise ValueError("Выберите действие из меню.")
    drivers = read_drivers(records.get(DRIVERS, {}).get("id"))
    owner = read_id("UUID физлица собственника", records.get(OWNERS, {}).get("person"))
    insurant = read_id("UUID физлица страхователя", records.get(INSURANTS, {}).get("person"))
    car = read_id("UUID автомобиля", records.get(CARS, {}).get("id"))
    result = create_object(api, drivers, owner, insurant, car)
    records[OBJECTS] = {"id": created_id(result), "drivers": drivers}


def calculate_agreement(api, records):
    insured = records.get(OBJECTS, {})
    record_id = read_id("UUID объекта страхования", insured.get("id"))
    previous_drivers = insured.get("drivers", []) if record_id == insured.get("id") else []
    drivers = read_drivers(",".join(previous_drivers) or None)
    result = calculate(api, agreement_data(record_id, drivers))
    records[AGREEMENTS] = {"id": created_id(result)}
    calculation = result.get("calculation")
    if isinstance(calculation, dict) and calculation.get("premium") is not None:
        print(f"Страховая премия по ответу API: {calculation['premium']}")
    print(f"Статус: {result.get('status') or 'не указан'}")


def update_agreement(api, records):
    record_id = read_id("UUID договора", records.get(AGREEMENTS, {}).get("id"))
    show(api.request("PATCH", AGREEMENTS + "/" + record_id, read_patch()))


def run(api):
    api.login(read_text("Логин учебного аккаунта"), getpass("Пароль: "))
    print("Вход выполнен.")
    records = {}
    while True:
        print(
            "\n1. Водитель\n2. Собственник\n3. Страхователь\n4. Автомобиль"
            "\n5. Объект страхования\n6. Рассчитать договор"
            "\n7. Список договоров\n8. Изменить договор\n0. Выход"
        )
        action = input("Выберите пункт: ").strip()
        try:
            if action == "0":
                return
            if action == "1":
                manage_record(api, DRIVERS, driver_data, records, editable=False)
            elif action == "2":
                manage_record(api, OWNERS, person_data, records, natural_person=True)
            elif action == "3":
                manage_record(api, INSURANTS, person_data, records, natural_person=True)
            elif action == "4":
                manage_record(api, CARS, car_data, records)
            elif action == "5":
                manage_object(api, records)
            elif action == "6":
                calculate_agreement(api, records)
            elif action == "7":
                show(list_agreements(api))
            elif action == "8":
                update_agreement(api, records)
            else:
                print("Такого пункта меню нет.")
        except (ApiError, ValueError) as error:
            print(error)


def main():
    try:
        with requests.Session() as session:
            run(Api(session))
    except (ApiError, ValueError) as error:
        print(error)
        return 1
    except (EOFError, KeyboardInterrupt):
        print("\nРабота завершена.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
