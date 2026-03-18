from dataclasses import dataclass
from datetime import date
from typing import Optional, TypedDict

from src.application.interfaces.embeddings import BaseEmbeddingService
from src.application.interfaces.repositories.npa import (
    BaseNormEmbeddingRepository,
    BaseNormRepository,
    BaseNormVersionRepository,
    BaseNpaRepository,
)
from src.domain.enums.npa import LanguageCode


class NpaSearchResult(TypedDict):
    document_title: str
    article: Optional[str]
    paragraph: Optional[str]
    text: str
    effective_from: str
    effective_to: Optional[str]
    language: str
    chunk_index: int
    chunk_text: str
    similarity: float


@dataclass
class NpaSearchService:

    embedding_service: BaseEmbeddingService
    embedding_repository: BaseNormEmbeddingRepository
    norm_repository: BaseNormRepository
    version_repository: BaseNormVersionRepository
    npa_repository: BaseNpaRepository

    async def search(
        self,
        query: str,
        language: LanguageCode = LanguageCode.RU,
        effective_date: Optional[date] = None,
        top_k: int = 10,
    ) -> list[NpaSearchResult]:
        query_embedding = await self.embedding_service.embed_text(query)

        results = await self.embedding_repository.search_similar(
            query_embedding=query_embedding,
            language=language,
            limit=top_k,
            effective_date=effective_date,
        )

        search_results = []
        for embedding_entity, similarity in results:
            version = await self.version_repository.get_by_id(embedding_entity.norm_version.id)
            if not version:
                continue

            norm = await self.norm_repository.get_by_id(version.norm.id)
            if not norm:
                continue

            npa = await self.npa_repository.get_by_id(norm.npa.id)
            if not npa:
                continue

            article, paragraph = self._extract_hierarchy(norm)

            search_results.append(NpaSearchResult(
                document_title=npa.title_ru,
                article=article,
                paragraph=paragraph,
                text=version.content_plain,
                effective_from=version.effective_from.isoformat() if version.effective_from else None,
                effective_to=version.effective_to.isoformat() if version.effective_to else None,
                language=version.language,
                chunk_index=embedding_entity.chunk_index,
                chunk_text=embedding_entity.chunk_text,
                similarity=round(similarity, 4),
            ))

        return search_results

    def _extract_hierarchy(self, norm) -> tuple[Optional[str], Optional[str]]:
        article = None
        paragraph = None

        if hasattr(norm.norm_type, 'code'):
            code = norm.norm_type.code
            if code == 'article':
                article = norm.number
            elif code in ('paragraph', 'subparagraph'):
                paragraph = norm.number

        return article, paragraph
