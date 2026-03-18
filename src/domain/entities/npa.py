from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from src.domain.entities.base import BaseEntity
from src.domain.enums.base import EntityStatus
from src.domain.enums.npa import LanguageCode, NormStatus, AmendmentAction


@dataclass
class NpaTypeEntity(BaseEntity):
    code: str
    name_ru: str
    name_kz: str
    hierarchy_level: int
    parent: Optional['NpaTypeEntity'] | EntityStatus = field(default=EntityStatus.NOT_LOADED)

    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class NpaEntity(BaseEntity):
    npa_type: NpaTypeEntity | EntityStatus
    registration_number: Optional[str]
    registration_date: date
    title_ru: str
    title_kz: str
    issuing_authority: str
    adopted_date: date
    effective_from: date
    effective_to: Optional[date] = None
    status: NormStatus = NormStatus.ACTIVE
    source_url: Optional[str] = None
    official_publication: Optional[str] = None

    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class NormTypeEntity(BaseEntity):
    code: str
    name_ru: str
    name_kz: str
    depth_level: int
    is_retrievable: bool = False


@dataclass
class NormEntity(BaseEntity):
    npa: NpaEntity | EntityStatus
    norm_type: NormTypeEntity | EntityStatus
    parent: Optional['NormEntity'] | EntityStatus = field(default=EntityStatus.NOT_LOADED)
    order_index: int = 0
    path: Optional[str] = None
    depth: int = 0
    number: Optional[str] = None

    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class NormVersionEntity(BaseEntity):
    norm: NormEntity | EntityStatus
    language: LanguageCode
    effective_from: date
    effective_to: Optional[date] = None
    title: Optional[str] = None
    content: str = ""
    content_plain: str = ""
    status: NormStatus = NormStatus.ACTIVE
    created_by_npa: Optional[NpaEntity] | EntityStatus = field(default=EntityStatus.NOT_LOADED)
    amendment_action: Optional[AmendmentAction] = None

    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class NormEmbeddingEntity(BaseEntity):
    norm_version: NormVersionEntity | EntityStatus
    embedding: list[float] = field(default_factory=list)
    model_name: str = ""
    chunk_index: int = 0
    chunk_text: str = ""

    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class AmendmentEntity(BaseEntity):
    amending_npa: NpaEntity | EntityStatus
    amended_npa: NpaEntity | EntityStatus
    amended_norm: Optional[NormEntity] | EntityStatus = field(default=EntityStatus.NOT_LOADED)
    action: AmendmentAction = AmendmentAction.MODIFIED
    effective_date: date = field(default_factory=date.today)
    description_ru: Optional[str] = None
    description_kz: Optional[str] = None

    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class CrossReferenceEntity(BaseEntity):
    source_norm: NormEntity | EntityStatus
    target_norm: NormEntity | EntityStatus
    reference_type: str = "explicit"
    reference_text: Optional[str] = None

    created_at: datetime = field(default_factory=datetime.now)
