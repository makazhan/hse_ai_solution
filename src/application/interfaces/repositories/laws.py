"""Интерфейс репозитория НПА (laws)."""
from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.domain.entities.laws import LawChunkEntity


@dataclass
class BaseLawsRepository(ABC):
    @abstractmethod
    async def search_vector(
        self,
        query_embedding: list[float],
        language: str,
        target_doc_ids: list[str],
        threshold: float = 0.4,
        limit: int = 10,
    ) -> list[tuple[LawChunkEntity, float]]:
        ...

    @abstractmethod
    async def search_bm25(
        self,
        query: str,
        language: str,
        target_doc_ids: list[str],
        limit: int = 10,
    ) -> list[tuple[LawChunkEntity, float]]:
        ...

    @abstractmethod
    async def fetch_metadata(
        self,
        doc_ids: list[str],
        language: str,
    ) -> dict[str, dict]:
        ...

    @abstractmethod
    async def load_target_doc_ids(
        self,
        table_name: str,
    ) -> list[str]:
        ...
