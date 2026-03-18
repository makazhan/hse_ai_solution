import uuid
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Date,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UUID,
    Boolean,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from src.domain.entities.npa import (
    NpaTypeEntity,
    NpaEntity,
    NormTypeEntity,
    NormEntity,
    NormVersionEntity,
    NormEmbeddingEntity,
    AmendmentEntity,
    CrossReferenceEntity,
)
from src.infrastructure.db.sqlalchemy.models.base import TimedBaseModel


class NpaTypeModel(TimedBaseModel):
    __tablename__ = 'npa_types'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name_ru: Mapped[str] = mapped_column(String(255), nullable=False)
    name_kz: Mapped[str] = mapped_column(String(255), nullable=False)
    hierarchy_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('npa_types.id'), nullable=True
    )

    parent: Mapped[Optional['NpaTypeModel']] = relationship(
        'NpaTypeModel', remote_side='NpaTypeModel.id', back_populates='children'
    )
    children: Mapped[list['NpaTypeModel']] = relationship('NpaTypeModel', back_populates='parent')
    npas: Mapped[list['NpaModel']] = relationship('NpaModel', back_populates='npa_type')

    @classmethod
    def from_entity(cls, entity: NpaTypeEntity) -> 'NpaTypeModel':
        return cls(
            id=entity.id,
            code=entity.code,
            name_ru=entity.name_ru,
            name_kz=entity.name_kz,
            hierarchy_level=entity.hierarchy_level,
            parent_id=entity.parent.id if hasattr(entity.parent, 'id') else None,
        )

    def to_entity(self) -> NpaTypeEntity:
        return NpaTypeEntity(
            id=self.id,
            code=self.code,
            name_ru=self.name_ru,
            name_kz=self.name_kz,
            hierarchy_level=self.hierarchy_level,
        )


class NpaModel(TimedBaseModel):
    __tablename__ = 'npas'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    npa_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('npa_types.id'), nullable=False
    )
    registration_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    registration_date: Mapped[Date] = mapped_column(Date, nullable=False)
    title_ru: Mapped[str] = mapped_column(Text, nullable=False)
    title_kz: Mapped[str] = mapped_column(Text, nullable=False)
    issuing_authority: Mapped[str] = mapped_column(String(255), nullable=False)
    adopted_date: Mapped[Date] = mapped_column(Date, nullable=False)
    effective_from: Mapped[Date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default='active', nullable=False
    )
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    official_publication: Mapped[str | None] = mapped_column(Text, nullable=True)

    npa_type: Mapped['NpaTypeModel'] = relationship('NpaTypeModel', back_populates='npas')
    norms: Mapped[list['NormModel']] = relationship('NormModel', back_populates='npa', cascade='all, delete-orphan')

    __table_args__ = (
        Index('idx_npas_type', 'npa_type_id'),
        Index('idx_npas_effective', 'effective_from', 'effective_to'),
        Index('idx_npas_status', 'status'),
    )

    @classmethod
    def from_entity(cls, entity: NpaEntity) -> 'NpaModel':
        return cls(
            id=entity.id,
            npa_type_id=entity.npa_type.id if hasattr(entity.npa_type, 'id') else None,
            registration_number=entity.registration_number,
            registration_date=entity.registration_date,
            title_ru=entity.title_ru,
            title_kz=entity.title_kz,
            issuing_authority=entity.issuing_authority,
            adopted_date=entity.adopted_date,
            effective_from=entity.effective_from,
            effective_to=entity.effective_to,
            status=entity.status,
            source_url=entity.source_url,
            official_publication=entity.official_publication,
        )

    def to_entity(self) -> NpaEntity:
        return NpaEntity(
            id=self.id,
            npa_type=self.npa_type.to_entity() if self.npa_type else None,
            registration_number=self.registration_number,
            registration_date=self.registration_date,
            title_ru=self.title_ru,
            title_kz=self.title_kz,
            issuing_authority=self.issuing_authority,
            adopted_date=self.adopted_date,
            effective_from=self.effective_from,
            effective_to=self.effective_to,
            status=self.status,
            source_url=self.source_url,
            official_publication=self.official_publication,
        )


