"""Доменные сущности НПА (плоская chunk-модель из agent-tb-api)."""
from dataclasses import dataclass


@dataclass
class LawMetadataEntity:
    id: str
    ngr: str | None = None
    language: str | None = None
    versions_count: str | None = None
    act_types: str | None = None
    status: str | None = None
    version_date: str | None = None
    state_agency_doc_number: str | None = None
    title: str | None = None
    requisites: str | None = None
    adilet_link: str | None = None


@dataclass
class LawChunkEntity:
    row_id: int
    doc_id: str | None = None
    chunk_metadata: str | None = None
    chunk: str | None = None
    metadata_rel: LawMetadataEntity | None = None
