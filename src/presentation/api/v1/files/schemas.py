from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.domain.entities.files import UploadedFile


class UploadedFileResponseSchema(BaseModel):
    """Ответ после загрузки файла."""
    file_id: UUID
    filename: str
    size_bytes: int
    content_type: str
    presigned_url: str

    class Config:
        from_attributes = True

    @classmethod
    def from_entity(cls, entity: UploadedFile, presigned_url: str) -> 'UploadedFileResponseSchema':
        return cls(
            file_id=entity.id,
            filename=entity.original_filename,
            size_bytes=entity.size_bytes,
            content_type=entity.content_type,
            presigned_url=presigned_url,
        )
