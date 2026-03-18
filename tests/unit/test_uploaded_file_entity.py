"""Тесты доменной сущности UploadedFile"""
import datetime
from uuid import uuid4

from src.domain.entities.files import UploadedFile


def test_uploaded_file_creation():
    """Создание сущности загруженного файла."""
    file_id = uuid4()
    now = datetime.datetime.now(datetime.timezone.utc)

    entity = UploadedFile(
        id=file_id,
        original_filename="test_report.pdf",
        content_type="application/pdf",
        size_bytes=1024,
        s3_key=f"uploads/2026/02/17/{file_id}.pdf",
        uploaded_at=now,
        created_at=now,
        updated_at=now,
    )

    assert entity.id == file_id
    assert entity.original_filename == "test_report.pdf"
    assert entity.size_bytes == 1024


def test_uploaded_file_timestamps_are_utc():
    """Дефолтные timestamps должны быть timezone-aware (UTC)."""
    entity = UploadedFile(
        original_filename="test.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        size_bytes=2048,
        s3_key="uploads/2026/02/17/test.xlsx",
    )

    assert entity.created_at.tzinfo is not None
    assert entity.uploaded_at.tzinfo is not None
    assert entity.updated_at.tzinfo is not None
