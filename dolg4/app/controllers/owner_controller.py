OWNERS = "/insured_objects/owners"
INSURANTS = "/insured_objects/insurants"


def person_id(record):
    person = record.get("person")
    return person.get("id") if isinstance(person, dict) else person
