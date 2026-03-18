"""Тесты доменной сущности Incident"""
import pytest
from datetime import date
from uuid import uuid4

from src.domain.entities.incidents import Incident
from src.domain.enums.incidents import Company, Region, IncidentClassification, InvestigationStatus


def test_incident_entity_creation(sample_incident_data):
    """Создание сущности с валидными данными"""
    incident = Incident(
        id=uuid4(),
        created_at=date.today(),
        updated_at=date.today(),
        **sample_incident_data
    )

    assert incident.id is not None
    assert incident.company == Company.KAZAKHTELECOM
    assert incident.region == Region.ALMATY_CITY
    assert incident.description == "Тестовый инцидент"


def test_incident_entity_requires_required_fields(sample_incident_data):
    """Обязательные поля должны быть заполнены"""
    # Убираем обязательное поле
    incomplete_data = sample_incident_data.copy()
    del incomplete_data['incident_date']

    with pytest.raises((TypeError, Exception)):
        Incident(
            id=uuid4(),
            created_at=date.today(),
            updated_at=date.today(),
            **incomplete_data
        )


def test_incident_entity_with_optional_fields():
    """Создание с минимальным набором обязательных полей"""
    incident = Incident(
        id=uuid4(),
        incident_date=date(2024, 1, 15),
        company=Company.KAZAKHTELECOM,
        classification=IncidentClassification.WORK_ACCIDENT,
        region=Region.ALMATY_CITY,
        location="Test location",
        description="Test description",
        investigation_status=InvestigationStatus.NOT_COMPLETED,
        created_at=date.today(),
        updated_at=date.today(),
    )

    assert incident.id is not None
    assert incident.victim_name is None
    assert incident.diagnosis is None
