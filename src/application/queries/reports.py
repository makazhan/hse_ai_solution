"""Запросы генерации аналитического отчёта."""
import asyncio
import datetime
import logging
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

from src.application.queries.base import BaseQuery, BaseQueryHandler
from src.application.filters.incidents import IncidentFilters
from src.application.filters.common import PaginationIn
from src.application.interfaces.repositories.incidents import (
    BaseIncidentRepository,
    BaseEnquiryActRepository,
)
from src.application.interfaces.llm_report import BaseLLMReportService
from src.application.services.report_npa_search import ReportNpaSearchService, format_norms_for_llm

logger = logging.getLogger(__name__)


@dataclass
class CauseCategoryDTO:
    """Категория причин с анализом."""
    category: str
    count: int
    analysis: str = ""


@dataclass
class RecurrencePatternDTO:
    """Паттерн повторяемости."""
    pattern_description: str
    frequency: int
    affected_companies: list[str] = field(default_factory=list)
    affected_regions: list[str] = field(default_factory=list)


@dataclass
class RiskItemDTO:
    """Оценка риска."""
    risk_type: str
    severity: str
    description: str
    affected_entities: list[str] = field(default_factory=list)


@dataclass
class RecommendationItemDTO:
    """Рекомендация."""
    priority: str
    recommendation: str
    rationale: str
    target_entities: list[str] = field(default_factory=list)


@dataclass
class AnalyticalReport:
    """Аналитический отчёт."""
    summary_narrative: str
    key_findings: list[str]
    cause_analysis: str
    top_cause_categories: list[CauseCategoryDTO]
    recurrence_patterns: list[RecurrencePatternDTO]
    risk_assessment: list[RiskItemDTO]
    overall_risk_level: str
    recommendations: list[RecommendationItemDTO]
    immediate_actions: list[str]
    report_language: str = "ru"
    confidence_note: Optional[str] = None
    raw_summary: Optional[dict] = None


@dataclass(frozen=True)
class GenerateAnalyticalReportQuery(BaseQuery):
    """Запрос генерации аналитического отчёта."""
    filters: IncidentFilters
    include_ai_analysis: bool = True


