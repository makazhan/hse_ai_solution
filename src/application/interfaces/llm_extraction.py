from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class BaseLLMExtractionService(ABC):

    @abstractmethod
    async def extract_structured_data(self, ocr_text: str) -> dict:
        """Извлечь структурированные данные из OCR-текста акта расследования."""
        ...
