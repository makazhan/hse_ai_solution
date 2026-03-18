import logging
from dataclasses import dataclass, field
from typing import Optional

from aiobotocore.session import AioSession

from src.application.interfaces.storage import BaseFileStorage
from src.settings.config import Config

logger = logging.getLogger(__name__)


@dataclass
class S3FileStorage(BaseFileStorage):
    """Async S3-клиент на базе aiobotocore с переиспользованием соединения."""
    _config: Config
    _session: AioSession
    _client_ctx: Optional[object] = field(default=None, init=False, repr=False)
    _client: Optional[object] = field(default=None, init=False, repr=False)
    _bucket_ensured: bool = field(default=False, init=False, repr=False)

    async def _get_client(self):
        """Возвращает переиспользуемый S3-клиент (создаёт при первом вызове)."""
        if self._client is None:
            endpoint = self._config.S3_ENDPOINT_URL
            if endpoint and not endpoint.startswith(('http://', 'https://')):
                endpoint = f'https://{endpoint}'
            self._client_ctx = self._session.create_client(
                's3',
                endpoint_url=endpoint,
                aws_access_key_id=self._config.S3_ACCESS_KEY,
                aws_secret_access_key=self._config.S3_SECRET_KEY,
                region_name=self._config.S3_REGION,
            )
            self._client = await self._client_ctx.__aenter__()
        return self._client

    async def _ensure_bucket(self):
        """Проверяет бакет при первом обращении; пытается создать если 404."""
        if self._bucket_ensured:
            return
        client = await self._get_client()
        bucket = self._config.S3_BUCKET_NAME
        try:
            await client.head_bucket(Bucket=bucket)
        except client.exceptions.ClientError as exc:
            error_code = int(exc.response.get('Error', {}).get('Code', 0) or
                             exc.response.get('ResponseMetadata', {}).get('HTTPStatusCode', 0))
            if error_code == 404:
                logger.info("Бакет %s не найден — создаём", bucket)
                await client.create_bucket(Bucket=bucket)
            else:
                # 403 (нет прав на head) или другие — предполагаем бакет существует
                logger.warning(
                    "head_bucket(%s) вернул %s — предполагаем бакет существует",
                    bucket, error_code,
                )
        self._bucket_ensured = True

    async def upload(self, key: str, data: bytes, content_type: str) -> str:
        await self._ensure_bucket()
        client = await self._get_client()
        await client.put_object(
            Bucket=self._config.S3_BUCKET_NAME,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return key

    async def download(self, key: str) -> bytes:
        client = await self._get_client()
        resp = await client.get_object(
            Bucket=self._config.S3_BUCKET_NAME,
            Key=key,
        )
        return await resp['Body'].read()

    async def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        client = await self._get_client()
        return await client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self._config.S3_BUCKET_NAME, 'Key': key},
            ExpiresIn=expires_in,
        )

    async def close(self):
        """Закрывает S3-клиент. Вызывается при остановке приложения."""
        if self._client_ctx is not None:
            await self._client_ctx.__aexit__(None, None, None)
            self._client = None
            self._client_ctx = None
