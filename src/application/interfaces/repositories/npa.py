from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Optional
from uuid import UUID

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
from src.domain.enums.npa import LanguageCode


@dataclass
class BaseNpaTypeRepository(ABC):
    @abstractmethod
    async def get_by_id(self, npa_type_id: UUID) -> NpaTypeEntity | None:
        ...

    @abstractmethod
    async def get_by_code(self, code: str) -> NpaTypeEntity | None:
        ...

    @abstractmethod
    async def get_all(self) -> list[NpaTypeEntity]:
        ...

    @abstractmethod
    async def create(self, npa_type: NpaTypeEntity) -> NpaTypeEntity:
        ...


@dataclass
class BaseNpaRepository(ABC):
    @abstractmethod
    async def get_by_id(self, npa_id: UUID) -> NpaEntity | None:
        ...

    @abstractmethod
    async def get_by_type(self, npa_type_id: UUID) -> list[NpaEntity]:
        ...

    @abstractmethod
    async def get_effective_on_date(self, query_date: date) -> list[NpaEntity]:
        ...

    @abstractmethod
    async def create(self, npa: NpaEntity) -> NpaEntity:
        ...

    @abstractmethod
    async def update(self, npa: NpaEntity) -> NpaEntity:
        ...


@dataclass
class BaseNormTypeRepository(ABC):
    @abstractmethod
    async def get_by_id(self, norm_type_id: UUID) -> NormTypeEntity | None:
        ...

    @abstractmethod
    async def get_by_code(self, code: str) -> NormTypeEntity | None:
        ...

    @abstractmethod
    async def get_retrievable(self) -> list[NormTypeEntity]:
        ...

    @abstractmethod
    async def create(self, norm_type: NormTypeEntity) -> NormTypeEntity:
        ...


@dataclass
class BaseNormRepository(ABC):
    @abstractmethod
    async def get_by_id(self, norm_id: UUID) -> NormEntity | None:
        ...

    @abstractmethod
    async def get_by_npa_id(self, npa_id: UUID) -> list[NormEntity]:
        ...

    @abstractmethod
    async def get_children(self, parent_id: UUID) -> list[NormEntity]:
        ...

    @abstractmethod
    async def get_ancestors(self, norm_id: UUID) -> list[NormEntity]:
        ...

    @abstractmethod
    async def create(self, norm: NormEntity) -> NormEntity:
        ...

    @abstractmethod
    async def update(self, norm: NormEntity) -> NormEntity:
        ...


@dataclass
class BaseNormVersionRepository(ABC):
    @abstractmethod
    async def get_by_id(self, version_id: UUID) -> NormVersionEntity | None:
        ...

    @abstractmethod
    async def get_current_version(
        self, norm_id: UUID, language: LanguageCode
    ) -> NormVersionEntity | None:
        ...

    @abstractmethod
    async def get_version_at_date(
        self, norm_id: UUID, language: LanguageCode, query_date: date
    ) -> NormVersionEntity | None:
        ...

    @abstractmethod
    async def get_all_versions(self, norm_id: UUID) -> list[NormVersionEntity]:
        ...

    @abstractmethod
    async def create(self, version: NormVersionEntity) -> NormVersionEntity:
        ...

    @abstractmethod
    async def update(self, version: NormVersionEntity) -> NormVersionEntity:
        ...

    @abstractmethod
    async def close_version(self, version_id: UUID, effective_to: date) -> None:
        ...


@dataclass
class BaseNormEmbeddingRepository(ABC):
    @abstractmethod
    async def get_by_id(self, embedding_id: UUID) -> NormEmbeddingEntity | None:
        ...

    @abstractmethod
    async def get_by_version_id(self, version_id: UUID) -> list[NormEmbeddingEntity]:
        ...

    @abstractmethod
    async def search_similar(
        self,
        query_embedding: list[float],
        language: LanguageCode,
        limit: int = 10,
        effective_date: Optional[date] = None,
    ) -> list[tuple[NormEmbeddingEntity, float]]:
        ...

    @abstractmethod
    async def create(self, embedding: NormEmbeddingEntity) -> NormEmbeddingEntity:
        ...

    @abstractmethod
    async def delete_by_version_id(self, version_id: UUID) -> None:
        ...


@dataclass
class BaseAmendmentRepository(ABC):
    @abstractmethod
    async def get_by_id(self, amendment_id: UUID) -> AmendmentEntity | None:
        ...

    @abstractmethod
    async def get_by_amending_npa(self, npa_id: UUID) -> list[AmendmentEntity]:
        ...

    @abstractmethod
    async def get_by_amended_npa(self, npa_id: UUID) -> list[AmendmentEntity]:
        ...

    @abstractmethod
    async def create(self, amendment: AmendmentEntity) -> AmendmentEntity:
        ...


@dataclass
class BaseCrossReferenceRepository(ABC):
    @abstractmethod
    async def get_by_id(self, ref_id: UUID) -> CrossReferenceEntity | None:
        ...

    @abstractmethod
    async def get_outgoing(self, norm_id: UUID) -> list[CrossReferenceEntity]:
        ...

    @abstractmethod
    async def get_incoming(self, norm_id: UUID) -> list[CrossReferenceEntity]:
        ...

    @abstractmethod
    async def create(self, ref: CrossReferenceEntity) -> CrossReferenceEntity:
        ...
