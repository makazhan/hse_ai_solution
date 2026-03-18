from dataclasses import dataclass
from uuid import UUID

from src.application.exceptions.base import ApplicationException, NotFoundException


@dataclass(frozen=True, eq=False)
class IncidentNotFoundException(NotFoundException):
    incident_id: UUID

    @property
    def message(self):
        return f"Инцидент с ID {self.incident_id} не найден"


@dataclass(frozen=True, eq=False)
class RecommendationNotFoundException(NotFoundException):
    recommendation_id: UUID

    @property
    def message(self):
        return f"Рекомендация с ID {self.recommendation_id} не найдена"


@dataclass(frozen=True, eq=False)
class EnquiryActNotFoundException(NotFoundException):
    act_id: UUID

    @property
    def message(self):
        return f"Акт расследования с ID {self.act_id} не найден"


@dataclass(frozen=True, eq=False)
class InvalidCompanyException(ApplicationException):
    company: str

    @property
    def message(self):
        return f"Недопустимое значение компании: {self.company}"
