import requests

from api.client import ApiError, EventApi

STATUSES = {
    "Registered": "Зарегистрирован",
    "Attended": "Посетил",
    "Cancelled": "Отменён",
    "NotAttended": "Не посетил",
}


def read_id(prompt):
    try:
        value = int(input(prompt).strip())
        if 1 <= value <= 2_147_483_647:
            return value
    except ValueError:
        pass
    raise ValueError("Введите корректный положительный ID.")


def show_events(events):
    print("\nМероприятия")
    if not events:
        print("Список мероприятий пуст.")
    for event in events:
        print(f"{event['id']} | {event['title']} | {event['date']}")


def registration_line(registration):
    date = registration["registrationDate"].replace("T", " ", 1)
    status = STATUSES.get(registration["status"], registration["status"])
    comment = registration["comment"] or "—"
    return f"{registration['id']} | {registration['eventTitle']} | {date} | {status} | {comment}"


def show_registrations(registrations):
    print("\nМои регистрации")
    if registrations:
        print("ID | Мероприятие | Дата регистрации | Статус | Комментарий")
        for registration in registrations:
            print(registration_line(registration))
    else:
        print("Регистраций пока нет.")


def refresh_registrations(api, employee_id):
    show_registrations(api.get_registrations(employee_id))


def get_own_registration(api, employee_id):
    registration_id = read_id("ID регистрации: ")
    registration = api.get_registration(registration_id)
    if registration["employeeId"] != employee_id:
        raise ValueError("Нет доступа: регистрация принадлежит другому сотруднику.")
    return registration


def create_registration(api, employee_id, events):
    show_events(events)
    if not events:
        return
    event_id = read_id("ID мероприятия: ")
    if not any(event["id"] == event_id for event in events):
        raise ValueError("Мероприятие с таким ID не найдено.")
    registrations = api.get_registrations(employee_id)
    if any(item["eventId"] == event_id and item["status"] != "Cancelled"
           for item in registrations):
        raise ValueError("У вас уже есть регистрация на это мероприятие.")
    comment = input("Комментарий (необязательно): ").strip()
    api.create_registration(employee_id, event_id, comment)
    print("Регистрация создана.")
    refresh_registrations(api, employee_id)


def change_status(api, employee_id):
    registration = get_own_registration(api, employee_id)
    options = {"1": 0, "2": 2, "3": 1}
    print("1. Зарегистрирован\n2. Посетил\n3. Отменён")
    choice = input("Новый статус: ").strip()
    if choice not in options:
        raise ValueError("Выберите статус от 1 до 3.")
    api.update_status(registration, options[choice])
    print("Статус обновлён.")
    refresh_registrations(api, employee_id)


def delete_registration(api, employee_id):
    registration = get_own_registration(api, employee_id)
    confirmation = input("Удалить регистрацию? [да/нет]: ").strip().casefold()
    if confirmation not in {"да", "д"}:
        print("Удаление отменено.")
        return
    api.delete_registration(registration["id"])
    print("Регистрация удалена.")
    refresh_registrations(api, employee_id)


def run(api):
    employee_id = read_id("Введите ID сотрудника: ")
    employee = api.get_employee(employee_id)
    full_name = " ".join(
        employee[field] for field in ("lastName", "firstName", "patronymic")
        if employee.get(field)
    )
    print(f"Вошедший пользователь: {full_name} (ID: {employee_id})")
    show_events(api.get_events())
    refresh_registrations(api, employee_id)

    while True:
        print("\n1. Мероприятия\n2. Мои регистрации\n3. Зарегистрироваться"
              "\n4. Просмотреть регистрацию\n5. Изменить статус"
              "\n6. Удалить регистрацию\n0. Выход")
        choice = input("Выберите действие: ").strip()
        try:
            if choice == "0":
                return
            if choice == "1":
                show_events(api.get_events())
            elif choice == "2":
                refresh_registrations(api, employee_id)
            elif choice == "3":
                create_registration(api, employee_id, api.get_events())
            elif choice == "4":
                print(registration_line(get_own_registration(api, employee_id)))
            elif choice == "5":
                change_status(api, employee_id)
            elif choice == "6":
                delete_registration(api, employee_id)
            else:
                print("Такого пункта меню нет.")
        except (ApiError, ValueError) as error:
            print(error)


def main():
    try:
        with requests.Session() as session:
            run(EventApi(session))
    except (ApiError, ValueError) as error:
        print(error)
        return 1
    except (EOFError, KeyboardInterrupt):
        print("\nРабота завершена.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
