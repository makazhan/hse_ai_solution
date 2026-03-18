"""Тесты команды UploadEnquiryActCommand"""
import datetime
import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from src.application.commands.incidents import UploadEnquiryActCommand, UploadEnquiryActCommandHandler
from src.application.exceptions.files import UnsupportedFileTypeException, UploadedFileNotFoundException
from src.domain.entities.files import UploadedFile
from src.domain.entities.incidents import EnquiryAct


def _make_uploaded_file(filename: str) -> UploadedFile:
    """Создание заглушки UploadedFile."""
    now = datetime.datetime.now(datetime.timezone.utc)
    return UploadedFile(
        id=uuid4(),
        original_filename=filename,
        content_type="application/pdf",
        size_bytes=100,
        s3_key=f"uploads/2026/02/17/{uuid4()}.pdf",
        uploaded_at=now,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_upload_act_file_not_found():
    """Если file_id не найден — UploadedFileNotFoundException."""
    mock_file_repo = AsyncMock()
    mock_file_repo.get_by_id.return_value = None

    handler = UploadEnquiryActCommandHandler(
        incident_repository=AsyncMock(),
        enquiry_act_repository=AsyncMock(),
        file_repository=mock_file_repo,
        file_storage=AsyncMock(),
        _mediator=None,
    )

    command = UploadEnquiryActCommand(file_id=uuid4())

    with pytest.raises(UploadedFileNotFoundException):
        await handler.handle(command)


@pytest.mark.asyncio
async def test_upload_act_unsupported_extension():
    """Если расширение файла не pdf/docx — UnsupportedFileTypeException."""
    fake_file = _make_uploaded_file("report.txt")
    mock_file_repo = AsyncMock()
    mock_file_repo.get_by_id.return_value = fake_file

    mock_storage = AsyncMock()
    mock_storage.download.return_value = b"some content"

    handler = UploadEnquiryActCommandHandler(
        incident_repository=AsyncMock(),
        enquiry_act_repository=AsyncMock(),
        file_repository=mock_file_repo,
        file_storage=mock_storage,
        _mediator=None,
    )

    command = UploadEnquiryActCommand(file_id=fake_file.id)

    with pytest.raises(UnsupportedFileTypeException):
        await handler.handle(command)


@pytest.mark.asyncio
async def test_upload_act_doc_extension_rejected():
    """Формат .doc не поддерживается (только .docx)."""
    fake_file = _make_uploaded_file("report.doc")
    mock_file_repo = AsyncMock()
    mock_file_repo.get_by_id.return_value = fake_file

    mock_storage = AsyncMock()
    mock_storage.download.return_value = b"some content"

    handler = UploadEnquiryActCommandHandler(
        incident_repository=AsyncMock(),
        enquiry_act_repository=AsyncMock(),
        file_repository=mock_file_repo,
        file_storage=mock_storage,
        _mediator=None,
    )

    command = UploadEnquiryActCommand(file_id=fake_file.id)

    with pytest.raises(UnsupportedFileTypeException):
        await handler.handle(command)
