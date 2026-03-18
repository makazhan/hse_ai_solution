"""Сервис авто-матчинга актов расследования с инцидентами."""
import datetime
import logging
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Optional
from uuid import UUID

from src.application.interfaces.repositories.incidents import (
    BaseEnquiryActRepository,
    BaseIncidentRepository,
)
from src.domain.entities.incidents import EnquiryAct, Incident
from src.domain.enums.incidents import EnquiryActLinkStatus

logger = logging.getLogger(__name__)

# Порог для автоматической привязки
MATCH_THRESHOLD = 0.80
# Подстрока — сильный, но не точный сигнал (ниже 1.0, т.к. не exact match)
SUBSTRING_SCORE = 0.9


@dataclass
class MatchResult:
    """Результат матчинга акта с инцидентом."""
    incident_id: UUID
    score: float


def _normalize(text: Optional[str]) -> str:
    """Нормализация строки: lowercase, схлопывание пробелов, удаление кавычек."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[«»""\'\']', '', text)
    text = " ".join(text.split())
    return text


def _score_date(act_date: Optional[datetime.date], incident_date: Optional[datetime.date]) -> float:
    """Скоринг по дате: линейное затухание за ±3 дня."""
    if not act_date or not incident_date:
        return 0.0
    diff = abs((act_date - incident_date).days)
    if diff > 3:
        return 0.0
    return 1.0 - diff / 4.0


def _score_name(act_name: Optional[str], incident_name: Optional[str]) -> float:
    """Скоринг по ФИО пострадавшего."""
    a = _normalize(act_name)
    b = _normalize(incident_name)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _score_company(
    act_company: Optional[str],
    incident_company: Optional[str],
    incident_dzo: Optional[str],
) -> float:
    """Скоринг по компании/ДЗО: подстрока + SequenceMatcher, берём max."""
    a = _normalize(act_company)
    if not a:
        return 0.0

    scores = []
    for raw in (incident_company, incident_dzo):
        b = _normalize(str(raw) if raw else "")
        if not b:
            continue
        if a in b or b in a:
            scores.append(SUBSTRING_SCORE)
        else:
            scores.append(SequenceMatcher(None, a, b).ratio())

    return max(scores) if scores else 0.0


def _score_region(act_region: Optional[str], incident_region: Optional[str]) -> float:
    """Скоринг по региону."""
    a = _normalize(act_region)
    b = _normalize(str(incident_region) if incident_region else "")
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return SUBSTRING_SCORE
    return SequenceMatcher(None, a, b).ratio()


def _score_injury_type(act_severity: Optional[str], incident_injury: Optional[str]) -> float:
    """Скоринг по типу травмы (keyword-based)."""
    a = _normalize(act_severity)
    b = _normalize(str(incident_injury) if incident_injury else "")
    if not a or not b:
        return 0.0

    keywords = {
        "смертельн": "смертельн",
        "летальн": "смертельн",
        "тяжел": "тяжел",
        "тяжёл": "тяжел",
        "лёгк": "лёгк",
        "легк": "лёгк",
        "групповой": "групповой",
        "групповых": "групповой",
    }

    a_cat = None
    b_cat = None
    for kw, cat in keywords.items():
        if kw in a:
            a_cat = cat
        if kw in b:
            b_cat = cat

    if a_cat and b_cat:
        return 1.0 if a_cat == b_cat else 0.3
    return 0.0


def _compute_score(act: EnquiryAct, incident: Incident) -> float:
    """Взвешенная сумма 5 компонент."""
    # Компания — конвертируем enum в строку
    company_str = incident.company.value if hasattr(incident.company, 'value') else str(incident.company)
    region_str = incident.region.value if hasattr(incident.region, 'value') else str(incident.region)
    injury_str = incident.injury_type.value if incident.injury_type and hasattr(incident.injury_type, 'value') else str(incident.injury_type) if incident.injury_type else None

    return (
        0.35 * _score_date(act.incident_date_from_act, incident.incident_date)
        + 0.30 * _score_name(act.victim_name_from_act, incident.victim_name)
        + 0.20 * _score_company(act.company_name_from_act, company_str, incident.dzo)
        + 0.10 * _score_region(act.region_from_act, region_str)
        + 0.05 * _score_injury_type(act.injury_severity, injury_str)
    )


@dataclass
class ActMatchingService:
    """Сервис сопоставления актов расследования с инцидентами."""
    incident_repository: BaseIncidentRepository
    enquiry_act_repository: BaseEnquiryActRepository

    async def _get_candidate_incidents_by_date(
        self, target_date: datetime.date,
    ) -> list[Incident]:
        """Запрос кандидатов из БД: ±3 дня от целевой даты."""
        date_from = target_date - datetime.timedelta(days=3)
        date_to = target_date + datetime.timedelta(days=3)
        return await self.incident_repository.get_candidates_for_matching(date_from, date_to)

    def _find_best_match(
        self, act: EnquiryAct, candidates: list[Incident],
    ) -> Optional[MatchResult]:
        """Перебор кандидатов, скоринг, выбор лучшего выше порога."""
        best_score = 0.0
        best_id = None

        for incident in candidates:
            score = _compute_score(act, incident)
            if score > best_score:
                best_score = score
                best_id = incident.id

        if best_score >= MATCH_THRESHOLD and best_id:
            return MatchResult(incident_id=best_id, score=best_score)
        return None

    async def find_best_incident_for_act(
        self, act: EnquiryAct,
    ) -> Optional[MatchResult]:
        """Направление A: акт → инцидент (при загрузке)."""
        if not act.incident_date_from_act:
            logger.debug("Матчинг пропущен: incident_date_from_act отсутствует (act_id=%s)", act.id)
            return None

        candidates = await self._get_candidate_incidents_by_date(act.incident_date_from_act)
        if not candidates:
            logger.debug("Матчинг: кандидатов не найдено за ±3 дня (act_id=%s)", act.id)
            return None

        result = self._find_best_match(act, candidates)
        if result:
            logger.debug(
                "Матчинг: акт %s → инцидент %s (score=%.3f)",
                act.id, result.incident_id, result.score,
            )
        else:
            logger.debug("Матчинг: подходящий инцидент не найден (act_id=%s)", act.id)
        return result

    async def adopt_unlinked_acts(
        self, new_incidents: list[Incident],
    ) -> list[tuple[UUID, UUID, float]]:
        """Направление C: инцидент → акт (при импорте журнала).

        Returns:
            Список (act_id, incident_id, score) успешных привязок.
        """
        unlinked = await self.enquiry_act_repository.get_unlinked()
        if not unlinked:
            return []

        # Фильтр: только акты с извлечённой датой инцидента
        eligible = [a for a in unlinked if a.incident_date_from_act is not None]
        if not eligible:
            logger.info("Усыновление: нет UNLINKED актов с incident_date_from_act")
            return []

        adoptions: list[tuple[UUID, UUID, float]] = []

        for act in eligible:
            result = self._find_best_match(act, new_incidents)
            if result:
                adoptions.append((act.id, result.incident_id, result.score))
                logger.debug(
                    "Усыновление: акт %s → инцидент %s (score=%.3f)",
                    act.id, result.incident_id, result.score,
                )

        # Атомарное обновление всех привязок в одной транзакции
        if adoptions:
            updates = [
                (act_id, inc_id, EnquiryActLinkStatus.AUTO_MATCHED.value)
                for act_id, inc_id, _score in adoptions
            ]
            await self.enquiry_act_repository.bulk_update_link_status(updates)

        logger.info("Усыновление завершено: %d актов привязано", len(adoptions))
        return adoptions
