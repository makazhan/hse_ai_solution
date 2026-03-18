"""Общие утилиты для LLM-сервисов."""
from openai import RateLimitError


def get_retry_wait(attempt: int, exc=None) -> float:
    """Экспоненциальный backoff с учётом Retry-After."""
    if isinstance(exc, RateLimitError) and exc.response:
        retry_after = exc.response.headers.get("retry-after")
        if retry_after:
            try:
                return min(float(retry_after), 120.0)
            except ValueError:
                pass
    return min(2 ** attempt, 60.0)