class NormTypeModel(TimedBaseModel):
    __tablename__ = 'norm_types'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name_ru: Mapped[str] = mapped_column(String(100), nullable=False)
    name_kz: Mapped[str] = mapped_column(String(100), nullable=False)
    depth_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_retrievable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    norms: Mapped[list['NormModel']] = relationship('NormModel', back_populates='norm_type')

    @classmethod
    def from_entity(cls, entity: NormTypeEntity) -> 'NormTypeModel':
        return cls(
            id=entity.id,
            code=entity.code,
            name_ru=entity.name_ru,
            name_kz=entity.name_kz,
            depth_level=entity.depth_level,
            is_retrievable=entity.is_retrievable,
        )

    def to_entity(self) -> NormTypeEntity:
        return NormTypeEntity(
            id=self.id,
            code=self.code,
            name_ru=self.name_ru,
            name_kz=self.name_kz,
            depth_level=self.depth_level,
            is_retrievable=self.is_retrievable,
        )


class NormModel(TimedBaseModel):
    __tablename__ = 'norms'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    npa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('npas.id', ondelete='CASCADE'), nullable=False
    )
    norm_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('norm_types.id'), nullable=False
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('norms.id', ondelete='CASCADE'), nullable=True
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    depth: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    number: Mapped[str | None] = mapped_column(String(50), nullable=True)

    npa: Mapped['NpaModel'] = relationship('NpaModel', back_populates='norms')
    norm_type: Mapped['NormTypeModel'] = relationship('NormTypeModel', back_populates='norms')
    parent: Mapped[Optional['NormModel']] = relationship(
        'NormModel', remote_side='NormModel.id', back_populates='children'
    )
    children: Mapped[list['NormModel']] = relationship('NormModel', back_populates='parent')
    versions: Mapped[list['NormVersionModel']] = relationship(
        'NormVersionModel', back_populates='norm', cascade='all, delete-orphan'
    )

    __table_args__ = (
        Index('idx_norms_npa', 'npa_id'),
        Index('idx_norms_parent', 'parent_id'),
        Index('idx_norms_type', 'norm_type_id'),
        Index('idx_norms_path', 'path'),
    )

    @classmethod
    def from_entity(cls, entity: NormEntity) -> 'NormModel':
        return cls(
            id=entity.id,
            npa_id=entity.npa.id if hasattr(entity.npa, 'id') else None,
            norm_type_id=entity.norm_type.id if hasattr(entity.norm_type, 'id') else None,
            parent_id=entity.parent.id if hasattr(entity.parent, 'id') else None,
            order_index=entity.order_index,
            path=entity.path,
            depth=entity.depth,
            number=entity.number,
        )

    def to_entity(self) -> NormEntity:
        return NormEntity(
            id=self.id,
            npa=self.npa.to_entity() if self.npa else None,
            norm_type=self.norm_type.to_entity() if self.norm_type else None,
            order_index=self.order_index,
            path=self.path,
            depth=self.depth,
            number=self.number,
        )


class NormVersionModel(TimedBaseModel):
    __tablename__ = 'norm_versions'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    norm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('norms.id', ondelete='CASCADE'), nullable=False
    )
    language: Mapped[str] = mapped_column(
        String(10), nullable=False
    )
    effective_from: Mapped[Date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Date | None] = mapped_column(Date, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_plain: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default='active', nullable=False
    )
    created_by_npa_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('npas.id'), nullable=True
    )
    amendment_action: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )

    norm: Mapped['NormModel'] = relationship('NormModel', back_populates='versions')
    created_by_npa: Mapped[Optional['NpaModel']] = relationship('NpaModel')
    embeddings: Mapped[list['NormEmbeddingModel']] = relationship(
        'NormEmbeddingModel', back_populates='norm_version', cascade='all, delete-orphan'
    )

    __table_args__ = (
        Index('idx_norm_versions_norm', 'norm_id'),
        Index('idx_norm_versions_effective', 'effective_from', 'effective_to'),
        Index('idx_norm_versions_status', 'status'),
    )

    @classmethod
    def from_entity(cls, entity: NormVersionEntity) -> 'NormVersionModel':
        return cls(
            id=entity.id,
            norm_id=entity.norm.id if hasattr(entity.norm, 'id') else None,
            language=entity.language,
            effective_from=entity.effective_from,
            effective_to=entity.effective_to,
            title=entity.title,
            content=entity.content,
            content_plain=entity.content_plain,
            status=entity.status,
            created_by_npa_id=entity.created_by_npa.id if hasattr(entity.created_by_npa, 'id') else None,
            amendment_action=entity.amendment_action,
        )

    def to_entity(self) -> NormVersionEntity:
        return NormVersionEntity(
            id=self.id,
            norm=self.norm.to_entity() if self.norm else None,
            language=self.language,
            effective_from=self.effective_from,
            effective_to=self.effective_to,
            title=self.title,
            content=self.content,
            content_plain=self.content_plain,
            status=self.status,
            amendment_action=self.amendment_action,
        )