@dataclass(frozen=True)
class GenerateAnalyticalReportQueryHandler(
    BaseQueryHandler[GenerateAnalyticalReportQuery, AnalyticalReport]
):
    """Обработчик генерации аналитического отчёта (секционная архитектура).

    Фаза 0:   Загрузка данных из БД
    Фаза 0.5: RAG-поиск по НПА
    Фаза 1:   Подготовка (Python-шаблоны, ~1ms)
    Фаза 2:   LLM секции 2+3 параллельно (causes + risks)
    Фаза 3:   LLM секция 4 последовательно (recommendations)
    Фаза 4:   Сборка AnalyticalReport DTO
    """
    incident_repository: BaseIncidentRepository
    enquiry_act_repository: BaseEnquiryActRepository
    llm_report_service: Optional[BaseLLMReportService]
    npa_search_service: Optional[ReportNpaSearchService] = None

    async def handle(
        self, query: GenerateAnalyticalReportQuery,
    ) -> AnalyticalReport:
        """Генерация аналитического отчёта."""
        filters = query.filters

        # Фаза 0: параллельная загрузка сводки и инцидентов
        summary, incidents = await asyncio.gather(
            self.incident_repository.get_aggregated_summary(filters),
            self.incident_repository.get_filtered(
                filters=filters,
                pagination=PaginationIn(limit=50, offset=0),
            ),
        )

        # Ранний выход при пустом датасете
        if summary.get("total_incidents", 0) == 0:
            return self._build_stub_report(
                summary,
                note="Нет инцидентов, соответствующих заданным фильтрам.",
            )

        # Фаза 0 (продолжение): акты, категории причин, типы нарушений
        incident_ids = [inc.id for inc in incidents if inc.id]
        (
            act_summaries,
            cause_categories,
            violation_types,
        ) = await asyncio.gather(
            self.enquiry_act_repository.get_linked_act_summaries(
                incident_ids=incident_ids,
                limit=30,
            ),
            self.enquiry_act_repository.get_tag_patterns(
                "cause_categories", limit=15,
                incident_ids=incident_ids or None,
            ),
            self.enquiry_act_repository.get_tag_patterns(
                "violation_types", limit=15,
                incident_ids=incident_ids or None,
            ),
        )

        # Данные о повторяемости
        recurrence_data: dict[str, int] = {}
        for inc in incidents:
            if inc.is_recurrent:
                company_name = (
                    inc.company.value
                    if hasattr(inc.company, 'value')
                    else str(inc.company)
                )
                recurrence_data[company_name] = (
                    recurrence_data.get(company_name, 0) + 1
                )

        # Фаза 0.5: RAG-поиск по НПА
        relevant_norms: list[dict] = []
        violation_type_tags = [tag for tag, _ in violation_types]
        cause_category_tags = [tag for tag, _ in cause_categories]
        legal_violations = self._collect_legal_violations(act_summaries)

        if self.npa_search_service and query.include_ai_analysis:
            try:
                npa_results = await self.npa_search_service.search_for_report(
                    violation_types=violation_type_tags,
                    cause_categories=cause_category_tags,
                    legal_violations=legal_violations,
                )
                relevant_norms = format_norms_for_llm(npa_results)
            except Exception:
                logger.warning(
                    "NPA RAG search failed, продолжаем без норм",
                    exc_info=True,
                )

        # Ранний выход если AI не запрошен
        if not query.include_ai_analysis or self.llm_report_service is None:
            logger.info(
                "LLM report пропущен (include_ai=%s, service=%s)",
                query.include_ai_analysis,
                type(self.llm_report_service).__name__,
            )
            stub = self._build_stub_report(summary)
            # Секция 1: детерминированная narrative
            narrative, findings = self._generate_summary_narrative(summary)
            stub.summary_narrative = narrative
            stub.key_findings = findings
            return stub

        # Фаза 1: подготовка данных (Python, ~1ms)
        summary_narrative, key_findings = self._generate_summary_narrative(summary)
        illustrative_cases = self._select_illustrative_cases(incidents, limit=5)
        training_stats = self._compute_training_stats(incidents)
        top_equipment = self._compute_top_equipment(incidents, limit=5)
        responsible_persons_summary = self._aggregate_responsible_persons(act_summaries)

        cause_patterns = {
            "cause_categories": [
                {"tag": tag, "count": count}
                for tag, count in cause_categories
            ],
            "violation_types": [
                {"tag": tag, "count": count}
                for tag, count in violation_types
            ],
        }

        # Фаза 2: LLM секции 2+3 ПАРАЛЛЕЛЬНО
        t_llm_start = time.monotonic()
        # act_summaries ограничиваем до 20 — causes-промпт фокусирован,
        # 20 актов достаточно для анализа; дополнительная обрезка в _call_llm при превышении лимита.
        causes_ctx = {
            "cause_patterns": cause_patterns,
            "act_summaries": act_summaries[:20],
            "illustrative_cases": illustrative_cases,
            "recurrence_data": recurrence_data,
            "training_stats": training_stats,
            "top_equipment": top_equipment,
        }
        risks_ctx = {
            "summary": summary,
            "cause_patterns": cause_patterns,
            "legal_violations": legal_violations,
            "relevant_legal_norms": relevant_norms,
            "recurrence_data": recurrence_data,
        }

        causes_result, risks_result = await asyncio.gather(
            self._safe_generate_section("causes", causes_ctx),
            self._safe_generate_section("risks", risks_ctx),
        )
        t_phase2 = time.monotonic() - t_llm_start
        logger.info("Фаза 2 (causes+risks параллельно): %.1fс", t_phase2)

        # Фаза 3: LLM секция 4 ПОСЛЕДОВАТЕЛЬНО (зависит от 2+3)
        t_phase3_start = time.monotonic()
        recommendations_ctx = {
            "summary_brief": {
                "total_incidents": summary.get("total_incidents", 0),
                "total_victims": summary.get("total_victims", 0),
                "total_fatalities": summary.get("total_fatalities", 0),
            },
            "cause_analysis": causes_result.get("cause_analysis", ""),
            "top_cause_categories": causes_result.get("top_cause_categories", []),
            "risk_assessment": risks_result.get("risk_assessment", []),
            "overall_risk_level": risks_result.get("overall_risk_level", "не определён"),
            "relevant_legal_norms": relevant_norms,
            "legal_violations": legal_violations,
            "responsible_persons_summary": responsible_persons_summary,
        }

        try:
            recommendations_result = await self.llm_report_service.generate_section(
                "recommendations", recommendations_ctx,
            )
        except Exception:
            logger.error("Секция recommendations упала", exc_info=True)
            recommendations_result = {}
        t_phase3 = time.monotonic() - t_phase3_start
        t_total_llm = time.monotonic() - t_llm_start
        logger.info(
            "Фаза 3 (recommendations): %.1fс | Итого LLM: %.1fс",
            t_phase3, t_total_llm,
        )

        # Фаза 4: сборка AnalyticalReport DTO
        # Определяем confidence_note при частичных сбоях
        failed_sections = []
        if not causes_result:
            failed_sections.append("causes")
        if not risks_result:
            failed_sections.append("risks")
        if not recommendations_result:
            failed_sections.append("recommendations")

        confidence_note = None
        if failed_sections:
            confidence_note = (
                f"Секции {', '.join(failed_sections)} не были сгенерированы из-за ошибок LLM."
            )

        return AnalyticalReport(
            summary_narrative=summary_narrative,
            key_findings=key_findings,
            cause_analysis=causes_result.get("cause_analysis", ""),
            top_cause_categories=[
                CauseCategoryDTO(**item)
                for item in causes_result.get("top_cause_categories", [])
            ],
            recurrence_patterns=[
                RecurrencePatternDTO(**item)
                for item in causes_result.get("recurrence_patterns", [])
            ],
            risk_assessment=[
                RiskItemDTO(**item)
                for item in risks_result.get("risk_assessment", [])
            ],
            overall_risk_level=risks_result.get("overall_risk_level", "не определён"),
            recommendations=[
                RecommendationItemDTO(**item)
                for item in recommendations_result.get("recommendations", [])
            ],
            immediate_actions=recommendations_result.get("immediate_actions", []),
            confidence_note=confidence_note,
            raw_summary=summary,
        )

    async def _safe_generate_section(self, section_name: str, context: dict) -> dict:
        """Обёртка для generate_section с перехватом исключений."""
        try:
            return await self.llm_report_service.generate_section(section_name, context)
        except Exception:
            logger.error("Секция %s упала", section_name, exc_info=True)
            return {}

    @staticmethod
    def _generate_summary_narrative(summary: dict) -> tuple[str, list[str]]:
        """Секция 1: детерминированная генерация summary_narrative + key_findings."""
        total = summary.get("total_incidents", 0)
        victims = summary.get("total_victims", 0)
        fatalities = summary.get("total_fatalities", 0)

        # Основной абзац
        parts = [
            f"За анализируемый период зарегистрировано {total} инцидентов "
            f"на производстве, в результате которых пострадало {victims} человек"
        ]
        if fatalities:
            parts[0] += f", из них {fatalities} со смертельным исходом"
        parts[0] += "."

        # Топ регионов
        by_region = summary.get("by_region", {})
        if by_region:
            sorted_regions = sorted(by_region.items(), key=lambda x: x[1], reverse=True)
            top_3 = sorted_regions[:3]
            region_str = ", ".join(f"{r} ({c})" for r, c in top_3)
            parts.append(f"Наибольшее число инцидентов зафиксировано в: {region_str}.")

        # Топ компаний
        by_company = summary.get("by_company", {})
        if by_company:
            sorted_companies = sorted(by_company.items(), key=lambda x: x[1], reverse=True)
            top_3 = sorted_companies[:3]
            company_str = ", ".join(f"{c} ({n})" for c, n in top_3)
            parts.append(f"Лидеры по числу инцидентов среди компаний: {company_str}.")

        # Тренд по месяцам
        by_month = summary.get("by_month", {})
        if len(by_month) >= 2:
            sorted_months = sorted(by_month.items())
            first_val = sorted_months[0][1]
            last_val = sorted_months[-1][1]
            if last_val > first_val * 1.2:
                parts.append(
                    f"Наблюдается рост числа инцидентов: "
                    f"с {first_val} ({sorted_months[0][0]}) до {last_val} ({sorted_months[-1][0]})."
                )
            elif last_val < first_val * 0.8:
                parts.append(
                    f"Наблюдается снижение числа инцидентов: "
                    f"с {first_val} ({sorted_months[0][0]}) до {last_val} ({sorted_months[-1][0]})."
                )

        narrative = "\n\n".join(parts)

        # key_findings
        findings: list[str] = []
        findings.append(f"Всего {total} инцидентов, {victims} пострадавших, {fatalities} погибших.")

        by_injury = summary.get("by_injury_type", {})
        if by_injury:
            for itype, count in sorted(by_injury.items(), key=lambda x: x[1], reverse=True):
                pct = round(count / total * 100, 1) if total else 0
                findings.append(f"{itype}: {count} ({pct}% от общего числа).")
                if len(findings) >= 5:
                    break

        if by_region:
            top_region = max(by_region, key=lambda k: by_region[k])
            findings.append(
                f"Регион с наибольшим числом инцидентов: {top_region} ({by_region[top_region]})."
            )

        return narrative, findings[:7]

    @staticmethod
    def _select_illustrative_cases(incidents: list, limit: int = 5) -> list[dict]:
        """Скоринг и отбор характерных кейсов."""
        recent_threshold = datetime.date.today() - datetime.timedelta(days=90)
        scored = []
        for inc in incidents:
            score = 0
            injury = (
                inc.injury_type.value
                if inc.injury_type and hasattr(inc.injury_type, 'value')
                else str(inc.injury_type) if inc.injury_type else ""
            )
            if "смертельн" in injury.lower() or "fatal" in injury.lower():
                score += 10
            elif "тяжел" in injury.lower() or "severe" in injury.lower():
                score += 5
            if inc.is_recurrent:
                score += 3
            if inc.equipment:
                score += 2
            if inc.incident_date and inc.incident_date >= recent_threshold:
                score += 1

            scored.append((score, inc))

        scored.sort(key=lambda x: x[0], reverse=True)

        cases = []
        for _, inc in scored[:limit]:
            company = (
                inc.company.value
                if hasattr(inc.company, 'value')
                else str(inc.company)
            )
            region = (
                inc.region.value
                if hasattr(inc.region, 'value')
                else str(inc.region)
            )
            classification = (
                inc.classification.value
                if hasattr(inc.classification, 'value')
                else str(inc.classification)
            )
            injury_type = (
                inc.injury_type.value
                if inc.injury_type and hasattr(inc.injury_type, 'value')
                else str(inc.injury_type) if inc.injury_type else None
            )
            cases.append({
                "incident_date": str(inc.incident_date),
                "company": company,
                "region": region,
                "classification": classification,
                "injury_type": injury_type,
                "description": (inc.description or "")[:500],
                "preliminary_causes": (inc.preliminary_causes or "")[:300],
                "root_causes": (inc.root_causes or "")[:300],
                "victim_position": inc.victim_position,
                "equipment": inc.equipment,
                "is_recurrent": inc.is_recurrent,
                "victim_count": inc.victim_count,
                "fatality_count": inc.fatality_count,
            })
        return cases

    @staticmethod
    def _compute_training_stats(incidents: list) -> dict:
        """Статистика обучения: total и процент без обучения."""
        total = len(incidents)
        if not total:
            return {"total": 0, "without_training_pct": 0.0}
        without = sum(
            1 for inc in incidents
            if inc.safety_training_completed is False
        )
        return {
            "total": total,
            "without_training_pct": round(without / total * 100, 1),
        }

    @staticmethod
    def _compute_top_equipment(incidents: list, limit: int = 5) -> list[dict]:
        """Оборудование с наибольшим числом инцидентов."""
        counter: Counter = Counter()
        for inc in incidents:
            if inc.equipment:
                counter[inc.equipment] += 1
        return [
            {"equipment": eq, "count": cnt}
            for eq, cnt in counter.most_common(limit)
        ]

    @staticmethod
    def _aggregate_responsible_persons(act_summaries: list[dict]) -> list[dict]:
        """Агрегация responsible_persons по должностям."""
        position_data: dict[str, dict] = {}
        for act in act_summaries:
            for person in act.get("responsible_persons", []):
                if not isinstance(person, dict):
                    continue
                pos = person.get("position", "не указано")
                if not pos:
                    pos = "не указано"
                if pos not in position_data:
                    position_data[pos] = {"count": 0, "violations": set()}
                position_data[pos]["count"] += 1
                violation = person.get("violation")
                if violation:
                    position_data[pos]["violations"].add(violation)

        return [
            {
                "position": pos,
                "count": data["count"],
                "violations": list(data["violations"]),
            }
            for pos, data in sorted(
                position_data.items(),
                key=lambda x: x[1]["count"],
                reverse=True,
            )
        ]

    @staticmethod
    def _collect_legal_violations(act_summaries: list[dict]) -> list[str]:
        """Собрать и дедуплицировать legal_violations из актов."""
        violations: set[str] = set()
        for act in act_summaries:
            for v in act.get("legal_violations", []):
                if v and isinstance(v, str):
                    violations.add(v.strip())
        return list(violations)

    @staticmethod
    def _build_stub_report(
        summary: dict,
        note: str = "AI-анализ не был выполнен. Отображена только сводная статистика.",
    ) -> AnalyticalReport:
        """Стаб-отчёт без LLM — только статистика."""
        return AnalyticalReport(
            summary_narrative=(
                f"Всего инцидентов: {summary.get('total_incidents', 0)}, "
                f"пострадавших: {summary.get('total_victims', 0)}, "
                f"погибших: {summary.get('total_fatalities', 0)}."
            ),
            key_findings=["AI-анализ не выполнен — данные без интерпретации"],
            cause_analysis="",
            top_cause_categories=[],
            recurrence_patterns=[],
            risk_assessment=[],
            overall_risk_level="не определён",
            recommendations=[],
            immediate_actions=[],
            confidence_note=note,
            raw_summary=summary,
        )
