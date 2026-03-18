"""Тесты CreateIncidentCommand и обработчика"""
import pytest
from uuid import uuid4
from datetime import date

from src.application.commands.incidents import (
    CreateIncidentCommand,
    CreateIncidentCommandHandler,
)
from src.domain.entities.incidents import Incident
from src.domain.enums.incidents import (
    Company, Region, IncidentClassification, InvestigationStatus
)


@pytest.mark.asyncio
async def test_create_incident_command_handler(mocker, sample_incident_data):
    """Обработчик корректно создаёт инцидент"""
    # Arrange
    mock_repo = mocker.AsyncMock()
    expected_incident = Incident(
        id=uuid4(),
        created_at=date.today(),
        updated_at=date.today(),
        **sample_incident_data
    )
    mock_repo.create.return_value = expected_incident

    handler = CreateIncidentCommandHandler(
        incident_repository=mock_repo,
        _mediator=None
    )

    command = CreateIncidentCommand(**sample_incident_data)

    # Act
    result = await handler.handle(command)

    # Assert
    assert result.id == expected_incident.id
    assert result.company == Company.KAZAKHTELECOM
    assert result.classification == IncidentClassification.WORK_ACCIDENT
    mock_repo.create.assert_called_once()


def test_create_incident_command_immutable(sample_incident_data):
    """Команда неизменяема (frozen dataclass)"""
    command = CreateIncidentCommand(**sample_incident_data)

    with pytest.raises(AttributeError):
        command.description = "Modified description"