class NormEmbeddingModel(TimedBaseModel):
    __tablename__ = 'norm_embeddings'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    norm_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('norm_versions.id', ondelete='CASCADE'), nullable=False
    )
    embedding = mapped_column(Vector(1024), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    chunk_index: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)

    norm_version: Mapped['NormVersionModel'] = relationship('NormVersionModel', back_populates='embeddings')

    __table_args__ = (
        Index('idx_norm_embeddings_version', 'norm_version_id'),
    )

    @classmethod
    def from_entity(cls, entity: NormEmbeddingEntity) -> 'NormEmbeddingModel':
        return cls(
            id=entity.id,
            norm_version_id=entity.norm_version.id if hasattr(entity.norm_version, 'id') else None,
            embedding=entity.embedding,
            model_name=entity.model_name,
            chunk_index=entity.chunk_index,
            chunk_text=entity.chunk_text,
        )

    def to_entity(self) -> NormEmbeddingEntity:
        return NormEmbeddingEntity(
            id=self.id,
            norm_version=self.norm_version.to_entity() if self.norm_version else None,
            embedding=list(self.embedding) if self.embedding is not None else [],
            model_name=self.model_name,
            chunk_index=self.chunk_index,
            chunk_text=self.chunk_text,
        )


class AmendmentModel(TimedBaseModel):
    __tablename__ = 'amendments'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    amending_npa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('npas.id'), nullable=False
    )
    amended_npa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('npas.id'), nullable=False
    )
    amended_norm_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('norms.id'), nullable=True
    )
    action: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    effective_date: Mapped[Date] = mapped_column(Date, nullable=False)
    description_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_kz: Mapped[str | None] = mapped_column(Text, nullable=True)

    amending_npa: Mapped['NpaModel'] = relationship('NpaModel', foreign_keys=[amending_npa_id])
    amended_npa: Mapped['NpaModel'] = relationship('NpaModel', foreign_keys=[amended_npa_id])
    amended_norm: Mapped[Optional['NormModel']] = relationship('NormModel')

    __table_args__ = (
        Index('idx_amendments_amending', 'amending_npa_id'),
        Index('idx_amendments_amended', 'amended_npa_id'),
    )

    @classmethod
    def from_entity(cls, entity: AmendmentEntity) -> 'AmendmentModel':
        return cls(
            id=entity.id,
            amending_npa_id=entity.amending_npa.id if hasattr(entity.amending_npa, 'id') else None,
            amended_npa_id=entity.amended_npa.id if hasattr(entity.amended_npa, 'id') else None,
            amended_norm_id=entity.amended_norm.id if hasattr(entity.amended_norm, 'id') else None,
            action=entity.action,
            effective_date=entity.effective_date,
            description_ru=entity.description_ru,
            description_kz=entity.description_kz,
        )

    def to_entity(self) -> AmendmentEntity:
        return AmendmentEntity(
            id=self.id,
            amending_npa=self.amending_npa.to_entity() if self.amending_npa else None,
            amended_npa=self.amended_npa.to_entity() if self.amended_npa else None,
            action=self.action,
            effective_date=self.effective_date,
            description_ru=self.description_ru,
            description_kz=self.description_kz,
        )


class CrossReferenceModel(TimedBaseModel):
    __tablename__ = 'cross_references'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_norm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('norms.id', ondelete='CASCADE'), nullable=False
    )
    target_norm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('norms.id', ondelete='CASCADE'), nullable=False
    )
    reference_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    source_norm: Mapped['NormModel'] = relationship('NormModel', foreign_keys=[source_norm_id])
    target_norm: Mapped['NormModel'] = relationship('NormModel', foreign_keys=[target_norm_id])

    __table_args__ = (
        Index('idx_cross_refs_source', 'source_norm_id'),
        Index('idx_cross_refs_target', 'target_norm_id'),
    )

    @classmethod
    def from_entity(cls, entity: CrossReferenceEntity) -> 'CrossReferenceModel':
        return cls(
            id=entity.id,
            source_norm_id=entity.source_norm.id if hasattr(entity.source_norm, 'id') else None,
            target_norm_id=entity.target_norm.id if hasattr(entity.target_norm, 'id') else None,
            reference_type=entity.reference_type,
            reference_text=entity.reference_text,
        )

    def to_entity(self) -> CrossReferenceEntity:
        return CrossReferenceEntity(
            id=self.id,
            source_norm=self.source_norm.to_entity() if self.source_norm else None,
            target_norm=self.target_norm.to_entity() if self.target_norm else None,
            reference_type=self.reference_type,
            reference_text=self.reference_text,
        )
