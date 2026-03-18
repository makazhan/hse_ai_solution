"""SQLAlchemy-модели НПА (плоская chunk-схема из agent-tb-api)."""
from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    ForeignKey,
    Integer,
    Text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from src.domain.entities.laws import LawChunkEntity, LawMetadataEntity
from src.infrastructure.db.sqlalchemy.models.base import BaseModel


class BaseLawsMetadataModel(BaseModel):
    __abstract__ = True

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    ngr: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(Text, nullable=True)
    versions_count: Mapped[str | None] = mapped_column(Text, nullable=True)
    act_types: Mapped[str | None] = mapped_column('actTypes', Text, nullable=True)
    status: Mapped[str | None] = mapped_column(Text, nullable=True)
    version_date: Mapped[str | None] = mapped_column(Text, nullable=True)
    state_agency_doc_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    requisites: Mapped[str | None] = mapped_column(Text, nullable=True)
    adilet_link: Mapped[str | None] = mapped_column(Text, nullable=True)

    def to_entity(self) -> LawMetadataEntity:
        return LawMetadataEntity(
            id=self.id,
            ngr=self.ngr,
            language=self.language,
            versions_count=self.versions_count,
            act_types=self.act_types,
            status=self.status,
            version_date=self.version_date,
            state_agency_doc_number=self.state_agency_doc_number,
            title=self.title,
            requisites=self.requisites,
            adilet_link=self.adilet_link,
        )


class BaseLawsModel(BaseModel):
    __abstract__ = True

    doc_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_metadata: Mapped[str | None] = mapped_column('metadata', Text, nullable=True)
    chunk: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding = mapped_column(Vector(1024), nullable=True)

    def to_entity(self) -> LawChunkEntity:
        return LawChunkEntity(
            row_id=self.row_id,
            doc_id=self.doc_id,
            chunk_metadata=self.chunk_metadata,
            chunk=self.chunk,
            metadata_rel=self.metadata_rel.to_entity() if self.metadata_rel else None,
        )


class AllLawsMetadataKzModel(BaseLawsMetadataModel):
    __tablename__ = 'all_laws_metadata_kz'

    chunks: Mapped[list['AllLawsKzModel']] = relationship(
        'AllLawsKzModel', back_populates='metadata_rel',
    )


class AllLawsMetadataRuModel(BaseLawsMetadataModel):
    __tablename__ = 'all_laws_metadata_ru'

    chunks: Mapped[list['AllLawsRuModel']] = relationship(
        'AllLawsRuModel', back_populates='metadata_rel',
    )


class AllLawsKzModel(BaseLawsModel):
    __tablename__ = 'all_laws_kz'

    row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey('all_laws_metadata_kz.id'), nullable=True,
    )

    metadata_rel: Mapped[AllLawsMetadataKzModel | None] = relationship(
        'AllLawsMetadataKzModel', back_populates='chunks',
    )


class AllLawsRuModel(BaseLawsModel):
    __tablename__ = 'all_laws_ru'

    row_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    doc_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey('all_laws_metadata_ru.id'), nullable=True,
    )

    metadata_rel: Mapped[AllLawsMetadataRuModel | None] = relationship(
        'AllLawsMetadataRuModel', back_populates='chunks',
    )


class NpaTargetModel(BaseModel):
    """Белый список doc_id для фильтрации поиска."""
    __tablename__ = 'safety_tb_npa'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_id: Mapped[str | None] = mapped_column(Text, nullable=True)
