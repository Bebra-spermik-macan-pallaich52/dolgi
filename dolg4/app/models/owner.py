from .users import credential, personal_data, read_text


def read_address():
    return {
        "address_query": read_text("Полный адрес"),
        "region_kladr_id": read_text("Код региона КЛАДР"),
        "city_kladr_id": read_text("Код города КЛАДР"),
    }


def person_data():
    person = personal_data()
    passport = credential("RUSSIAN_INTERNAL_PASSPORT", "паспорта")
    passport["issue_point"] = read_text("Кем выдан паспорт")
    passport["issue_point_code"] = read_text("Код подразделения")
    address = read_address()
    return {
        **person,
        "credential": [passport],
        "address": [
            {**address, "address_type": kind}
            for kind in ("LEGAL_ADDRESS", "ACTUAL_ADDRESS")
        ],
    }
