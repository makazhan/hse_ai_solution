from dataclasses import dataclass
from uuid import UUID

from src.domain.events.base import BaseEvent


@dataclass
class IncidentCreatedEvent(BaseEvent):
    """Событие создания инцидента"""
    incident_id: UUID
    company: str
    classification: str


@dataclass
class EnquiryActUploadedEvent(BaseEvent):
    """Событие загрузки акта расследования"""
    act_id: UUID
    incident_id: UUID


@dataclass
class AnalysisRequestedEvent(BaseEvent):
    """Запрос на AI-анализ"""
    incident_ids: list[UUID]
    analysis_type: str  # 'risk', 'recommendation', 'report'
