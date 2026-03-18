from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from src.domain.entities.incidents import (
    Incident, EnquiryAct, EnquiryActChunk, Recommendation,
)
from src.application.filters.incidents import IncidentFilters
from src.application.filters.enquiry_acts import EnquiryActFilters
from src.application.filters.common import PaginationIn


@dataclass
class IncidentStatistics:
    """Статистика по инцидентам"""
    total_count: int
    by_classification: dict[str, int]
    by_injury_type: dict[str, int]
    total_victims: int
    total_fatalities: int


@dataclass
class BaseIncidentRepository(ABC):
    """Базовый репозиторий для работы с инцидентами"""

    @abstractmethod
    async def create(self, incident: Incident) -> Incident:
        """Создать инцидент"""
        ...

    @abstractmethod
    async def get_by_id(self, incident_id: UUID) -> Optional[Incident]:
        """Получить инцидент по ID"""
        ...

    @abstractmethod
    async def get_filtered(
        self,
        filters: IncidentFilters,
        pagination: PaginationIn
    ) -> list[Incident]:
        """Получить отфильтрованный список инцидентов"""
        ...

    @abstractmethod
    async def get_count(self, filters: IncidentFilters) -> int:
        """Получить количество инцидентов по фильтрам"""
        ...

    @abstractmethod
    async def get_aggregated_summary(
        self,
        filters: IncidentFilters,
    ) -> dict:
        """Получить полную аналитическую сводку"""
        ...

    @abstractmethod
    async def get_statistics(
        self,
        company_name: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> IncidentStatistics:
        """Получить статистику по инцидентам"""
        ...

    @abstractmethod
    async def get_regional_distribution(self) -> dict[str, int]:
        """Получить распределение инцидентов по регионам"""
        ...

    @abstractmethod
    async def bulk_create(self, incidents: list[Incident]) -> list[Incident]:
        """Массовое создание инцидентов"""
        ...

    @abstractmethod
    async def bulk_update(self, incidents: list[Incident]) -> list[Incident]:
        """Массовое обновление инцидентов"""
        ...

    @abstractmethod
    async def bulk_upsert(
        self,
        to_create: list[Incident],
        to_update: list[Incident],
    ) -> tuple[int, int]:
        """Атомарное создание и обновление инцидентов в одной транзакции.

        Args:
            to_create: новые инциденты для вставки.
            to_update: существующие инциденты для обновления (по id).

        Returns:
            Кортеж (created_count, updated_count).
        """
        ...

    @abstractmethod
    async def update(self, incident: Incident) -> Incident:
        """Обновить инцидент"""
        ...

    @abstractmethod
    async def get_candidates_for_matching(
        self, date_from: date, date_to: date,
    ) -> list[Incident]:
        """Получить инциденты-кандидаты для матчинга с актами.

        Загружает поля, необходимые для скоринга: id, incident_date,
        victim_name, company, region, dzo, injury_type.
        """
        ...

    @abstractmethod
    async def get_by_year_range(self, start_year: int, end_year: int) -> list[Incident]:
        """Получить инциденты за диапазон лет.

        NOTE: возвращает полные сущности; при больших диапазонах расход памяти растет.
        """
        ...


@dataclass
class BaseEnquiryActRepository(ABC):
    """Репозиторий актов расследования"""

    @abstractmethod
    async def create(self, act: EnquiryAct) -> EnquiryAct:
        """Создать акт расследования"""
        ...

    @abstractmethod
    async def get_by_id(self, act_id: UUID) -> Optional[EnquiryAct]:
        """Получить акт по ID"""
        ...

    @abstractmethod
    async def get_by_incident_id(self, incident_id: UUID) -> list[EnquiryAct]:
        """Получить акты по инциденту (включая related_incident_ids)"""
        ...

    @abstractmethod
    async def get_unlinked(self) -> list[EnquiryAct]:
        """Получить непривязанные акты (link_status = UNLINKED)"""
        ...

    @abstractmethod
    async def update(self, act: EnquiryAct) -> EnquiryAct:
        """Обновить акт расследования"""
        ...

    @abstractmethod
    async def bulk_update_link_status(
        self,
        updates: list[tuple[UUID, UUID, str]],
    ) -> int:
        """Атомарное обновление привязки актов к инцидентам.

        Args:
            updates: список (act_id, incident_id, link_status).

        Returns:
            Количество обновлённых актов.
        """
        ...

    @abstractmethod
    async def get_filtered(
        self,
        filters: EnquiryActFilters,
        pagination: PaginationIn,
    ) -> list[EnquiryAct]:
        """Получить отфильтрованный список актов"""
        ...

    @abstractmethod
    async def get_count(self, filters: EnquiryActFilters) -> int:
        """Получить количество актов по фильтрам"""
        ...

    @abstractmethod
    async def get_tag_patterns(
        self,
        tag_field: str,
        limit: int = 10,
        incident_ids: Optional[list[UUID]] = None,
    ) -> list[tuple[str, int]]:
        """Агрегация паттернов: топ-N значений тегов.

        Args:
            tag_field: имя колонки (cause_categories, violation_types, industry_tags).
            limit: максимальное количество результатов.
            incident_ids: если задан — фильтр только по актам привязанным к этим инцидентам.

        Returns:
            Список (тег, количество) отсортированный по убыванию.
        """
        ...

    @abstractmethod
    async def get_linked_act_summaries(
        self,
        incident_ids: list[UUID],
        limit: int = 30,
    ) -> list[dict]:
        """Краткие данные актов привязанных к инцидентам — для контекста отчёта.

        Args:
            incident_ids: список ID инцидентов.
            limit: максимальное количество актов.

        Returns:
            Список словарей с ключами: ai_summary, root_causes,
            immediate_causes, employer_fault_pct, corrective_measures,
            cause_categories, violation_types, conclusions.
        """
        ...



@dataclass
class BaseEnquiryActChunkRepository(ABC):
    """Репозиторий чанков актов для RAG-поиска.

    TODO: реализация SqlAlchemyEnquiryActChunkRepository и регистрация
    в containers.py будут добавлены при подключении RAG-поиска по актам.
    """

    @abstractmethod
    async def bulk_create(self, chunks: list[EnquiryActChunk]) -> list[EnquiryActChunk]:
        """Массовое создание чанков"""
        ...

    @abstractmethod
    async def get_by_act_id(self, act_id: UUID) -> list[EnquiryActChunk]:
        """Получить чанки по акту"""
        ...

    @abstractmethod
    async def search_similar(
        self,
        query_embedding: list[float],
        limit: int = 10,
        section_type: Optional[str] = None,
    ) -> list[tuple[EnquiryActChunk, float]]:
        """Семантический поиск по чанкам (косинусное расстояние)"""
        ...

    @abstractmethod
    async def delete_by_act_id(self, act_id: UUID) -> None:
        """Удалить все чанки акта"""
        ...


@dataclass
class BaseRecommendationRepository(ABC):
    """Репозиторий рекомендаций по ТБ"""

    @abstractmethod
    async def create(self, recommendation: Recommendation) -> Recommendation:
        """Создать рекомендацию"""
        ...

    @abstractmethod
    async def get_by_id(self, recommendation_id: UUID) -> Optional[Recommendation]:
        """Получить рекомендацию по ID"""
        ...

    @abstractmethod
    async def get_by_incident_id(self, incident_id: UUID) -> list[Recommendation]:
        """Получить рекомендации по инциденту"""
        ...

    @abstractmethod
    async def update(self, recommendation: Recommendation) -> Recommendation:
        """Обновить рекомендацию"""
        ...
