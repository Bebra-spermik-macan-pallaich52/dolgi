from .users import credential, personal_data, read_date


def driver_data():
    return {
        **personal_data(),
        "driving_experience_started": read_date("Дата начала стажа"),
        "driver_licenses": [credential("DRIVER_LICENSE", "удостоверения")],
    }
