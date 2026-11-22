import requests

from core.config import API_URL, REQUEST_TIMEOUT


class ApiError(Exception):
    pass


class EventApi:
    def __init__(self, session):
        self.session = session

    def _request(self, method, path, payload=None):
        try:
            response = self.session.request(
                method,
                f"{API_URL}/{path}",
                json=payload,
                headers={"Accept": "application/json"},
                timeout=REQUEST_TIMEOUT,
            )
        except requests.Timeout as error:
            raise ApiError("API не ответил вовремя. Проверьте результат перед повтором.") from error
        except requests.ConnectionError as error:
            raise ApiError(f"Нет связи с {API_URL}. Запустите WebAPI и повторите попытку.") from error
        except requests.RequestException as error:
            raise ApiError(f"Не удалось выполнить запрос: {error}") from error

        data = None
        if response.content:
            try:
                data = response.json()
            except requests.exceptions.JSONDecodeError as error:
                if response.ok:
                    raise ApiError("API вернул ответ не в формате JSON.") from error

        if not response.ok:
            messages = {
                400: "API отклонил данные запроса.",
                403: "Нет доступа.",
                404: "Запись не найдена.",
                409: "Такая регистрация уже существует.",
            }
            message = messages.get(response.status_code, "Ошибка API.")
            if isinstance(data, dict):
                message = data.get("message") or message
            raise ApiError(f"HTTP {response.status_code}. {message}")

        return data

    def get_employee(self, employee_id):
        return self._request("GET", f"Employees/{employee_id}")

    def get_events(self):
        return self._request("GET", "Events")

    def get_registrations(self, employee_id):
        return self._request("GET", f"Registrations/employee/{employee_id}")

    def get_registration(self, registration_id):
        return self._request("GET", f"Registrations/{registration_id}")

    def create_registration(self, employee_id, event_id, comment):
        self._request("POST", "Registrations", {
            "employeeId": employee_id,
            "eventId": event_id,
            "status": 0,
            "comment": comment,
        })

    def update_status(self, registration, status):
        self._request("PUT", f"Registrations/{registration['id']}", {
            "employeeId": registration["employeeId"],
            "eventId": registration["eventId"],
            "status": status,
            "comment": registration["comment"] or "",
        })

    def delete_registration(self, registration_id):
        self._request("DELETE", f"Registrations/{registration_id}")
