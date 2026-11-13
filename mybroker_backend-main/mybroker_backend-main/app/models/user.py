from dataclasses import dataclass
import json
import os
from pathlib import Path


@dataclass(frozen=True)
class User:
    id: int
    role: str
    fcm_token: str


class UserStore:
    def __init__(self, users: list[User]) -> None:
        self._users = users

    @staticmethod
    def _parse_items(items: list[dict]) -> list[User]:
        users = [
            User(
                id=int(item.get("id", 0)),
                role=str(item.get("role", "")).strip(),
                fcm_token=str(item.get("fcm_token", "")).strip(),
            )
            for item in items
            if item
        ]
        return [u for u in users if u.id and u.role and u.fcm_token]

    @classmethod
    def from_env(cls) -> "UserStore":
        raw = os.getenv("NOTIFICATION_USERS_JSON", "").strip()
        if not raw:
            return cls([])
        try:
            items = json.loads(raw)
            return cls(cls._parse_items(items))
        except json.JSONDecodeError:
            return cls([])

    @classmethod
    def from_file(cls, path: str | None) -> "UserStore":
        if not path:
            return cls([])
        try:
            file_path = Path(path)
            if not file_path.exists():
                return cls([])
            raw = file_path.read_text(encoding="utf-8").strip()
            if not raw:
                return cls([])
            items = json.loads(raw)
            return cls(cls._parse_items(items))
        except (OSError, json.JSONDecodeError):
            return cls([])

    @classmethod
    def from_sources(cls, path: str | None) -> "UserStore":
        env_users = cls.from_env()._users
        file_users = cls.from_file(path)._users
        merged: dict[int, User] = {}
        for user in env_users + file_users:
            merged[user.id] = user
        return cls(list(merged.values()))

    def get_by_roles(self, roles: list[str]) -> list[User]:
        role_set = {r.strip().lower() for r in roles}
        return [u for u in self._users if u.role.lower() in role_set]

    def upsert(self, user: User) -> None:
        existing = {u.id: u for u in self._users}
        existing[user.id] = user
        self._users = list(existing.values())

    def to_json_list(self) -> list[dict]:
        return [
            {"id": u.id, "role": u.role, "fcm_token": u.fcm_token}
            for u in sorted(self._users, key=lambda item: item.id)
        ]

    def save_to_file(self, path: str | None) -> None:
        if not path:
            return
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self.to_json_list(), ensure_ascii=True, indent=2)
        file_path.write_text(payload, encoding="utf-8")
