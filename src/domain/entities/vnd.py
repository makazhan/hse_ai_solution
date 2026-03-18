"""Доменные сущности ВНД (внутренние нормативные документы)."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class VndChunkEntity:
    id: int
    doc_path: Optional[str] = None
    doc_title_without_transl: Optional[str] = None
    doc_title_with_transl: Optional[str] = None
    chunk_index: Optional[int] = None
    chunk_text: Optional[str] = None
    file_name_minio: Optional[str] = None
    metadata: Optional[str] = None
