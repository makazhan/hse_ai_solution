from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class BaseEmbeddingService(ABC):

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        ...
