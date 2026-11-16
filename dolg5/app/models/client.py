from dataclasses import dataclass, field


@dataclass
class Client:
    id: int | None = None
    username: str = ""
    password_hash: str = field(default="", repr=False)
    phone: str | None = None
    email: str = ""

    def to_dict(self) -> dict:
        """Публичное представление клиента без хеша пароля."""
        return {
            "id": self.id,
            "username": self.username,
            "phone": self.phone,
            "email": self.email,
        }
