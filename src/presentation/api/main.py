import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import (
    APIRouter,
    FastAPI,
)
from fastapi.requests import Request
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.staticfiles import StaticFiles

from src.application.exceptions.base import ApplicationException, NotFoundException

from src.infrastructure.di.containers import init_container
from src.presentation.api.schemas import PingResponseSchema
from src.presentation.api.v1.routers import router as router_v1
from src.settings.config import Config

logger = logging.getLogger(__name__)

health_check_router = APIRouter(tags=['HealthChecks'])

container = init_container()
config: Config = container.resolve(Config)


@health_check_router.get('/health-ams')
async def health_ams() -> PingResponseSchema:
    return PingResponseSchema(status="healthy")


@health_check_router.get('/health')
async def health() -> PingResponseSchema:
    return PingResponseSchema(status="healthy")


@health_check_router.get('/readiness')
async def readiness() -> PingResponseSchema:
    return PingResponseSchema(status="ready")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app() -> FastAPI:
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )
    # Аутентификация: внешняя сессионная (X-Session-ID), управляется AUTH_ENABLED.
    # См. docs/plan-auth.md
    app = FastAPI(
        title='TB-Expert API',
        debug=config.debug,
        root_path=config.ROOT_PATH,
        version='1.00',
        lifespan=lifespan,
    )

    # Глобальный обработчик кастомных исключений
    @app.exception_handler(ApplicationException)
    async def application_exception_handler(request: Request, exc: ApplicationException):
        status_code = 404 if isinstance(exc, NotFoundException) else 400
        return JSONResponse(status_code=status_code, content={"error": exc.message})

    # Middleware для логирования запросов
    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:16])
        start = time.monotonic()
        response: Response = await call_next(request)
        elapsed_ms = (time.monotonic() - start) * 1000
        logger.info(
            "%s %s %s → %d (%.0f ms)",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        response.headers["X-Request-ID"] = request_id
        return response

    app.include_router(health_check_router)
    app.include_router(router_v1)
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://([a-z0-9-]+\.)*sk-ai\.kz$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Отключаемый дашборд — удаление static/ ничего не ломает
    static_dir = Path(__file__).parents[3] / "static"
    if static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

        @app.get("/demo")
        async def demo_page():
            return FileResponse(static_dir / "index.html")

    return app
