import requests

from config import BASE_URL, TIMEOUT


class ApiError(Exception):
    pass


class Api:
    def __init__(self, session):
        self.session = session
        self.session.headers.update({"Accept": "application/json", "User-Agent": "Mozilla/5.0"})

    def request(self, method, path, body=None):
        try:
            response = self.session.request(
                method, BASE_URL + path, json=body, timeout=TIMEOUT, allow_redirects=False
            )
        except requests.Timeout as error:
            raise ApiError("API не ответил вовремя. Проверьте результат перед повтором запроса.") from error
        except requests.RequestException as error:
            raise ApiError("Не удалось подключиться к API.") from error

        if not 200 <= response.status_code < 300:
            problems = {
                400: "API отклонил данные.",
                401: "Проверьте логин и пароль или войдите заново.",
                403: "Доступ запрещён.",
                404: "Запись не найдена.",
            }
            message = problems.get(response.status_code, "Ошибка API.")
            if path != "/users/obtain-token":
                try:
                    detail = response.json()
                except ValueError:
                    detail = None
                if detail:
                    message = f"{message} {detail}"
            raise ApiError(f"HTTP {response.status_code}. {message}")

        if not response.content:
            return None
        try:
            return response.json()
        except ValueError as error:
            raise ApiError("В ответе API нет корректного JSON.") from error

    def login(self, username, password):
        data = self.request("POST", "/users/obtain-token", {
            "username": username,
            "password": password,
        })
        token = data.get("token") if isinstance(data, dict) else None
        if not isinstance(token, str) or not token.strip():
            raise ApiError("API не вернул токен.")
        self.session.headers["Authorization"] = f"Token {token}"
