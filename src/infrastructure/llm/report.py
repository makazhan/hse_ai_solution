"""LLM-сервис генерации аналитического отчёта по данным инцидентов ТБ."""
import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Optional

from openai import (
    APIConnectionError,
    APITimeoutError,
    AsyncOpenAI,
    InternalServerError,
    RateLimitError,
)
from pydantic import BaseModel

from src.application.exceptions.llm import LLMReportGenerationFailedException
from src.application.interfaces.llm_report import BaseLLMReportService
from src.infrastructure.llm.report_prompts import (
    CAUSES_SYSTEM_PROMPT,
    RECOMMENDATIONS_SYSTEM_PROMPT,
    RISKS_SYSTEM_PROMPT,
)
from src.infrastructure.llm.report_schema import AnalyticalReportLLMResponse
from src.infrastructure.llm.report_section_schemas import (
    CausesSectionResponse,
    RecommendationsSectionResponse,
    RisksSectionResponse,
)
from src.infrastructure.llm.utils import get_retry_wait

logger = logging.getLogger(__name__)

# Максимальная длина входного контекста (символов).
# gemma3-27b на LiteLLM-прокси рвёт соединение при слишком больших запросах.
MAX_CONTEXT_CHARS = 30_000

# Маппинг секций: промпт, Pydantic-схема, max_tokens
_SECTION_CONFIG: dict[str, tuple[str, type[BaseModel], int]] = {
    "causes": (CAUSES_SYSTEM_PROMPT, CausesSectionResponse, 4096),
    "risks": (RISKS_SYSTEM_PROMPT, RisksSectionResponse, 4096),
    "recommendations": (RECOMMENDATIONS_SYSTEM_PROMPT, RecommendationsSectionResponse, 4096),
}

# Лимиты контекста по секциям
_SECTION_MAX_CONTEXT: dict[str, int] = {
    "causes": 20_000,
    "risks": 15_000,
    "recommendations": 18_000,
}

REPORT_SYSTEM_PROMPT = """\
Ты — эксперт по охране труда и промышленной безопасности (Казахстан).
Тебе предоставлены данные об инцидентах на производстве за определённый период.
Твоя задача — составить профессиональный аналитический отчёт.

ВХОДНЫЕ ДАННЫЕ (JSON):
- "summary" — агрегированная статистика: total_incidents, total_victims,
  total_fatalities, by_classification (по видам), by_injury_type (по тяжести),
  by_region, by_company, by_month (YYYY-MM)
- "incidents_sample" — выборка инцидентов с полями: incident_date, company,
  region, classification, injury_type, description, preliminary_causes,
  root_causes, victim_position, work_type, equipment,
  safety_training_completed, is_recurrent, victim_count, fatality_count
- "cause_patterns" — топ причин из актов расследования:
  cause_categories [{tag, count}], violation_types [{tag, count}]
- "act_summaries" — резюме из актов: ai_summary, root_causes,
  immediate_causes, employer_fault_pct, corrective_measures, conclusions
- "recurrence_data" — повторяемость: {компания: количество_повторных_инцидентов}
- "relevant_legal_norms" — нормы законодательства РК, найденные по типам нарушений.
  Каждая запись содержит: document (название НПА), text (текст нормы),
  adilet_link (ссылка на Adilet), act_types (тип: КОД/ЗАК/ПОСТ/ПРИК).

ТРЕБОВАНИЯ К ОТЧЁТУ:
Верни ответ СТРОГО в формате JSON:

{
  "summary_narrative": "Интерпретация статистики. 2-4 абзаца. \
Общее количество инцидентов, динамика по месяцам (рост/снижение), \
наиболее пострадавшие регионы и компании, доля тяжёлых травм и смертей.",

  "key_findings": ["Ключевой вывод 1", "Ключевой вывод 2", ...],

  "cause_analysis": "Анализ причин. 2-4 абзаца. Опирайся на cause_patterns \
и act_summaries. Преобладающие категории, связь типов нарушений с тяжестью.",

  "top_cause_categories": [
    {"category": "название", "count": N, "analysis": "почему лидирует"}
  ],

  "recurrence_patterns": [
    {
      "pattern_description": "описание повторяющегося паттерна",
      "frequency": N,
      "affected_companies": ["..."],
      "affected_regions": ["..."]
    }
  ],

  "risk_assessment": [
    {
      "risk_type": "финансовый",
      "severity": "высокий | средний | низкий",
      "description": "описание со ссылками на данные",
      "affected_entities": ["компания/регион"]
    },
    { "risk_type": "регуляторный", ... },
    { "risk_type": "репутационный", ... }
  ],

  "overall_risk_level": "высокий | средний | низкий",

  "recommendations": [
    {
      "priority": "высокий | средний | низкий",
      "recommendation": "конкретная рекомендация",
      "rationale": "обоснование с цифрами из данных",
      "target_entities": ["компании/регионы"]
    }
  ],

  "immediate_actions": ["первоочередное действие 1", ...],

  "report_language": "ru",

  "confidence_note": "примечание если данных мало" | null
}

ПРАВИЛА:
1. Все выводы ДОЛЖНЫ опираться на предоставленные данные — не выдумывай фактов.
2. Упоминай конкретные компании, регионы и цифры.
3. Если данных мало — укажи в confidence_note.
4. Рекомендации должны быть практичными для казахстанских предприятий.
5. Финансовые риски: штрафы, компенсации, простои.
6. Регуляторные риски: нарушения ТК РК, проверки Госинспекции труда, приостановка работ.
7. Репутационные риски: ESG-рейтинги «Самрук-Қазына», публичность.
8. Язык — русский, стиль — официально-деловой.
9. key_findings: 3-7 пунктов. recommendations: 5-10 пунктов.
10. Если в by_month виден тренд (рост/снижение) — отметь обязательно.
11. Верни ТОЛЬКО JSON, без пояснений вне JSON.
12. При упоминании законодательства ссылайся ТОЛЬКО на нормы из "relevant_legal_norms". \
НЕ выдумывай номера статей — используй только предоставленные. \
Если relevant_legal_norms пуст — укажи, что конкретные статьи не найдены."""


