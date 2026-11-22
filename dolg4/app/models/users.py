from datetime import date


def read_text(label, default=None):
    hint = f" [{default}]" if default is not None else ""
    value = input(f"{label}{hint}: ").strip()
    if value:
        return value
    if default is not None:
        return default
    raise ValueError(f"Заполните поле «{label}».")


def read_date(label):
    value = read_text(f"{label} (ГГГГ-ММ-ДД)")
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("Введите дату в формате ГГГГ-ММ-ДД.")
    return value


def read_number(label):
    value = int(read_text(label))
    if value <= 0:
        raise ValueError(f"Поле «{label}» должно быть положительным.")
    return value


def personal_data():
    return {
        "last_name": read_text("Фамилия"),
        "first_name": read_text("Имя"),
        "patronymic": read_text("Отчество"),
        "birth_date": read_date("Дата рождения"),
    }


def credential(kind, label):
    return {
        "credential_type": kind,
        "series": read_text(f"Серия {label}"),
        "number": read_text(f"Номер {label}"),
        "issue_date": read_date(f"Дата выдачи {label}"),
    }
