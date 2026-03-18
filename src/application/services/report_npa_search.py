"""RAG-сервис поиска НПА для аналитического отчёта."""
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional

from src.application.dto.search_results import NPASearchResult
from src.application.interfaces.embeddings import BaseEmbeddingService
from src.application.interfaces.repositories.laws import BaseLawsRepository

logger = logging.getLogger(__name__)


def format_norms_for_llm(results: list[NPASearchResult]) -> list[dict]:
    """Форматирует результаты RAG для вставки в LLM-контекст."""
    return [
        {
            "document": r.title or "Без названия",
            "chunk_metadata": r.metadata,
            "text": r.chunk,
            "adilet_link": r.adilet_link,
            "act_types": r.act_types,
            "similarity": round(r.score, 3),
        }
        for r in results
    ]


@dataclass
class ReportNpaSearchService:
    """Сервис поиска НПА для аналитического отчёта.

    Использует vector search по тегам (violation_types, cause_categories)
    и BM25 по точным ссылкам на статьи (legal_violations).
    """
    embedding_service: BaseEmbeddingService
    laws_repository: BaseLawsRepository
    _target_doc_ids: Optional[list[str]] = field(default=None, repr=False)
    _target_table: str = "safety_tb_npa"

    async def _ensure_target_ids(self) -> list[str]:
        """Ленивая загрузка белого списка doc_id."""
        if self._target_doc_ids is None:
            self._target_doc_ids = await self.laws_repository.load_target_doc_ids(
                self._target_table,
            )
            logger.info(
                "Загружено %d target doc_ids из %s",
                len(self._target_doc_ids), self._target_table,
            )
        return self._target_doc_ids

    async def search_for_report(
        self,
        violation_types: list[str],
        cause_categories: list[str],
        legal_violations: list[str],
        language: str = "rus",
        vector_top_k: int = 5,
        bm25_top_k: int = 3,
        vector_threshold: float = 0.4,
        max_results: int = 20,
    ) -> list[NPASearchResult]:
        """RAG-поиск для аналитического отчёта.

        1. Batch embed тегов (violation_types + cause_categories)
        2. Параллельный vector search по каждому эмбеддингу
        3. Параллельный BM25 search по каждому legal_violation
        4. Дедупликация + fetch metadata
        """
        target_doc_ids = await self._ensure_target_ids()
        if not target_doc_ids:
            logger.warning("Белый список НПА пуст — поиск невозможен")
            return []

        # Дедупликация тегов
        search_tags = list(dict.fromkeys(
            tag.strip() for tag in (violation_types + cause_categories)
            if tag and tag.strip()
        ))

        # Шаг 1: batch embedding (1 вызов API)
        embeddings: list[list[float]] = []
        if search_tags:
            embeddings = await self.embedding_service.embed_batch(search_tags)

        # Шаг 2: параллельные поиски
        lang_code = "kaz" if language == "kaz" else "rus"

        vector_tasks = [
            self.laws_repository.search_vector(
                query_embedding=emb,
                language=lang_code,
                target_doc_ids=target_doc_ids,
                threshold=vector_threshold,
                limit=vector_top_k,
            )
            for emb in embeddings
        ]

        bm25_tasks = [
            self.laws_repository.search_bm25(
                query=ref,
                language=lang_code,
                target_doc_ids=target_doc_ids,
                limit=bm25_top_k,
            )
            for ref in legal_violations
            if ref and ref.strip()
        ]

        all_results = await asyncio.gather(
            *vector_tasks, *bm25_tasks,
            return_exceptions=True,
        )

        # Шаг 3: сбор результатов, BM25 приоритетнее
        seen_row_ids: set[int] = set()
        merged: list[NPASearchResult] = []

        # Сначала BM25 (точные ссылки на статьи важнее)
        bm25_start = len(vector_tasks)
        for result in all_results[bm25_start:]:
            if isinstance(result, Exception):
                logger.warning("BM25 search failed: %s", result)
                continue
            for entity, score in result:
                if entity.row_id not in seen_row_ids:
                    seen_row_ids.add(entity.row_id)
                    merged.append(NPASearchResult(
                        row_id=entity.row_id,
                        doc_id=entity.doc_id,
                        metadata=entity.chunk_metadata,
                        chunk=entity.chunk,
                        score=score,
                    ))

        # Затем vector
        for result in all_results[:bm25_start]:
            if isinstance(result, Exception):
                logger.warning("Vector search failed: %s", result)
                continue
            for entity, score in result:
                if entity.row_id not in seen_row_ids:
                    seen_row_ids.add(entity.row_id)
                    merged.append(NPASearchResult(
                        row_id=entity.row_id,
                        doc_id=entity.doc_id,
                        metadata=entity.chunk_metadata,
                        chunk=entity.chunk,
                        score=score,
                    ))

        # Шаг 4: fetch metadata
        doc_ids = list({r.doc_id for r in merged if r.doc_id})
        if doc_ids:
            metadata_map = await self.laws_repository.fetch_metadata(
                doc_ids=doc_ids,
                language=lang_code,
            )
            for result in merged:
                if result.doc_id and result.doc_id in metadata_map:
                    meta = metadata_map[result.doc_id]
                    result.title = meta.get("title")
                    result.adilet_link = meta.get("adilet_link")
                    result.act_types = meta.get("actTypes")

        logger.info(
            "RAG поиск НПА: %d тегов, %d legal_violations → %d результатов",
            len(search_tags), len(bm25_tasks), len(merged),
        )

        return merged[:max_results]
