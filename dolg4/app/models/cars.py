from .users import credential, read_number, read_text


def car_data():
    return {
        "car_model_id": read_number("ID модели автомобиля из справочника"),
        "engine_power": read_number("Мощность двигателя, л. с."),
        "vin_number": read_text("VIN"),
        "number_plate": read_text("Госномер"),
        "manufacturing_year": read_number("Год выпуска"),
        "credential": [credential("VEHICLE_REGISTRATION", "СТС")],
    }
