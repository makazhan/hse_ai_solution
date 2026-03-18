from dataclasses import dataclass

from src.application.exceptions.base import ApplicationException


@dataclass(frozen=True, eq=False)
class EventHandlersNotRegisteredException(ApplicationException):
    event_type: type

    @property
    def message(self):
        return f'Не найден хендлер для ивента: {self.event_type}'


@dataclass(frozen=True, eq=False)
class CommandHandlersNotRegisteredException(ApplicationException):
    command_type: type

    @property
    def message(self):
        return f'Не найден хендлер для команды: {self.command_type}'


@dataclass(frozen=True, eq=False)
class QueryHandlersNotRegisteredException(ApplicationException):
    query_type: type

    @property
    def message(self):
        return f'Не найден хендлер для квери: {self.query_type}'
