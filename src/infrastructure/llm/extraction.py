"""LLM-сервис извлечения структурированных данных из текста акта расследования."""
import asyncio
import json
import logging
from dataclasses import dataclass
import re

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    InternalServerError,
    RateLimitError,
)

from src.application.exceptions.llm import LLMExtractionFailedException
from src.application.interfaces.llm_extraction import BaseLLMExtractionService
from src.infrastructure.llm.extraction_schema import EnquiryActExtractionResult
from src.infrastructure.llm.utils import get_retry_wait

logger = logging.getLogger(__name__)

# Максимальная длина входного текста (символов)
MAX_INPUT_CHARS = 100_000

# ВНИМАНИЕ: JSON-схема в промпте и в extraction_schema.py должны быть синхронизированы.
# При добавлении/удалении полей — обновить оба места.
EXTRACTION_SYSTEM_PROMPT = """Ты — аналитик документов по охране труда и промышленной безопасности (Казахстан).
Тебе дан OCR-текст акта расследования несчастного случая на производстве.
Извлеки из него структурированные данные и верни СТРОГО в формате JSON.

СХЕМА JSON-ответа (все поля nullable — если данных нет, ставь null):
{
  "act_type": "Внутреннее расследование" | "Специальное расследование" | null,
  "act_date": "YYYY-MM-DD" | null,
  "act_number": "строка" | null,
  "language": "ru" | "kk" | null,

  "commission_chairman": "ФИО председателя комиссии" | null,
  "commission_members": ["ФИО1", "ФИО2"] | null,
  "investigation_period": "период расследования текстом" | null,

  "incident_date_from_act": "YYYY-MM-DD дата несчастного случая" | null,
  "victim_name_from_act": "ФИО пострадавшего как указано в акте (для авто-матчинга, может совпадать с victim_name)" | null,
  "company_name_from_act": "название предприятия (для матчинга)" | null,
  "region_from_act": "регион/область (для матчинга)" | null,

  "victim_name": "полное ФИО пострадавшего" | null,
  "victim_birth_date": "YYYY-MM-DD" | null,
  "victim_position": "должность" | null,
  "victim_experience": "стаж работы текстом" | null,
  "victim_training_dates": "даты инструктажей" | null,
  "injury_severity": "лёгкая" | "тяжёлая" | "смертельный исход" | null,
  "victim_dependents": "иждивенцы" | null,

  "company_name": "полное название организации" | null,
  "company_bin": "БИН/ИИН" | null,
  "workplace_description": "описание рабочего места" | null,

  "circumstances": "обстоятельства несчастного случая" | null,
  "root_causes": "основные причины" | null,
  "immediate_causes": "непосредственные причины" | null,
  "state_classifier_codes": ["код1", "код2"] | null,
  "investigation_method": "метод расследования" | null,

  "legal_violations": ["ссылка на НПА 1", "ссылка на НПА 2"] | null,

  "responsible_persons": [
    {"name": "ФИО", "position": "должность", "violation": "нарушение"}
  ] | null,

  "corrective_measures": [
    {"measure": "мероприятие", "deadline": "срок", "responsible": "ответственный"}
  ] | null,

  "work_related": true | false | null,
  "employer_fault_pct": 0-100 | null,
  "worker_fault_pct": 0-100 | null,
  "conclusions": "общие выводы комиссии" | null,

  "ai_summary": "краткое резюме документа (2-3 предложения)",
  "ai_risk_factors": ["фактор риска 1", "фактор риска 2"] | null,

  "cause_categories": ["категория причины"] | null,
  "violation_types": ["тип нарушения"] | null,
  "industry_tags": ["отрасль/сфера"] | null
}

ТАКСОНОМИЯ ТЕГОВ:
- cause_categories: "Организационные", "Технические", "Личностные", "Природные", "Нарушение ТБ", "Недостаточная квалификация", "Неисправность оборудования", "Нарушение технологии"
- violation_types: "Нарушение ПДД", "Нарушение правил ОТ", "Нарушение электробезопасности", "Нарушение пожарной безопасности", "Нарушение правил работы на высоте", "Нарушение правил эксплуатации оборудования", "Отсутствие инструктажа", "Отсутствие СИЗ"
- industry_tags: "Телекоммуникации", "Энергетика", "Строительство", "Транспорт", "Нефть и газ", "Горнодобыча", "Связь", "ИТ-инфраструктура"

ПРАВИЛА:
1. Не придумывай данных — если информация отсутствует в тексте, ставь null
2. Даты строго в формате YYYY-MM-DD
3. victim_name_from_act и victim_name могут совпадать — это нормально
4. company_name_from_act и company_name могут совпадать — это нормально
5. Документ может быть на русском или казахском — обрабатывай оба языка
6. Верни ТОЛЬКО JSON, без пояснений и комментариев"""


