from pathlib import PurePosixPath

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from punq import Container

from src.application.commands.files import UploadFileCommand
from src.application.interfaces.storage import BaseFileStorage
from src.application.mediator.base import Mediator
from src.domain.entities.users import UserEntity
from src.infrastructure.di.containers import init_container
from src.presentation.api.v1.auth import get_current_user
from src.presentation.api.v1.files.schemas import UploadedFileResponseSchema
from src.settings.config import MAX_UPLOAD_SIZE

# Допустимые MIME-типы для загрузки
ALLOWED_CONTENT_TYPES = {
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
    'application/vnd.ms-excel',  # .xls
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
    'application/octet-stream',  # разрешаем для случаев, когда браузер не определил тип
}

# Допустимые расширения — дополнительная проверка при octet-stream
ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.xls', '.xlsx'}

router = APIRouter(prefix='/files', tags=['files'])


@router.post('/upload', response_model=UploadedFileResponseSchema,
             status_code=status.HTTP_201_CREATED)
async def upload_file_handler(
    file: UploadFile = File(...),
    _user: UserEntity = Depends(get_current_user),
    container: Container = Depends(init_container),
) -> UploadedFileResponseSchema:
    """Загрузка одного файла → S3 + БД. Возвращает file_id и presigned_url."""
    mediator: Mediator = container.resolve(Mediator)
    file_storage: BaseFileStorage = container.resolve(BaseFileStorage)

    content_type = file.content_type or 'application/octet-stream'
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f'Недопустимый тип файла: {content_type}. '
                   f'Допустимые: PDF, DOCX, XLS, XLSX',
        )

    # Дополнительная валидация расширения — защита от обхода через octet-stream
    ext = PurePosixPath(file.filename or '').suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f'Недопустимое расширение файла: {ext or "(нет)"}. '
                   f'Допустимые: {", ".join(sorted(ALLOWED_EXTENSIONS))}',
        )

    file_content = await file.read()
    if len(file_content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail='Файл превышает допустимый размер (50 МБ)',
        )

    command = UploadFileCommand(
        file_content=file_content,
        filename=file.filename or 'unknown',
        content_type=content_type,
    )

    uploaded_file, *_ = await mediator.handle_command(command)

    presigned_url = await file_storage.generate_presigned_url(uploaded_file.s3_key)

    return UploadedFileResponseSchema.from_entity(uploaded_file, presigned_url)
