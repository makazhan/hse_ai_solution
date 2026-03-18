"""SQLAlchemy-модель ВНД (внутренние нормативные документы)."""
from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Integer,
    SmallInteger,
    Text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from src.domain.entities.vnd import VndChunkEntity
from src.infrastructure.db.sqlalchemy.models.base import BaseModel


class VndMainChunksModel(BaseModel):
    __tablename__ = 'safety_tb_vnd'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    doc_title_without_transl: Mapped[str | None] = mapped_column(Text, nullable=True)
    doc_title_with_transl: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_index = mapped_column(SmallInteger, nullable=True)
    chunk_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_name_minio: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_metadata: Mapped[str | None] = mapped_column('metadata', Text, nullable=True)
    dense_embedding = mapped_column(Vector(1024), nullable=True)

    def to_entity(self) -> VndChunkEntity:
        return VndChunkEntity(
            id=self.id,
            doc_path=self.doc_path,
            doc_title_without_transl=self.doc_title_without_transl,
            doc_title_with_transl=self.doc_title_with_transl,
            chunk_index=self.chunk_index,
            chunk_text=self.chunk_text,
            file_name_minio=self.file_name_minio,
            metadata=self.chunk_metadata,
        )
