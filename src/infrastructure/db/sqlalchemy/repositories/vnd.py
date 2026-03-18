"""Репозиторий ВНД — raw SQL через text() (порт из agent-tb-api)."""
from dataclasses import dataclass

from sqlalchemy import text

from src.application.interfaces.repositories.vnd import BaseVndRepository
from src.domain.entities.vnd import VndChunkEntity
from src.infrastructure.db.sqlalchemy.repositories.base import BaseSqlAlchemyRepository

_ALLOWED_VND_TABLES = frozenset({'safety_tb_vnd'})
_ALLOWED_FTS_CONFIGS = frozenset({'simple', 'russian'})


def _validate_vnd_table(name: str) -> str:
    if name not in _ALLOWED_VND_TABLES:
        raise ValueError(f"Invalid VND table name: {name}")
    return name


def _validate_fts_config(name: str) -> str:
    if name not in _ALLOWED_FTS_CONFIGS:
        raise ValueError(f"Invalid FTS config: {name}")
    return name


@dataclass
class SqlAlchemyVndRepository(BaseVndRepository, BaseSqlAlchemyRepository):
    table_name: str = 'safety_tb_vnd'

    async def search_vector(
        self,
        query_embedding: list[float],
        limit: int = 10,
    ) -> list[tuple[VndChunkEntity, float]]:
        table = _validate_vnd_table(self.table_name)
        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
        sql = text(f"""
            SELECT id, doc_path, doc_title_without_transl, doc_title_with_transl,
                   chunk_index, chunk_text, file_name_minio, metadata,
                   1 - (dense_embedding <=> :embedding::vector) as score
            FROM {table}
            WHERE dense_embedding IS NOT NULL
            ORDER BY dense_embedding <=> :embedding::vector
            LIMIT :limit
        """)
        async with self._async_sessionmaker() as session:
            result = await session.execute(sql, {"embedding": embedding_str, "limit": limit})
            rows = result.mappings().all()
            return [(self._row_to_entity(row), float(row["score"])) for row in rows]

    async def search_bm25(
        self,
        query: str,
        language: str,
        limit: int = 10,
    ) -> list[tuple[VndChunkEntity, float]]:
        table = _validate_vnd_table(self.table_name)
        fts_config = _validate_fts_config('simple' if language == 'kaz' else 'russian')
        sql = text(f"""
            SELECT id, doc_path, doc_title_without_transl, doc_title_with_transl,
                   chunk_index, chunk_text, file_name_minio, metadata,
                   ts_rank_cd(to_tsvector('{fts_config}', chunk_text),
                              plainto_tsquery('{fts_config}', :query)) as score
            FROM {table}
            WHERE to_tsvector('{fts_config}', chunk_text)
                  @@ plainto_tsquery('{fts_config}', :query)
            ORDER BY score DESC
            LIMIT :limit
        """)
        async with self._async_sessionmaker() as session:
            result = await session.execute(sql, {"query": query, "limit": limit})
            rows = result.mappings().all()
            return [(self._row_to_entity(row), float(row["score"])) for row in rows]

    @staticmethod
    def _row_to_entity(row) -> VndChunkEntity:
        return VndChunkEntity(
            id=row["id"],
            doc_path=row.get("doc_path"),
            doc_title_without_transl=row.get("doc_title_without_transl"),
            doc_title_with_transl=row.get("doc_title_with_transl"),
            chunk_index=row.get("chunk_index"),
            chunk_text=row.get("chunk_text"),
            file_name_minio=row.get("file_name_minio"),
            metadata=row.get("metadata"),
        )
