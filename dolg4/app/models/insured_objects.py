from uuid import UUID

from .owner import read_address
from .users import read_date, read_text


def read_id(label, default=None):
    return str(UUID(read_text(label, default)))


def read_drivers(default=None):
    value = read_text("UUID водителей через запятую", default)
    return list(dict.fromkeys(str(UUID(part.strip())) for part in value.split(",")))


def read_flag(label):
    value = read_text(f"{label} (да/нет)", "нет").casefold()
    if value not in {"да", "нет"}:
        raise ValueError("Введите «да» или «нет».")
    return value == "да"


def agreement_data(object_id, drivers):
    start = read_date("Начало договора")
    end = read_date("Окончание договора")
    if start >= end:
        raise ValueError("Окончание договора должно быть позже начала.")
    period = int(read_text("Код периода (8/11 — год, 3/6/9 — месяцы)", "11"))
    if period not in {3, 6, 8, 9, 11}:
        raise ValueError("Неизвестный код периода.")
    periods = []
    if period in {3, 6, 9}:
        first = read_date("Начало периода использования")
        last = read_date("Окончание периода использования")
        if not start <= first <= last <= end:
            raise ValueError("Период использования должен входить в срок договора.")
        periods.append({"start_date": first, "end_date": last})
    target = read_text("Цель (PERSONAL, TAXI, CARGO)", "PERSONAL").upper()
    if target not in {"PERSONAL", "TAXI", "CARGO"}:
        raise ValueError("Неизвестная цель использования.")
    power = int(read_text("Мощность двигателя, л. с."))
    if power <= 0:
        raise ValueError("Мощность должна быть положительной.")
    return {
        "insured_object": object_id,
        "valid_from": start,
        "valid_to": end,
        "insurance_period": period,
        "target_of_using": target,
        "drivers_ids": drivers,
        "is_car_without_registration": read_flag("ТС без регистрации"),
        "engine_power": power,
        "has_car_trailer": read_flag("Есть прицеп"),
        "car_type": read_text("Категория ТС", "B").upper(),
        "owner_registration": read_address(),
        "periods": periods,
    }
