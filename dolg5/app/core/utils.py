"""Вспомогательные функции приложения."""

import hashlib
import secrets


def hash_password(password: str) -> str:
    """PBKDF2-SHA256 с индивидуальной случайной солью для каждого пароля."""
    if not password:
        raise ValueError("Пароль не должен быть пустым.")
    iterations = 600_000
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"
