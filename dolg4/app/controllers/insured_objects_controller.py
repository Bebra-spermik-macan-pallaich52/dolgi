OBJECTS = "/insured_objects"
AGREEMENTS = "/agreements"


def create_object(api, drivers, owner, insurant, car):
    return api.request("POST", OBJECTS + "/", {
        "drivers": drivers,
        "owner": owner,
        "insurant": insurant,
        "car": car,
    })


def calculate(api, body):
    return api.request("POST", AGREEMENTS + "/calculations", body)


def list_agreements(api):
    return api.request("GET", AGREEMENTS + "/")