_RETRYABLE_ERRORS = (
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    InternalServerError,
)


@dataclass
class LLMReportService(BaseLLMReportService):
    """Сервис генерации аналитического отчёта через LLM."""
    client: AsyncOpenAI
    model: str
    max_retries: int = 3
    max_tokens: int = 8192

    async def _call_llm(
        self,
        system_prompt: str,
        context: dict,
        schema: type[BaseModel],
        max_tokens: int,
        max_context_chars: int,
        label: str = "report",
    ) -> Optional[dict]:
        """Общая логика вызова LLM с retry и валидацией через Pydantic.

        Returns:
            Словарь с полями схемы или None при неудаче.
        """
        context_text = json.dumps(context, ensure_ascii=False, default=str)

        # Обрезка контекста при превышении лимита
        if len(context_text) > max_context_chars:
            logger.warning(
                "LLM %s context %d символов > %d, уменьшаем выборки",
                label, len(context_text), max_context_chars,
            )
            if "act_summaries" in context:
                context["act_summaries"] = context["act_summaries"][:5]
            if "incidents_sample" in context:
                context["incidents_sample"] = context["incidents_sample"][:10]
            if "relevant_legal_norms" in context:
                context["relevant_legal_norms"] = context["relevant_legal_norms"][:10]
            if "illustrative_cases" in context:
                context["illustrative_cases"] = context["illustrative_cases"][:3]
            context_text = json.dumps(context, ensure_ascii=False, default=str)

            # Вторичная проверка — если всё ещё превышает, усечение строки
            if len(context_text) > max_context_chars:
                logger.warning(
                    "LLM %s context всё ещё %d > %d после обрезки выборок, усекаем строку",
                    label, len(context_text), max_context_chars,
                )
                context_text = context_text[:max_context_chars]

        user_content = (
            f"Сгенерируй секцию «{label}» аналитического отчёта "
            "на основе следующих данных:\n\n" + context_text
        )

        logger.info(
            "LLM %s: отправляем %d символов контекста, max_tokens=%d",
            label, len(context_text), max_tokens,
        )

        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    temperature=0.3,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                )

                raw_content = response.choices[0].message.content or "{}"

                if response.choices[0].finish_reason == "length":
                    logger.warning(
                        "LLM %s: ответ обрезан (finish_reason=length), попытка %d/%d",
                        label, attempt, self.max_retries,
                    )
                    if attempt < self.max_retries:
                        await asyncio.sleep(get_retry_wait(attempt))
                        continue
                    # Последняя попытка — пробуем валидировать как есть

                # Валидация через Pydantic
                try:
                    result = schema.model_validate_json(raw_content)
                except Exception:
                    try:
                        raw_dict = json.loads(raw_content)
                        result = schema.model_validate(raw_dict)
                    except Exception:
                        if attempt < self.max_retries:
                            logger.warning(
                                "LLM %s: валидация не удалась, попытка %d/%d",
                                label, attempt, self.max_retries,
                            )
                            await asyncio.sleep(get_retry_wait(attempt))
                            continue
                        logger.error(
                            "LLM %s: валидация не удалась после %d попыток",
                            label, self.max_retries,
                        )
                        return None

                return result.model_dump()

            except _RETRYABLE_ERRORS as exc:
                wait = get_retry_wait(attempt, exc)
                cause = exc.__cause__ or exc
                if attempt < self.max_retries:
                    logger.warning(
                        "LLM %s попытка %d/%d не удалась (%s: %s | cause: %r), повтор через %.1fс",
                        label, attempt, self.max_retries,
                        type(exc).__name__, exc, cause, wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error(
                        "LLM %s не удался после %d попыток: %s | cause: %r",
                        label, self.max_retries, exc, cause,
                    )
                    raise LLMReportGenerationFailedException(
                        detail=f"{type(exc).__name__}: {exc}",
                    ) from exc

        return None

    async def generate_report(self, context: dict) -> dict:
        """Сгенерировать аналитический отчёт (монолитный, legacy)."""
        result = await self._call_llm(
            system_prompt=REPORT_SYSTEM_PROMPT,
            context=context,
            schema=AnalyticalReportLLMResponse,
            max_tokens=self.max_tokens,
            max_context_chars=MAX_CONTEXT_CHARS,
            label="report",
        )
        return result or {}

    async def generate_section(self, section_name: str, context: dict) -> dict:
        """Сгенерировать одну секцию аналитического отчёта."""
        if section_name not in _SECTION_CONFIG:
            raise LLMReportGenerationFailedException(
                detail=f"Неизвестная секция: {section_name}",
            )

        prompt, schema, max_tokens = _SECTION_CONFIG[section_name]
        max_context = _SECTION_MAX_CONTEXT.get(section_name, 20_000)

        result = await self._call_llm(
            system_prompt=prompt,
            context=context,
            schema=schema,
            max_tokens=max_tokens,
            max_context_chars=max_context,
            label=section_name,
        )
        return result or {}
