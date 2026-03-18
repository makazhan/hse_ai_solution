import asyncio
import base64
import logging
from dataclasses import dataclass

import pymupdf
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    InternalServerError,
    RateLimitError,
)

from src.application.interfaces.ocr import BaseOcrService

logger = logging.getLogger(__name__)

OCR_SYSTEM_PROMPT = (
    "You are a document OCR assistant. Extract ALL text from the provided page image "
    "and reproduce it as clean Markdown. Preserve the document structure: headings "
    "(using # levels), paragraphs, bullet/numbered lists, and tables (using Markdown "
    "table syntax). Do NOT describe the image or add commentary. Do NOT wrap the output "
    "in a code fence. Output ONLY the extracted Markdown text. "
    "The document may be in Russian or Kazakh with occasional English words and phrases "
    "— preserve the original language exactly."
)

OCR_USER_PROMPT = "Extract all text from this document page ({page_num}/{total_pages})."


@dataclass
class QwenOcrService(BaseOcrService):
    client: AsyncOpenAI
    model: str
    system_prompt: str
    user_prompt: str
    dpi: int = 150
    max_image_kb: int = 500
    concurrency: int = 4
    max_retries: int = 3
    max_tokens: int = 16384

    @staticmethod
    def _render_page_to_jpeg(page: pymupdf.Page, dpi: int = 150, max_kb: int = 500) -> bytes:
        """Рендер страницы PDF в grayscale JPEG с ограничением размера."""
        pixmap = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY, alpha=False)
        quality = 85
        while quality >= 40:
            data = pixmap.tobytes("jpeg", jpg_quality=quality)
            if len(data) / 1024 <= max_kb:
                return data
            quality -= 10
        return data

    @staticmethod
    def _get_retry_wait(attempt: int, exc=None) -> float:
        """Экспоненциальный backoff с учётом Retry-After."""
        if isinstance(exc, RateLimitError) and exc.response:
            retry_after = exc.response.headers.get("retry-after")
            if retry_after:
                try:
                    return min(float(retry_after), 120.0)
                except ValueError:
                    pass
        return min(2 ** attempt, 60.0)

    async def _ocr_image(self, image_bytes: bytes, user_prompt: str) -> str:
        """Отправка изображения в vision-модель с retry."""
        mime_type = "image/jpeg" if image_bytes[:2] == b'\xff\xd8' else "image/png"
        b64_image = base64.b64encode(image_bytes).decode("ascii")
        use_stream = True

        for attempt in range(1, self.max_retries + 1):
            try:
                request_kwargs = dict(
                    model=self.model,
                    temperature=0.0,
                    max_tokens=self.max_tokens,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{mime_type};base64,{b64_image}",
                                    },
                                },
                                {
                                    "type": "text",
                                    "text": user_prompt,
                                },
                            ],
                        },
                    ],
                )

                if use_stream:
                    stream = await self.client.chat.completions.create(**request_kwargs, stream=True)
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
                    content = "".join(chunks)
                else:
                    response = await self.client.chat.completions.create(**request_kwargs)
                    content = response.choices[0].message.content or ""
                    finish_reason = response.choices[0].finish_reason

                if finish_reason == "length":
                    logger.warning("OCR: ответ обрезан (finish_reason=length)")

                return content

            except (APIConnectionError, APITimeoutError, RateLimitError, InternalServerError) as exc:
                wait = self._get_retry_wait(attempt, exc)
                if attempt < self.max_retries:
                    logger.warning(
                        "OCR попытка %d/%d не удалась (%s), повтор через %.1fс",
                        attempt, self.max_retries, type(exc).__name__, wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error(
                        "OCR не удался после %d попыток: %s", self.max_retries, exc,
                    )
                    raise
            except APIStatusError as exc:
                # Модель не поддерживает streaming — fallback на non-stream
                if use_stream:
                    logger.warning(
                        "OCR: streaming не поддерживается (%s), fallback на non-stream",
                        exc,
                    )
                    use_stream = False
                    continue
                raise

        return ""

    async def extract_text_from_image(self, image_bytes: bytes) -> str:
        """Извлечь текст из одного изображения."""
        return await self._ocr_image(image_bytes, self.user_prompt)

    async def extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """Извлечь текст из всех страниц PDF с конкурентной обработкой."""
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        total_pages = len(doc)
        logger.info(
            "OCR: старт для PDF, %d стр. (dpi=%d, concurrency=%d)",
            total_pages, self.dpi, self.concurrency,
        )

        # CPU-bound рендеринг — выносим в поток, чтобы не блокировать event loop
        def _render_all() -> list[bytes]:
            return [
                self._render_page_to_jpeg(doc.load_page(i), dpi=self.dpi, max_kb=self.max_image_kb)
                for i in range(total_pages)
            ]

        page_images = await asyncio.to_thread(_render_all)
        doc.close()

        for i, img in enumerate(page_images, 1):
            logger.debug(
                "Стр. %d/%d: %d КБ JPEG", i, total_pages, len(img) // 1024,
            )

        sem = asyncio.Semaphore(self.concurrency)
        page_results: dict[int, str] = {}

        async def extract_one(page_num: int) -> None:
            async with sem:
                prompt = self.user_prompt.format(
                    page_num=page_num, total_pages=total_pages,
                )
                try:
                    text = await self._ocr_image(page_images[page_num - 1], prompt)
                    page_results[page_num] = text
                    logger.info("Стр. %d/%d OK", page_num, total_pages)
                except Exception as exc:
                    logger.error(
                        "Стр. %d/%d: ошибка извлечения: %s", page_num, total_pages, exc,
                    )
                    page_results[page_num] = f"<!-- Page {page_num}: extraction failed -->"

        tasks = [extract_one(i) for i in range(1, total_pages + 1)]
        await asyncio.gather(*tasks)

        text_parts = [
            page_results[i] for i in range(1, total_pages + 1)
            if page_results[i].strip() and "extraction failed" not in page_results[i]
        ]

        failed_count = sum(
            1 for i in range(1, total_pages + 1)
            if "extraction failed" in page_results.get(i, "")
        )
        if failed_count:
            logger.warning(
                "OCR PDF завершён с %d/%d неудачных страниц", failed_count, total_pages,
            )
        else:
            logger.info("OCR PDF завершён успешно для всех %d страниц", total_pages)

        return "\n\n".join(text_parts)
