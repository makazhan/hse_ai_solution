"""Конфигурация pytest и общие фикстуры"""
import datetime
import pytest
import pytest_asyncio
from datetime import date, time
from uuid import uuid4

from src.domain.entities.incidents import Incident
from src.domain.enums.incidents import (
    Company, Region, IncidentClassification,
    InvestigationStatus, WorkExperience, InjuryType
)


@pytest.fixture
def sample_incident_data():
    """Тестовые данные инцидента"""
    return {
        "incident_date": date(2024, 1, 15),
        "incident_time": time(14, 30),
        "company": Company.KAZAKHTELECOM,
        "dzo": "ДЗО Алматы",
        "classification": IncidentClassification.WORK_ACCIDENT,
        "region": Region.ALMATY_CITY,
        "location": "Офис, 3 этаж",
        "victim_name": "Иванов Иван Иванович",
        "victim_birth_date": date(1985, 5, 20),
        "victim_position": "Инженер",
        "victim_work_experience": WorkExperience.FROM_1_TO_5_YEARS,
        "injury_type": InjuryType.NON_SEVERE,
        "diagnosis": "Ушиб руки",
        "description": "Тестовый инцидент",
        "investigation_status": InvestigationStatus.NOT_COMPLETED,
    }


@pytest.fixture
def sample_incident(sample_incident_data):
    """Создание тестовой сущности Incident"""
    now = datetime.datetime.now(datetime.timezone.utc)
    return Incident(
        id=uuid4(),
        created_at=now,
        updated_at=now,
        **sample_incident_data
    )


@pytest.fixture
def mock_mediator(mocker):
    """Мок медиатора для тестирования команд/запросов"""
    from src.application.mediator.base import Mediator
    return mocker.Mock(spec=Mediator)
