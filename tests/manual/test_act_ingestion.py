"""Ручной тест пайплайна загрузки актов расследования (OCR + LLM extraction).

НЕ является pytest-тестом — запускается напрямую через python:
    python tests/manual/test_act_ingestion.py INPUT_FILE [OPTIONS]

Pytest не подхватит этот файл, т.к. нет функций test_* / классов Test*.
"""
import argparse
import asyncio
import datetime
import json
import logging
import pathlib
import re
import sys

logger = logging.getLogger("act_ingestion_test")

# Паттерн для base64-данных в image_url (data:image/...;base64,AAAA...)
_B64_RE = re.compile(r'(data:image/[^;]+;base64,)[A-Za-z0-9+/=]{64,}')


def _redact(obj):
    """Рекурсивно вырезает base64 из строк, dict и коллекций."""
    if isinstance(obj, str):
        return _B64_RE.sub(r'\1<...redacted...>', obj)
    if isinstance(obj, dict):
        return {k: _redact(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return type(obj)(_redact(item) for item in obj)
    return obj


class _RedactBase64Filter(logging.Filter):
    """Вырезает base64-содержимое из логов (включая lazy %s args)."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.args:
            record.args = _redact(record.args)
        if isinstance(record.msg, str):
            record.msg = _B64_RE.sub(r'\1<...redacted...>', record.msg)
        return True


# ---------------------------------------------------------------------------
# JSON-сериализация для datetime
# ---------------------------------------------------------------------------

class _DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        return super().default(obj)


# ---------------------------------------------------------------------------
# Извлечение текста (повторяет логику UploadEnquiryActCommandHandler)
# ---------------------------------------------------------------------------

def _extract_text_from_pdf_native(data: bytes) -> str:
    """Извлечь текстовый слой из PDF (pymupdf)."""
    import pymupdf
    doc = pymupdf.open(stream=data, filetype="pdf")
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text


def _extract_text_from_docx(data: bytes) -> str:
    """Извлечь текст из DOCX (python-docx)."""
    from io import BytesIO
    from docx import Document
    doc = Document(BytesIO(data))
    return "\n".join(para.text for para in doc.paragraphs)


# ---------------------------------------------------------------------------
# Создание сервисов (повторяет containers.py без DI)
# ---------------------------------------------------------------------------

def _create_ocr_service(config):
    from openai import AsyncOpenAI, Timeout as OpenAITimeout
    from src.infrastructure.llm.ocr import QwenOcrService, OCR_SYSTEM_PROMPT, OCR_USER_PROMPT

    client = AsyncOpenAI(
        api_key=config.OPENAI_API_KEY,
        base_url=config.OPENAI_BASE_URL,
        max_retries=0,
        timeout=OpenAITimeout(config.OCR_TIMEOUT, connect=config.OCR_CONNECT_TIMEOUT),
    )
    return QwenOcrService(
        client=client,
        model=config.OCR_MODEL,
        system_prompt=OCR_SYSTEM_PROMPT,
        user_prompt=OCR_USER_PROMPT,
        dpi=config.OCR_DPI,
        max_image_kb=config.OCR_MAX_IMAGE_KB,
        concurrency=config.OCR_CONCURRENCY,
        max_retries=config.OCR_MAX_RETRIES,
        max_tokens=config.OCR_MAX_TOKENS,
    )


def _create_extraction_service(config):
    from openai import AsyncOpenAI, Timeout as OpenAITimeout
    from src.infrastructure.llm.extraction import LLMExtractionService

    client = AsyncOpenAI(
        api_key=config.OPENAI_API_KEY,
        base_url=config.OPENAI_BASE_URL,
        max_retries=0,
        timeout=OpenAITimeout(
            config.LLM_EXTRACTION_TIMEOUT,
            connect=config.LLM_EXTRACTION_CONNECT_TIMEOUT,
        ),
    )
    return LLMExtractionService(
        client=client,
        model=config.OPENAI_MODEL,
        max_retries=config.LLM_EXTRACTION_MAX_RETRIES,
        max_tokens=config.LLM_EXTRACTION_MAX_TOKENS,
    )


# ---------------------------------------------------------------------------
# Основной пайплайн
# ---------------------------------------------------------------------------

async def run(args: argparse.Namespace) -> None:
    input_path = pathlib.Path(args.input_file).resolve()
    if not input_path.is_file():
        logger.error("Файл не найден: %s", input_path)
        sys.exit(1)

    ext = input_path.suffix.lower()
    if ext not in (".pdf", ".docx"):
        logger.error("Неподдерживаемый формат: %s (ожидается .pdf или .docx)", ext)
        sys.exit(1)

    # Пути промежуточного представления и результата
    md_path = input_path.with_suffix(input_path.suffix + ".md")
    output_path = pathlib.Path(args.output).resolve() if args.output else input_path.with_suffix(".json")

    logger.info("Входной файл : %s", input_path)
    logger.info("Markdown кэш : %s", md_path)
    logger.info("Результат    : %s", output_path)

    file_data = input_path.read_bytes()
    logger.info("Размер файла : %d КБ", len(file_data) // 1024)

    # --- Загрузка конфига ---
    from dotenv import load_dotenv
    load_dotenv(args.env_file, override=True)

    from src.settings.config import Config
    config = Config()

    if not config.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY не задан (проверьте %s)", args.env_file)
        sys.exit(1)

    # --- Извлечение текста ---
    ocr_used = False
    ocr_reused = False
    extracted_text = ""

    if ext == ".pdf":
        logger.info("Извлечение текстового слоя из PDF...")
        extracted_text = await asyncio.to_thread(_extract_text_from_pdf_native, file_data)

        if extracted_text.strip():
            logger.info(
                "Текстовый слой найден (%d символов), OCR не требуется", len(extracted_text),
            )
            # Сохраняем нативный текст как .md для инспекции
            md_path.write_text(extracted_text, encoding="utf-8")
            logger.info("Текст сохранён в %s", md_path)
        else:
            logger.info("Текстовый слой пуст — требуется OCR")

            # Проверяем кэш
            if args.reuse and md_path.is_file():
                logger.info("Флаг -r: используем кэшированный markdown из %s", md_path)
                extracted_text = md_path.read_text(encoding="utf-8")
                ocr_used = True
                ocr_reused = True
            else:
                logger.info("Запуск OCR (модель: %s)...", config.OCR_MODEL)
                ocr_service = _create_ocr_service(config)
                extracted_text = await ocr_service.extract_text_from_pdf(file_data)
                ocr_used = True

                # Сохраняем промежуточное представление
                md_path.write_text(extracted_text, encoding="utf-8")
                logger.info("OCR markdown сохранён в %s (%d символов)", md_path, len(extracted_text))

    elif ext == ".docx":
        logger.info("Извлечение текста из DOCX...")
        extracted_text = await asyncio.to_thread(_extract_text_from_docx, file_data)
        logger.info("Извлечено %d символов из DOCX", len(extracted_text))

        # Сохраняем для инспекции
        md_path.write_text(extracted_text, encoding="utf-8")
        logger.info("Текст сохранён в %s", md_path)

    if not extracted_text.strip():
        logger.error("Текст пуст после извлечения — невозможно продолжить")
        sys.exit(1)

    # --- LLM Extraction ---
    logger.info("Запуск LLM extraction (модель: %s)...", config.OPENAI_MODEL)
    extraction_service = _create_extraction_service(config)
    extracted_fields = await extraction_service.extract_structured_data(extracted_text)
    logger.info("LLM extraction: извлечено %d полей", len(extracted_fields))

    # --- Формирование результата ---
    result = {
        "input_file": str(input_path),
        "extracted_text_length": len(extracted_text),
        "ocr_used": ocr_used,
        "ocr_reused_from_cache": ocr_reused,
        "intermediate_md_path": str(md_path),
        "extracted_fields": extracted_fields,
    }

    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, cls=_DateEncoder),
        encoding="utf-8",
    )
    logger.info("Результат записан в %s", output_path)

    # --- Сводка ---
    print("\n" + "=" * 60)
    print(f"  Файл         : {input_path.name}")
    print(f"  Размер текста: {len(extracted_text)} символов")
    print(f"  OCR          : {'да' if ocr_used else 'нет'}"
          + (f" (из кэша)" if ocr_reused else ""))
    print(f"  Полей        : {len(extracted_fields)}")
    print(f"  Результат    : {output_path}")
    print("=" * 60)

    # Ключевые поля для быстрой проверки
    key_fields = [
        "region_from_act", "victim_name_from_act", "company_name_from_act",
        "incident_date_from_act", "injury_severity", "ai_summary",
    ]
    found = {k: extracted_fields[k] for k in key_fields if k in extracted_fields}
    if found:
        print("\nКлючевые поля:")
        for k, v in found.items():
            val = v if len(str(v)) <= 80 else str(v)[:77] + "..."
            print(f"  {k}: {val}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ручной тест пайплайна загрузки актов (OCR + LLM extraction)",
    )
    parser.add_argument(
        "input_file",
        help="Путь к PDF или DOCX файлу акта расследования",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Путь для сохранения результата JSON (по умолчанию: INPUT_FILE.json)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Подробное логирование (DEBUG)",
    )
    parser.add_argument(
        "-r", "--reuse",
        action="store_true",
        help="Переиспользовать кэшированный .md (пропустить OCR, если файл уже есть)",
    )
    parser.add_argument(
        "--env-file",
        default="dev/.env",
        help="Путь к .env файлу (по умолчанию: dev/.env)",
    )
    return parser.parse_args()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    args = _parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)-5s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # Фильтр base64 из логов OpenAI SDK (image_url payload)
    for handler in logging.root.handlers:
        handler.addFilter(_RedactBase64Filter())

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
