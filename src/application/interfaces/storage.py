from abc import ABC, abstractmethod


class BaseFileStorage(ABC):
    """Интерфейс объектного хранилища (S3 / MinIO)."""

    @abstractmethod
    async def upload(self, key: str, data: bytes, content_type: str) -> str:
        """Загрузить файл. Возвращает ключ."""
        ...

    @abstractmethod
    async def download(self, key: str) -> bytes:
        """Скачать файл по ключу."""
        ...

    @abstractmethod
    async def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Сгенерировать временную ссылку на скачивание."""
        ...
