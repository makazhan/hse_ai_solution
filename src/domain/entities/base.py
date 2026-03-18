import uuid
from abc import ABC
from copy import copy
from dataclasses import (
    dataclass,
    field,
)
from typing import Optional
from uuid import UUID

from src.domain.events.base import BaseEvent


@dataclass
class BaseEntity(ABC):
    id: UUID = field(default_factory=uuid.uuid4, kw_only=True)  # noqa

    _events: list[BaseEvent] = field(
        default_factory=list,
        kw_only=True,
    )

    def register_event(self, event: BaseEvent, position: Optional[int] = None) -> None:
        if position is not None:
            self._events.insert(position, event)
        else:
            self._events.append(event)

    def pull_events(self) -> list[BaseEvent]:
        registered_events = copy(self._events)
        self._events.clear()
        return registered_events
