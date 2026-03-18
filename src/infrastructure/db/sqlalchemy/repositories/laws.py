"""Репозиторий НПА — raw SQL через text() (порт из agent-tb-api)."""
import logging
from dataclasses import dataclass

from sqlalchemy import text

from src.application.interfaces.repositories.laws import BaseLawsRepository
from src.domain.entities.laws import LawChunkEntity
from src.infrastructure.db.sqlalchemy.repositories.base import BaseSqlAlchemyRepository

logger = logging.getLogger(__name__)


_ALLOWED_TABLES = frozenset({
    'all_laws_ru', 'all_laws_kz',
    'all_laws_metadata_ru', 'all_laws_metadata_kz',
    'safety_tb_npa',
})

_ALLOWED_FTS_CONFIGS = frozenset({'simple', 'russian'})


def _validate_table(name: str) -> str:
    if name not in _ALLOWED_TABLES:
        raise ValueError(f"Invalid table name: {name}")
    return name


def _validate_fts_config(name: str) -> str:
    if name not in _ALLOWED_FTS_CONFIGS:
        raise ValueError(f"Invalid FTS config: {name}")
    return name


@dataclass
class SqlAlchemyLawsRepository(BaseLawsRepository, BaseSqlAlchemyRepository):
    def _get_table(self, language: str) -> str:
        return _validate_table('all_laws_kz' if language == 'kaz' else 'all_laws_ru')

    def _get_metadata_table(self, language: str) -> str:
        return _validate_table('all_laws_metadata_kz' if language == 'kaz' else 'all_laws_metadata_ru')

    @staticmethod
    def _to_pg_text_array(items: list[str]) -> str:
        if not items:
            return '{}'
        escaped = [str(item).replace('"', '\\"') for item in items]
        return '{' + ','.join(f'"{item}"' for item in escaped) + '}'

    @staticmethod
    def _build_or_tsquery(query: str) -> str:
        words = query.split()
        significant = [w for w in words if len(w) > 2]
        if not significant:
            significant = words[:3] or [query]
        return ' or '.join(significant)

    async def search_vector(
        self,
        query_embedding: list[float],
        language: str,
        target_doc_ids: list[str],
        threshold: float = 0.4,
        limit: int = 10,
    ) -> list[tuple[LawChunkEntity, float]]:
        table = self._get_table(language)
        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
        target_ids_array = self._to_pg_text_array(target_doc_ids)

        sql = text(f"""
            SELECT row_id, doc_id, metadata, chunk,
                   1 - (embedding <=> :embedding::vector) AS score
            FROM {table}
            WHERE doc_id = ANY(:target_ids::text[])
              AND 1 - (embedding <=> :embedding::vector) >= :threshold
            ORDER BY embedding <=> :embedding::vector
            LIMIT :limit
        """)
        async with self._async_sessionmaker() as session:
            result = await session.execute(sql, {
                "embedding": embedding_str,
                "target_ids": target_ids_array,
                "threshold": threshold,
                "limit": limit,
            })
            rows = result.mappings().all()
            return [(self._row_to_entity(row), float(row["score"])) for row in rows]

    async def search_bm25(
        self,
        query: str,
        language: str,
        target_doc_ids: list[str],
        limit: int = 10,
    ) -> list[tuple[LawChunkEntity, float]]:
        table = self._get_table(language)
        fts_config = _validate_fts_config('simple' if language == 'kaz' else 'russian')
        or_query = self._build_or_tsquery(query)
        target_ids_array = self._to_pg_text_array(target_doc_ids)

        sql = text(f"""
            SELECT row_id, doc_id, metadata, chunk,
                   ts_rank_cd(to_tsvector('{fts_config}', chunk),
                              websearch_to_tsquery('{fts_config}', :or_query)) AS score
            FROM {table}
            WHERE doc_id = ANY(:target_ids::text[])
              AND to_tsvector('{fts_config}', chunk)
                  @@ websearch_to_tsquery('{fts_config}', :or_query)
            ORDER BY score DESC
            LIMIT :limit
        """)
        async with self._async_sessionmaker() as session:
            result = await session.execute(sql, {
                "or_query": or_query,
                "target_ids": target_ids_array,
                "limit": limit,
            })
            rows = result.mappings().all()
            return [(self._row_to_entity(row), float(row["score"])) for row in rows]

    async def fetch_metadata(
        self,
        doc_ids: list[str],
        language: str,
    ) -> dict[str, dict]:
        if not doc_ids:
            return {}
        metadata_table = self._get_metadata_table(language)
        doc_ids_array = self._to_pg_text_array(doc_ids)

        sql = text(f"""
            SELECT id, title, adilet_link, "actTypes"
            FROM {metadata_table}
            WHERE id = ANY(:doc_ids::text[])
        """)
        async with self._async_sessionmaker() as session:
            result = await session.execute(sql, {"doc_ids": doc_ids_array})
            rows = result.mappings().all()
            return {
                row["id"]: {
                    "title": row.get("title", ""),
                    "adilet_link": row.get("adilet_link", ""),
                    "actTypes": row.get("actTypes", ""),
                }
                for row in rows
            }

    async def load_target_doc_ids(self, table_name: str) -> list[str]:
        _validate_table(table_name)
        sql = text(f"SELECT doc_id FROM {table_name} ORDER BY id")
        async with self._async_sessionmaker() as session:
            result = await session.execute(sql)
            rows = result.mappings().all()
            return [row["doc_id"] for row in rows if row.get("doc_id")]

    @staticmethod
    def _row_to_entity(row) -> LawChunkEntity:
        return LawChunkEntity(
            row_id=row["row_id"],
            doc_id=row.get("doc_id"),
            chunk_metadata=row.get("metadata"),
            chunk=row.get("chunk"),
        )
