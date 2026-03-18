from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from sqlalchemy import select

from src.application.interfaces.repositories.files import BaseUploadedFileRepository
from src.domain.entities.files import UploadedFile
from src.infrastructure.db.sqlalchemy.models.files import UploadedFileModel
from src.infrastructure.db.sqlalchemy.repositories.base import BaseSqlAlchemyRepository


@dataclass
class SqlAlchemyUploadedFileRepository(BaseUploadedFileRepository, BaseSqlAlchemyRepository):
    """Репозиторий метаданных загруженных файлов (SQLAlchemy)."""

    async def create(self, entity: UploadedFile) -> UploadedFile:
        async with self._async_sessionmaker() as session:
            model = UploadedFileModel.from_entity(entity)
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return model.to_entity()

    async def get_by_id(self, file_id: UUID) -> Optional[UploadedFile]:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(UploadedFileModel).where(UploadedFileModel.id == file_id)
            )
            model = result.scalar_one_or_none()
            return model.to_entity() if model else None
