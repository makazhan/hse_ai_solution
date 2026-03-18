"""Тесты OCR-fallback в UploadEnquiryActCommandHandler."""
import datetime
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from src.application.commands.incidents import UploadEnquiryActCommand, UploadEnquiryActCommandHandler
from src.domain.entities.files import UploadedFile
from src.domain.entities.incidents import EnquiryAct


def _make_uploaded_pdf(filename: str = "scan.pdf") -> UploadedFile:
    now = datetime.datetime.now(datetime.timezone.utc)
    return UploadedFile(
        id=uuid4(),
        original_filename=filename,
        content_type="application/pdf",
        size_bytes=1000,
        s3_key=f"uploads/2026/02/18/{uuid4()}.pdf",
        uploaded_at=now,
        created_at=now,
        updated_at=now,
    )


def _make_handler(
    file_repo: AsyncMock,
    file_storage: AsyncMock,
    act_repo: AsyncMock | None = None,
    ocr_service: AsyncMock | None = None,
) -> UploadEnquiryActCommandHandler:
    if act_repo is None:
        act_repo = AsyncMock()
        act_repo.create.side_effect = lambda act: act
    return UploadEnquiryActCommandHandler(
        incident_repository=AsyncMock(),
        enquiry_act_repository=act_repo,
        file_repository=file_repo,
        file_storage=file_storage,
        ocr_service=ocr_service,
        _mediator=None,
    )


@pytest.mark.asyncio
async def test_pdf_with_text_does_not_call_ocr():
    """PDF с текстовым слоем — OCR не вызывается."""
    fake_file = _make_uploaded_pdf()
    file_repo = AsyncMock()
    file_repo.get_by_id.return_value = fake_file

    file_storage = AsyncMock()
    file_storage.download.return_value = b"fake-pdf-bytes"

    ocr_service = AsyncMock()

    handler = _make_handler(file_repo, file_storage, ocr_service=ocr_service)
    command = UploadEnquiryActCommand(file_id=fake_file.id)

    with patch("src.application.commands.incidents.asyncio.to_thread", new_callable=AsyncMock, return_value="Нормальный текст из PDF"):
        await handler.handle(command)

    ocr_service.extract_text_from_pdf.assert_not_called()


@pytest.mark.asyncio
async def test_scanned_pdf_triggers_ocr():
    """PDF с пустым текстом + OCR доступен — вызывается OCR."""
    fake_file = _make_uploaded_pdf()
    file_repo = AsyncMock()
    file_repo.get_by_id.return_value = fake_file

    file_storage = AsyncMock()
    file_storage.download.return_value = b"fake-scanned-pdf-bytes"

    ocr_service = AsyncMock()
    ocr_service.extract_text_from_pdf.return_value = "Текст из OCR"

    act_repo = AsyncMock()
    act_repo.create.side_effect = lambda act: act

    handler = _make_handler(file_repo, file_storage, act_repo=act_repo, ocr_service=ocr_service)
    command = UploadEnquiryActCommand(file_id=fake_file.id)

    with patch("src.application.commands.incidents.asyncio.to_thread", new_callable=AsyncMock, return_value="   \n  "):
        result = await handler.handle(command)

    ocr_service.extract_text_from_pdf.assert_called_once_with(b"fake-scanned-pdf-bytes")
    assert result.extracted_text == "Текст из OCR"


@pytest.mark.asyncio
async def test_scanned_pdf_without_ocr_service_returns_empty():
    """PDF с пустым текстом + OCR=None — возвращается пустой текст."""
    fake_file = _make_uploaded_pdf()
    file_repo = AsyncMock()
    file_repo.get_by_id.return_value = fake_file

    file_storage = AsyncMock()
    file_storage.download.return_value = b"fake-scanned-pdf-bytes"

    act_repo = AsyncMock()
    act_repo.create.side_effect = lambda act: act

    handler = _make_handler(file_repo, file_storage, act_repo=act_repo, ocr_service=None)
    command = UploadEnquiryActCommand(file_id=fake_file.id)

    with patch("src.application.commands.incidents.asyncio.to_thread", new_callable=AsyncMock, return_value=""):
        result = await handler.handle(command)

    assert result.extracted_text == ""


@pytest.mark.asyncio
async def test_ocr_exception_propagates():
    """Если OCR выбрасывает исключение — оно пробрасывается наверх."""
    fake_file = _make_uploaded_pdf()
    file_repo = AsyncMock()
    file_repo.get_by_id.return_value = fake_file

    file_storage = AsyncMock()
    file_storage.download.return_value = b"fake-scanned-pdf-bytes"

    ocr_service = AsyncMock()
    ocr_service.extract_text_from_pdf.side_effect = RuntimeError("Qwen API unavailable")

    handler = _make_handler(file_repo, file_storage, ocr_service=ocr_service)
    command = UploadEnquiryActCommand(file_id=fake_file.id)

    with patch("src.application.commands.incidents.asyncio.to_thread", new_callable=AsyncMock, return_value=""):
        with pytest.raises(RuntimeError, match="Qwen API unavailable"):
            await handler.handle(command)
