"""DTO результатов поиска по НПА и ВНД."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class NPASearchResult:
    row_id: int
    doc_id: Optional[str] = None
    metadata: Optional[str] = None
    chunk: Optional[str] = None
    score: float = 0.0
    title: Optional[str] = None
    adilet_link: Optional[str] = None
    act_types: Optional[str] = None


@dataclass
class VNDSearchResult:
    id: int
    doc_path: Optional[str] = None
    doc_title_without_transl: Optional[str] = None
    doc_title_with_transl: Optional[str] = None
    chunk_index: Optional[int] = None
    chunk_text: Optional[str] = None
    file_name_minio: Optional[str] = None
    metadata: Optional[str] = None
    score: float = 0.0
