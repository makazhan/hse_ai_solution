import datetime
import uuid
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from src.application.commands.base import BaseCommand, CommandHandler
from src.application.interfaces.repositories.files import BaseUploadedFileRepository
from src.application.interfaces.storage import BaseFileStorage
from src.application.mediator.base import Mediator
from src.domain.entities.files import UploadedFile


@dataclass(frozen=True)
class UploadFileCommand(BaseCommand):
    """Команда загрузки файла в S3."""
    file_content: bytes
    filename: str
    content_type: str


@dataclass(frozen=True)
class UploadFileCommandHandler(CommandHandler[UploadFileCommand, UploadedFile]):
    """Загружает файл в S3, создает запись в uploaded_files."""
    file_storage: BaseFileStorage
    file_repository: BaseUploadedFileRepository
    _mediator: Mediator = field(default=None, repr=False, compare=False)

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Извлекает только имя файла, ограничивает длину, убирает null-байты."""
        # Берём только имя (без пути)
        name = PurePosixPath(filename).name
        # Убираем null-байты и управляющие символы
        name = ''.join(ch for ch in name if ch.isprintable())
        # Ограничиваем длину
        return name[:255] if name else 'unknown'

    async def handle(self, command: UploadFileCommand) -> UploadedFile:
        now = datetime.datetime.utcnow()
        file_id = uuid.uuid4()
        safe_filename = self._sanitize_filename(command.filename)

        # S3-ключ: uploads/{YYYY}/{MM}/{DD}/{uuid}.{ext}
        ext = PurePosixPath(safe_filename).suffix or ''
        s3_key = f"uploads/{now:%Y/%m/%d}/{file_id}{ext}"

        await self.file_storage.upload(s3_key, command.file_content, command.content_type)

        entity = UploadedFile(
            id=file_id,
            original_filename=safe_filename,
            content_type=command.content_type,
            size_bytes=len(command.file_content),
            s3_key=s3_key,
            uploaded_at=now,
            created_at=now,
            updated_at=now,
        )

        return await self.file_repository.create(entity)
