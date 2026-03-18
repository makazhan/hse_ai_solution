from abc import (
    ABC,
    abstractmethod,
)
from dataclasses import dataclass, field
from typing import (
    Any,
    Generic,
    TypeVar,
)

from src.application.mediator.event import EventMediator


@dataclass(frozen=True)
class BaseCommand(ABC):
    ...


CT = TypeVar('CT', bound=BaseCommand)
CR = TypeVar('CR', bound=Any)


class CommandHandler(ABC, Generic[CT, CR]):
    @abstractmethod
    async def handle(self, command: CT) -> CR:
        ...
