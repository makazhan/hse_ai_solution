from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from src.domain.entities.files import UploadedFile


@dataclass
class BaseUploadedFileRepository(ABC):
    """Репозиторий метаданных загруженных файлов."""

    @abstractmethod
    async def create(self, entity: UploadedFile) -> UploadedFile:
        """Создать запись о загруженном файле."""
        ...

    @abstractmethod
    async def get_by_id(self, file_id: UUID) -> Optional[UploadedFile]:
        """Получить метаданные файла по ID."""
        ...
