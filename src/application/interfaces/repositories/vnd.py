"""Интерфейс репозитория ВНД."""
from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.domain.entities.vnd import VndChunkEntity


@dataclass
class BaseVndRepository(ABC):
    @abstractmethod
    async def search_vector(
        self,
        query_embedding: list[float],
        limit: int = 10,
    ) -> list[tuple[VndChunkEntity, float]]:
        ...

    @abstractmethod
    async def search_bm25(
        self,
        query: str,
        language: str,
        limit: int = 10,
    ) -> list[tuple[VndChunkEntity, float]]:
        ...
