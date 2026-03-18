from dataclasses import dataclass


@dataclass(frozen=True, eq=False)
class ApplicationException(Exception):
    @property
    def message(self):
        return 'Возникла ошибка приложения'


@dataclass(frozen=True, eq=False)
class NotFoundException(ApplicationException):
    """Базовый класс для всех «не найдено» исключений (→ HTTP 404)."""

    @property
    def message(self):
        return 'Ресурс не найден'
