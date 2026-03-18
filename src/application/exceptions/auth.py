from dataclasses import dataclass

from src.application.exceptions.base import ApplicationException


@dataclass(frozen=True, eq=False)
class AuthClientBadRequestException(ApplicationException):
    session_id: str

    @property
    def message(self):
        return 'Невалидная сессия'


@dataclass(frozen=True, eq=False)
class AuthServiceUnavailableException(ApplicationException):
    @property
    def message(self):
        return 'Сервис авторизации недоступен'
