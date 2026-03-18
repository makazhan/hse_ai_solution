import datetime
import uuid
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UploadedFile(BaseModel):
    """Загруженный файл (метаданные). Сам файл хранится в S3."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: UUID = Field(default_factory=uuid.uuid4)
    original_filename: str
    content_type: str
    size_bytes: int
    s3_key: str  # "uploads/2026/02/17/{uuid}.xlsx"
    uploaded_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
