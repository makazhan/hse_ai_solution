"""Embedding-сервис через OpenAI-совместимый API (LiteLLM)."""
from dataclasses import dataclass

from openai import AsyncOpenAI

from src.application.interfaces.embeddings import BaseEmbeddingService


@dataclass
class BgeEmbeddingService(BaseEmbeddingService):
    client: AsyncOpenAI
    model: str

    async def embed_text(self, text: str) -> list[float]:
        response = await self.client.embeddings.create(
            model=self.model,
            input=[text],
        )
        return response.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Эмбеддинги для списка текстов одним вызовом API."""
        if not texts:
            return []
        response = await self.client.embeddings.create(
            model=self.model,
            input=texts,
        )
        return [item.embedding for item in response.data]