@dataclass
class LLMExtractionService(BaseLLMExtractionService):
    """Сервис извлечения структурированных данных из текста акта через LLM."""
    client: AsyncOpenAI
    model: str
    max_retries: int = 3
    max_tokens: int = 16384

    async def _stream_completion(self, kwargs: dict) -> tuple[str, str | None]:
        """Streaming-запрос к LLM. Возвращает (content, finish_reason)."""
        stream = await self.client.chat.completions.create(**kwargs, stream=True)
        chunks: list[str] = []
        finish_reason: str | None = None
        async for chunk in stream:
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            if choice.delta.content:
                chunks.append(choice.delta.content)
            if choice.finish_reason:
                finish_reason = choice.finish_reason
        return "".join(chunks) or "{}", finish_reason

    async def _sync_completion(self, kwargs: dict) -> tuple[str, str | None]:
        """Non-streaming запрос к LLM. Возвращает (content, finish_reason)."""
        response = await self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or "{}"
        return content, response.choices[0].finish_reason

    async def extract_structured_data(self, ocr_text: str) -> dict:
        """Извлечь структурированные данные из OCR-текста акта."""
        if not ocr_text or not ocr_text.strip():
            logger.warning("LLM extraction: пустой входной текст")
            return {}

        # Обрезка при превышении лимита
        if len(ocr_text) > MAX_INPUT_CHARS:
            logger.warning(
                "LLM extraction: текст обрезан с %d до %d символов",
                len(ocr_text), MAX_INPUT_CHARS,
            )
            ocr_text = ocr_text[:MAX_INPUT_CHARS]

        use_stream = True  # streaming по умолчанию, fallback на non-stream

        for attempt in range(1, self.max_retries + 1):
            try:
                request_kwargs = dict(
                    model=self.model,
                    temperature=0.0,
                    max_tokens=self.max_tokens,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": f"Извлеки данные из следующего текста акта расследования:\n\n{ocr_text}",
                        },
                    ],
                )

                if use_stream:
                    raw_content, finish_reason = await self._stream_completion(request_kwargs)
                else:
                    raw_content, finish_reason = await self._sync_completion(request_kwargs)

                # raw_content = re.sub(r'\n+', '', raw_content)
                logger.debug("LLM extraction raw response:\n%s", raw_content)

                if finish_reason == "length":
                    logger.warning("LLM extraction: ответ обрезан (finish_reason=length)")

                # Валидация через Pydantic
                try:
                    result = EnquiryActExtractionResult.model_validate_json(raw_content)
                except Exception as validation_exc:
                    logger.warning(
                        "LLM extraction: невалидный JSON, попытка частичной валидации: %s",
                        validation_exc,
                    )
                    # Частичная валидация: убираем поля, вызвавшие ошибки
                    try:
                        raw_dict = json.loads(raw_content)
                        # Извлекаем имена проблемных полей из ошибок Pydantic
                        from pydantic import ValidationError
                        if isinstance(validation_exc, ValidationError):
                            bad_fields = {
                                e["loc"][0]
                                for e in validation_exc.errors()
                                if e.get("loc")
                            }
                            for field_name in bad_fields:
                                raw_dict.pop(field_name, None)
                            logger.info(
                                "LLM extraction: убраны проблемные поля %s, повтор валидации",
                                bad_fields,
                            )
                        result = EnquiryActExtractionResult.model_validate(raw_dict)
                    except Exception:
                        logger.warning("LLM extraction: частичная валидация тоже не удалась")
                        return {}

                # Конвертация в dict, исключая None-значения
                return {
                    k: v for k, v in result.model_dump().items()
                    if v is not None
                }

            except (APIConnectionError, APITimeoutError, RateLimitError, InternalServerError) as exc:
                wait = get_retry_wait(attempt, exc)
                if attempt < self.max_retries:
                    logger.warning(
                        "LLM extraction попытка %d/%d не удалась (%s: %s), повтор через %.1fс",
                        attempt, self.max_retries, type(exc).__name__, exc, wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error(
                        "LLM extraction не удался после %d попыток: %s",
                        self.max_retries, exc,
                    )
                    raise LLMExtractionFailedException(
                        detail=f"{type(exc).__name__}: {exc}",
                    ) from exc
            except (APIConnectionError, APIStatusError) as exc:
                # Модель не поддерживает streaming — fallback на non-stream
                if use_stream:
                    logger.warning(
                        "LLM extraction: streaming не поддерживается (%s), fallback на non-stream",
                        exc,
                    )
                    use_stream = False
                    continue
                raise

        return {}
