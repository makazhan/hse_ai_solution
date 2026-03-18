from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class BaseOcrService(ABC):

    @abstractmethod
    async def extract_text_from_image(self, image_bytes: bytes) -> str:
        """Извлечь текст из изображения через OCR."""
        ...

    @abstractmethod
    async def extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """Извлечь текст из отсканированного PDF через OCR."""
        ...
