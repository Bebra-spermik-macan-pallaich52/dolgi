from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

ph = PasswordHasher()


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Пароль не должен быть пустым.")
    return ph.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return ph.verify(hashed, plain)
    except (InvalidHashError, VerificationError):
        return False
