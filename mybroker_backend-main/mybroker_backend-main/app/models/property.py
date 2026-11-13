from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Property:
    id: int
    seller_id: int | None
    title: str | None
    document_url: str | None
    created_at: datetime


class PropertyStore:
    def __init__(self) -> None:
        self._items: list[Property] = []
        self._next_id = 1

    def create(
        self,
        seller_id: int | None,
        title: str | None,
        document_url: str | None,
    ) -> Property:
        prop = Property(
            id=self._next_id,
            seller_id=seller_id,
            title=title,
            document_url=document_url,
            created_at=datetime.utcnow(),
        )
        self._items.append(prop)
        self._next_id += 1
        return prop

    def all(self) -> list[Property]:
        return list(self._items)
