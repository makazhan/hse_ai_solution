from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlalchemy import select, and_, or_, func, extract, case, text, literal_column
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import load_only

from src.application.exceptions.incidents import (
    IncidentNotFoundException,
    RecommendationNotFoundException,
    EnquiryActNotFoundException,
)
from src.application.filters.incidents import IncidentFilters
from src.application.filters.enquiry_acts import EnquiryActFilters
from src.application.filters.common import PaginationIn
from src.application.interfaces.repositories.incidents import (
    BaseIncidentRepository,
    BaseEnquiryActRepository,
    BaseRecommendationRepository,
    IncidentStatistics,
)
from src.domain.entities.incidents import Incident, EnquiryAct, Recommendation
from src.domain.enums.incidents import InjuryType, EnquiryActLinkStatus
from src.infrastructure.db.sqlalchemy.models.incidents import (
    IncidentModel,
    EnquiryActModel,
    RecommendationModel,
)
from src.infrastructure.db.sqlalchemy.repositories.base import BaseSqlAlchemyRepository


def _serialize_value(v):
    """Enum → .value для безопасного setattr на моделях SQLAlchemy."""
    if isinstance(v, Enum):
        return v.value
    return v


def _escape_like(value: str) -> str:
    """Экранирование спецсимволов LIKE/ILIKE (%, _, \\)."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@dataclass
class SqlAlchemyIncidentRepository(BaseIncidentRepository, BaseSqlAlchemyRepository):
    """Репозиторий инцидентов (SQLAlchemy)"""

    async def create(self, incident: Incident) -> Incident:
        async with self._async_sessionmaker() as session:
            model = IncidentModel.from_entity(incident)
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return model.to_entity()

    async def get_by_id(self, incident_id: UUID) -> Optional[Incident]:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(IncidentModel).where(IncidentModel.id == incident_id)
            )
            model = result.scalar_one_or_none()
            return model.to_entity() if model else None

    def _build_filter_conditions(self, filters: IncidentFilters) -> list:
        """Построение условий фильтрации из IncidentFilters."""
        conditions = []

        # Диапазон дат
        if filters.date_from:
            conditions.append(IncidentModel.incident_date >= filters.date_from)
        if filters.date_to:
            conditions.append(IncidentModel.incident_date <= filters.date_to)

        # Точное совпадение перечислений (значения уже строки после схемы)
        if filters.region:
            conditions.append(IncidentModel.region == filters.region)
        if filters.company:
            conditions.append(IncidentModel.company == filters.company)
        if filters.companies:
            conditions.append(IncidentModel.company.in_(filters.companies))
        if filters.regions:
            conditions.append(IncidentModel.region.in_(filters.regions))
        if filters.classification:
            conditions.append(IncidentModel.classification == filters.classification)
        if filters.injury_type:
            conditions.append(IncidentModel.injury_type == filters.injury_type)
        if filters.investigation_status:
            conditions.append(IncidentModel.investigation_status == filters.investigation_status)
        if filters.investigation_results:
            conditions.append(IncidentModel.investigation_results == filters.investigation_results)
        if filters.work_experience:
            conditions.append(IncidentModel.victim_work_experience == filters.work_experience)

        # Текстовый поиск (ILIKE) — спецсимволы экранируются
        if filters.victim_name:
            conditions.append(IncidentModel.victim_name.ilike(f"%{_escape_like(filters.victim_name)}%"))
        if filters.victim_position:
            conditions.append(IncidentModel.victim_position.ilike(f"%{_escape_like(filters.victim_position)}%"))
        if filters.dzo:
            conditions.append(IncidentModel.dzo.ilike(f"%{_escape_like(filters.dzo)}%"))
        if filters.location:
            conditions.append(IncidentModel.location.ilike(f"%{_escape_like(filters.location)}%"))
        if filters.description:
            conditions.append(IncidentModel.description.ilike(f"%{_escape_like(filters.description)}%"))

        # Время суток
        if filters.time_from:
            conditions.append(IncidentModel.incident_time >= filters.time_from)
        if filters.time_to:
            conditions.append(IncidentModel.incident_time <= filters.time_to)

        # Поиск по причинам (два поля)
        if filters.cause_search:
            escaped = _escape_like(filters.cause_search)
            conditions.append(
                or_(
                    IncidentModel.preliminary_causes.ilike(f"%{escaped}%"),
                    IncidentModel.main_causes_from_report.ilike(f"%{escaped}%"),
                )
            )

        # --- Фаза A: ILIKE текстовый поиск ---
        if filters.work_type:
            conditions.append(IncidentModel.work_type.ilike(f"%{_escape_like(filters.work_type)}%"))
        if filters.equipment:
            conditions.append(IncidentModel.equipment.ilike(f"%{_escape_like(filters.equipment)}%"))
        if filters.safety_responsible_person:
            conditions.append(IncidentModel.safety_responsible_person.ilike(f"%{_escape_like(filters.safety_responsible_person)}%"))
        if filters.weather_conditions:
            conditions.append(IncidentModel.weather_conditions.ilike(f"%{_escape_like(filters.weather_conditions)}%"))

        # --- Фаза B: диапазоны ---
        if filters.victim_count_min is not None:
            conditions.append(IncidentModel.victim_count >= filters.victim_count_min)
        if filters.victim_count_max is not None:
            conditions.append(IncidentModel.victim_count <= filters.victim_count_max)
        if filters.fatality_count_min is not None:
            conditions.append(IncidentModel.fatality_count >= filters.fatality_count_min)
        if filters.fatality_count_max is not None:
            conditions.append(IncidentModel.fatality_count <= filters.fatality_count_max)

        # --- Фаза C: булевые ---
        if filters.safety_training_completed is not None:
            conditions.append(IncidentModel.safety_training_completed == filters.safety_training_completed)
        if filters.is_recurrent is not None:
            conditions.append(IncidentModel.is_recurrent == filters.is_recurrent)
        if filters.regulatory_compliant is not None:
            conditions.append(IncidentModel.regulatory_compliant == filters.regulatory_compliant)

        # --- Фаза B: субзапрос по статусу рекомендаций ---
        if filters.recommendation_status:
            if filters.recommendation_status == "Нет рекомендаций":
                subq = select(RecommendationModel.incident_id).where(
                    RecommendationModel.incident_id == IncidentModel.id
                ).correlate(IncidentModel).exists()
                conditions.append(~subq)
            else:
                subq = select(RecommendationModel.incident_id).where(
                    and_(
                        RecommendationModel.incident_id == IncidentModel.id,
                        RecommendationModel.status == filters.recommendation_status,
                    )
                ).correlate(IncidentModel).exists()
                conditions.append(subq)

        return conditions

    async def get_filtered(
        self,
        filters: IncidentFilters,
        pagination: PaginationIn
    ) -> list[Incident]:
        async with self._async_sessionmaker() as session:
            query = select(IncidentModel)
            conditions = self._build_filter_conditions(filters)

            if conditions:
                query = query.where(and_(*conditions))

            query = query.order_by(IncidentModel.incident_date.desc())
            query = query.offset(pagination.offset).limit(pagination.limit)

            result = await session.execute(query)
            models = result.scalars().all()
            return [model.to_entity() for model in models]

    async def get_count(self, filters: IncidentFilters) -> int:
        async with self._async_sessionmaker() as session:
            query = select(func.count(IncidentModel.id))
            conditions = self._build_filter_conditions(filters)

            if conditions:
                query = query.where(and_(*conditions))

            result = await session.execute(query)
            return result.scalar_one()

    async def get_aggregated_summary(self, filters: IncidentFilters) -> dict:
        """Аналитическая сводка по всем измерениям."""
        async with self._async_sessionmaker() as session:
            conditions = self._build_filter_conditions(filters)
            where_clause = and_(*conditions) if conditions else True

            # Итоги
            totals_q = select(
                func.count(IncidentModel.id),
                func.count(func.distinct(IncidentModel.victim_name)),
                func.sum(case((IncidentModel.injury_type == InjuryType.FATAL.value, 1), else_=0)),
            ).where(where_clause)
            total_incidents, total_victims, total_fatalities = (await session.execute(totals_q)).one()

            # По классификации
            cls_q = select(
                IncidentModel.classification, func.count(IncidentModel.id)
            ).where(where_clause).group_by(IncidentModel.classification)
            by_classification = {str(k): v for k, v in (await session.execute(cls_q)).all() if k}

            # По типу травмы
            inj_q = select(
                IncidentModel.injury_type, func.count(IncidentModel.id)
            ).where(where_clause).group_by(IncidentModel.injury_type)
            by_injury_type = {str(k): v for k, v in (await session.execute(inj_q)).all() if k}

            # По регионам
            reg_q = select(
                IncidentModel.region, func.count(IncidentModel.id)
            ).where(where_clause).group_by(IncidentModel.region)
            by_region = {str(k): v for k, v in (await session.execute(reg_q)).all() if k}

            # По компаниям
            comp_q = select(
                IncidentModel.company, func.count(IncidentModel.id)
            ).where(where_clause).group_by(IncidentModel.company)
            by_company = {str(k): v for k, v in (await session.execute(comp_q)).all() if k}

            # По месяцам (YYYY-MM)
            month_q = select(
                func.to_char(IncidentModel.incident_date, 'YYYY-MM').label('month'),
                func.count(IncidentModel.id),
            ).where(where_clause).group_by('month').order_by('month')
            by_month = {str(k): v for k, v in (await session.execute(month_q)).all() if k}

            return {
                "total_incidents": total_incidents or 0,
                "total_victims": total_victims or 0,
                "total_fatalities": total_fatalities or 0,
                "by_classification": by_classification,
                "by_injury_type": by_injury_type,
                "by_region": by_region,
                "by_company": by_company,
                "by_month": by_month,
            }

    async def get_statistics(
        self,
        company_name: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> IncidentStatistics:
        async with self._async_sessionmaker() as session:
            query = select(
                func.count(IncidentModel.id),
                func.count(func.distinct(IncidentModel.victim_name)),
                func.sum(case((IncidentModel.injury_type == 'Смертельный исход', 1), else_=0))
            )

            conditions = []
            if company_name:
                conditions.append(IncidentModel.company == company_name)
            if date_from:
                conditions.append(IncidentModel.incident_date >= date_from)
            if date_to:
                conditions.append(IncidentModel.incident_date <= date_to)

            if conditions:
                query = query.where(and_(*conditions))

            total_count, total_victims, total_fatalities = (await session.execute(query)).one()

            # По классификации
            classification_query = select(IncidentModel.classification, func.count(IncidentModel.id)).group_by(IncidentModel.classification)
            if conditions:
                classification_query = classification_query.where(and_(*conditions))

            by_classification = {
                str(key): value for key, value in (await session.execute(classification_query)).all()
            }

            # По типу травмы
            injury_type_query = select(IncidentModel.injury_type, func.count(IncidentModel.id)).group_by(IncidentModel.injury_type)
            if conditions:
                injury_type_query = injury_type_query.where(and_(*conditions))

            by_injury_type = {
                str(key): value for key, value in (await session.execute(injury_type_query)).all() if key
            }

            return IncidentStatistics(
                total_count=total_count or 0,
                by_classification=by_classification,
                by_injury_type=by_injury_type,
                total_victims=total_victims or 0,
                total_fatalities=total_fatalities or 0,
            )

    async def get_regional_distribution(self) -> dict[str, int]:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(
                    IncidentModel.region,
                    func.count(IncidentModel.id)
                ).group_by(IncidentModel.region)
            )
            return {str(region): count for region, count in result.all()}

    async def bulk_create(self, incidents: list[Incident]) -> list[Incident]:
        """Массовое создание инцидентов.

        NOTE: refresh каждой модели после коммита — N+1 для больших батчей.
        """
        async with self._async_sessionmaker() as session:
            models = [IncidentModel.from_entity(incident) for incident in incidents]
            session.add_all(models)
            await session.commit()
            for model in models:
                await session.refresh(model)
            return [model.to_entity() for model in models]

    async def bulk_update(self, incidents: list[Incident]) -> list[Incident]:
        """Массовое обновление инцидентов. Ненайденные ID пропускаются."""
        async with self._async_sessionmaker() as session:
            updated_models = []
            for incident in incidents:
                model = await session.get(IncidentModel, incident.id)
                if model:
                     update_data = incident.model_dump(exclude={'id', 'created_at'})
                     for k, v in update_data.items():
                         setattr(model, k, _serialize_value(v))
                     updated_models.append(model)

            await session.commit()
            for model in updated_models:
                await session.refresh(model)
            return [m.to_entity() for m in updated_models]

    async def bulk_upsert(
        self,
        to_create: list[Incident],
        to_update: list[Incident],
    ) -> tuple[int, int]:
        """Атомарный upsert в одной транзакции.

        Args:
            to_create: новые инциденты для вставки.
            to_update: существующие инциденты для обновления.

        Returns:
            Кортеж (created_count, updated_count).
        """
        async with self._async_sessionmaker() as session:
            create_models = [IncidentModel.from_entity(inc) for inc in to_create]
            session.add_all(create_models)

            # Updates
            updated_count = 0
            for incident in to_update:
                model = await session.get(IncidentModel, incident.id)
                if model:
                    update_data = incident.model_dump(exclude={'id', 'created_at'})
                    for k, v in update_data.items():
                        setattr(model, k, _serialize_value(v))
                    updated_count += 1

            await session.commit()
            return len(create_models), updated_count

    async def update(self, incident: Incident) -> Incident:
        async with self._async_sessionmaker() as session:
            model = await session.get(IncidentModel, incident.id)
            if not model:
                raise IncidentNotFoundException(incident_id=incident.id)
            update_data = incident.model_dump(exclude={'id', 'created_at'})
            for key, value in update_data.items():
                setattr(model, key, _serialize_value(value))

            await session.commit()
            await session.refresh(model)
            return model.to_entity()

    async def get_candidates_for_matching(
        self, date_from: date, date_to: date,
    ) -> list[Incident]:
        """Кандидаты для матчинга с актами за точный диапазон дат."""
        async with self._async_sessionmaker() as session:
            query = select(IncidentModel).where(
                and_(
                    IncidentModel.incident_date >= date_from,
                    IncidentModel.incident_date <= date_to,
                )
            )
            result = await session.execute(query)
            return [m.to_entity() for m in result.scalars().all()]

    async def get_by_year_range(self, start_year: int, end_year: int) -> list[Incident]:
        """Инциденты за диапазон лет (для дедупликации).

        Загружает только поля, необходимые для ключа дедупликации
        (id, created_at, incident_date, company, classification,
        region, victim_name, location).
        """
        async with self._async_sessionmaker() as session:
             query = select(IncidentModel).options(
                 load_only(
                     IncidentModel.id,
                     IncidentModel.created_at,
                     IncidentModel.incident_date,
                     IncidentModel.company,
                     IncidentModel.classification,
                     IncidentModel.region,
                     IncidentModel.victim_name,
                     IncidentModel.location,
                 )
             ).where(
                 and_(
                     extract('year', IncidentModel.incident_date) >= start_year,
                     extract('year', IncidentModel.incident_date) <= end_year
                 )
             )
             result = await session.execute(query)
             models = result.scalars().all()
             return [model.to_entity() for model in models]


@dataclass
class SqlAlchemyEnquiryActRepository(BaseEnquiryActRepository, BaseSqlAlchemyRepository):
    """Репозиторий актов расследования (SQLAlchemy)"""

    async def create(self, act: EnquiryAct) -> EnquiryAct:
        async with self._async_sessionmaker() as session:
            model = EnquiryActModel.from_entity(act)
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return model.to_entity()

    async def get_by_id(self, act_id: UUID) -> Optional[EnquiryAct]:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(EnquiryActModel).where(EnquiryActModel.id == act_id)
            )
            model = result.scalar_one_or_none()
            return model.to_entity() if model else None

    async def get_by_incident_id(self, incident_id: UUID) -> list[EnquiryAct]:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(EnquiryActModel).where(
                    EnquiryActModel.incident_id == incident_id
                )
            )
            models = result.scalars().all()
            return [model.to_entity() for model in models]

    async def get_unlinked(self) -> list[EnquiryAct]:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(EnquiryActModel).where(
                    EnquiryActModel.link_status == EnquiryActLinkStatus.UNLINKED.value
                ).order_by(EnquiryActModel.uploaded_at.desc())
            )
            models = result.scalars().all()
            return [model.to_entity() for model in models]

    async def update(self, act: EnquiryAct) -> EnquiryAct:
        async with self._async_sessionmaker() as session:
            model = await session.get(EnquiryActModel, act.id)
            if not model:
                raise EnquiryActNotFoundException(act_id=act.id)
            update_data = act.model_dump(exclude={'id', 'created_at'})
            for key, value in update_data.items():
                setattr(model, key, _serialize_value(value))
            await session.commit()
            await session.refresh(model)
            return model.to_entity()

    async def bulk_update_link_status(
        self,
        updates: list[tuple[UUID, UUID, str]],
    ) -> int:
        """Атомарное обновление привязки актов к инцидентам в одной транзакции."""
        if not updates:
            return 0
        async with self._async_sessionmaker() as session:
            count = 0
            for act_id, incident_id, link_status in updates:
                model = await session.get(EnquiryActModel, act_id)
                if model:
                    model.incident_id = incident_id
                    model.link_status = link_status
                    count += 1
            await session.commit()
            return count

    def _build_act_filter_conditions(self, filters: EnquiryActFilters) -> list:
        """Построение условий фильтрации из EnquiryActFilters."""
        conditions = []

        if filters.act_type:
            conditions.append(EnquiryActModel.act_type == filters.act_type)
        if filters.link_status:
            conditions.append(EnquiryActModel.link_status == filters.link_status)

        if filters.date_from:
            conditions.append(EnquiryActModel.act_date >= filters.date_from)
        if filters.date_to:
            conditions.append(EnquiryActModel.act_date <= filters.date_to)

        if filters.victim_name:
            conditions.append(EnquiryActModel.victim_name.ilike(f"%{_escape_like(filters.victim_name)}%"))
        if filters.company_name:
            conditions.append(EnquiryActModel.company_name.ilike(f"%{_escape_like(filters.company_name)}%"))
        if filters.companies:
            conditions.append(
                or_(*[EnquiryActModel.company_name.ilike(f"%{_escape_like(c)}%") for c in filters.companies])
            )
        if filters.region:
            conditions.append(EnquiryActModel.region_from_act.ilike(f"%{_escape_like(filters.region)}%"))
        if filters.regions:
            conditions.append(
                or_(*[EnquiryActModel.region_from_act.ilike(f"%{_escape_like(r)}%") for r in filters.regions])
            )
        if filters.language:
            conditions.append(EnquiryActModel.language == filters.language)
        if filters.incident_id:
            conditions.append(EnquiryActModel.incident_id == UUID(filters.incident_id))

        # Фильтрация по тегам (@> — «содержит»)
        if filters.cause_category:
            conditions.append(EnquiryActModel.cause_categories.contains([filters.cause_category]))
        if filters.violation_type:
            conditions.append(EnquiryActModel.violation_types.contains([filters.violation_type]))
        if filters.industry_tag:
            conditions.append(EnquiryActModel.industry_tags.contains([filters.industry_tag]))

        return conditions

    async def get_filtered(
        self,
        filters: EnquiryActFilters,
        pagination: PaginationIn,
    ) -> list[EnquiryAct]:
        async with self._async_sessionmaker() as session:
            query = select(EnquiryActModel)
            conditions = self._build_act_filter_conditions(filters)

            if conditions:
                query = query.where(and_(*conditions))

            query = query.order_by(EnquiryActModel.uploaded_at.desc())
            query = query.offset(pagination.offset).limit(pagination.limit)

            result = await session.execute(query)
            models = result.scalars().all()
            return [model.to_entity() for model in models]

    async def get_count(self, filters: EnquiryActFilters) -> int:
        async with self._async_sessionmaker() as session:
            query = select(func.count(EnquiryActModel.id))
            conditions = self._build_act_filter_conditions(filters)

            if conditions:
                query = query.where(and_(*conditions))

            result = await session.execute(query)
            return result.scalar_one()

    # Допустимые колонки для агрегации (защита от SQL-инъекций)
    _ALLOWED_TAG_FIELDS = frozenset({'cause_categories', 'violation_types', 'industry_tags'})

    async def get_tag_patterns(
        self,
        tag_field: str,
        limit: int = 10,
        incident_ids: list[UUID] | None = None,
    ) -> list[tuple[str, int]]:
        """Агрегация паттернов: топ-N значений тегов через unnest."""
        if tag_field not in self._ALLOWED_TAG_FIELDS:
            return []

        where_clause = ""
        params: dict = {"lim": limit}
        if incident_ids:
            where_clause = "WHERE incident_id = ANY(:ids) "
            params["ids"] = incident_ids

        sql = text(
            f"SELECT tag, COUNT(*) AS cnt "
            f"FROM enquiry_acts, unnest({tag_field}) AS tag "
            f"{where_clause}"
            f"GROUP BY tag ORDER BY cnt DESC LIMIT :lim"
        )

        async with self._async_sessionmaker() as session:
            result = await session.execute(sql, params)
            return [(row[0], row[1]) for row in result.all()]

    async def get_linked_act_summaries(
        self,
        incident_ids: list[UUID],
        limit: int = 30,
    ) -> list[dict]:
        """Краткие данные актов привязанных к инцидентам — для контекста отчёта."""
        if not incident_ids:
            return []

        async with self._async_sessionmaker() as session:
            query = (
                select(
                    EnquiryActModel.ai_summary,
                    EnquiryActModel.root_causes,
                    EnquiryActModel.immediate_causes,
                    EnquiryActModel.employer_fault_pct,
                    EnquiryActModel.corrective_measures,
                    EnquiryActModel.cause_categories,
                    EnquiryActModel.violation_types,
                    EnquiryActModel.conclusions,
                    EnquiryActModel.legal_violations,
                    EnquiryActModel.responsible_persons,
                    EnquiryActModel.circumstances,
                    EnquiryActModel.workplace_description,
                )
                .where(
                    and_(
                        EnquiryActModel.incident_id.in_(incident_ids),
                        EnquiryActModel.ai_summary.isnot(None),
                        EnquiryActModel.ai_summary != "",
                    )
                )
                .limit(limit)
            )
            result = await session.execute(query)
            return [
                {
                    "ai_summary": row.ai_summary,
                    "root_causes": row.root_causes,
                    "immediate_causes": row.immediate_causes,
                    "employer_fault_pct": row.employer_fault_pct,
                    "corrective_measures": row.corrective_measures,
                    "cause_categories": row.cause_categories or [],
                    "violation_types": row.violation_types or [],
                    "conclusions": row.conclusions,
                    "legal_violations": row.legal_violations or [],
                    "responsible_persons": row.responsible_persons or [],
                    "circumstances": row.circumstances,
                    "workplace_description": row.workplace_description,
                }
                for row in result.all()
            ]


@dataclass
class SqlAlchemyRecommendationRepository(BaseRecommendationRepository, BaseSqlAlchemyRepository):
    """Репозиторий рекомендаций (SQLAlchemy)"""

    async def create(self, recommendation: Recommendation) -> Recommendation:
        async with self._async_sessionmaker() as session:
            model = RecommendationModel.from_entity(recommendation)
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return model.to_entity()

    async def get_by_id(self, recommendation_id: UUID) -> Optional[Recommendation]:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(RecommendationModel).where(
                    RecommendationModel.id == recommendation_id
                )
            )
            model = result.scalar_one_or_none()
            return model.to_entity() if model else None

    async def get_by_incident_id(self, incident_id: UUID) -> list[Recommendation]:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(RecommendationModel).where(
                    RecommendationModel.incident_id == incident_id
                )
            )
            models = result.scalars().all()
            return [model.to_entity() for model in models]

    async def update(self, recommendation: Recommendation) -> Recommendation:
        async with self._async_sessionmaker() as session:
            model = await session.get(RecommendationModel, recommendation.id)
            if not model:
                raise RecommendationNotFoundException(recommendation_id=recommendation.id)

            model.recommendation_text = recommendation.recommendation_text
            model.priority = recommendation.priority.value
            model.status = recommendation.status.value
            model.legal_references = recommendation.legal_references

            await session.commit()
            await session.refresh(model)
            return model.to_entity()
