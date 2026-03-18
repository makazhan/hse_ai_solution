import uuid
import datetime

from sqlalchemy import String, BigInteger, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.domain.entities.files import UploadedFile
from src.infrastructure.db.sqlalchemy.models.base import TimedBaseModel


class UploadedFileModel(TimedBaseModel):
    """Метаданные загруженного файла (S3)."""
    __tablename__ = 'uploaded_files'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    s3_key: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True)
    uploaded_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)

    @classmethod
    def from_entity(cls, entity: UploadedFile) -> 'UploadedFileModel':
        return cls(
            id=entity.id,
            original_filename=entity.original_filename,
            content_type=entity.content_type,
            size_bytes=entity.size_bytes,
            s3_key=entity.s3_key,
            uploaded_at=entity.uploaded_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def to_entity(self) -> UploadedFile:
        return UploadedFile(
            id=self.id,
            original_filename=self.original_filename,
            content_type=self.content_type,
            size_bytes=self.size_bytes,
            s3_key=self.s3_key,
            uploaded_at=self.uploaded_at,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
