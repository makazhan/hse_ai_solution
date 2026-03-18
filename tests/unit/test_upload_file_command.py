"""Тесты команды UploadFileCommand и sanitize_filename"""
import datetime
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.application.commands.files import UploadFileCommand, UploadFileCommandHandler
from src.domain.entities.files import UploadedFile


class TestSanitizeFilename:
    """Тесты санитизации имён файлов."""

    def _sanitize(self, filename: str) -> str:
        return UploadFileCommandHandler._sanitize_filename(filename)

    def test_normal_filename(self):
        assert self._sanitize("report.pdf") == "report.pdf"

    def test_filename_with_path(self):
        """Путь должен быть отброшен — остаётся только имя."""
        assert self._sanitize("/etc/passwd") == "passwd"
        assert self._sanitize("C:/Users/test/file.xlsx") == "file.xlsx"
        assert self._sanitize("../../secret.txt") == "secret.txt"

    def test_filename_with_null_bytes(self):
        """Null-байты и управляющие символы удаляются."""
        assert self._sanitize("test\x00.pdf") == "test.pdf"
        assert self._sanitize("test\x01\x02.pdf") == "test.pdf"

    def test_long_filename_truncated(self):
        """Слишком длинное имя обрезается до 255 символов."""
        long_name = "a" * 500 + ".pdf"
        result = self._sanitize(long_name)
        assert len(result) <= 255

    def test_empty_filename(self):
        """Пустое имя заменяется на 'unknown'."""
        assert self._sanitize("") == "unknown"


@pytest.mark.asyncio
async def test_upload_file_command_handler():
    """Интеграционный тест: загрузка файла через handler."""
    mock_storage = AsyncMock()
    mock_storage.upload.return_value = "uploads/2026/02/17/test.pdf"

    mock_repo = AsyncMock()
    now = datetime.datetime.now(datetime.timezone.utc)
    fake_entity = UploadedFile(
        id=uuid4(),
        original_filename="test.pdf",
        content_type="application/pdf",
        size_bytes=100,
        s3_key="uploads/2026/02/17/test.pdf",
        uploaded_at=now,
        created_at=now,
        updated_at=now,
    )
    mock_repo.create.return_value = fake_entity

    handler = UploadFileCommandHandler(
        file_storage=mock_storage,
        file_repository=mock_repo,
        _mediator=None,
    )

    command = UploadFileCommand(
        file_content=b"fake pdf content",
        filename="test.pdf",
        content_type="application/pdf",
    )

    result = await handler.handle(command)

    assert result.original_filename == "test.pdf"
    mock_storage.upload.assert_called_once()
    mock_repo.create.assert_called_once()

    # Проверяем, что entity передана с правильными полями
    created_entity = mock_repo.create.call_args[0][0]
    assert created_entity.content_type == "application/pdf"
    assert created_entity.size_bytes == len(b"fake pdf content")
