from fastapi import APIRouter

from src.presentation.api.v1.incidents.handlers import router as incidents_router
from src.presentation.api.v1.analytics.handlers import router as analytics_router
from src.presentation.api.v1.acts.handlers import router as acts_router
from src.presentation.api.v1.files.handlers import router as files_router


router = APIRouter(prefix='/v1')

router.include_router(incidents_router)
router.include_router(analytics_router)
router.include_router(acts_router)
router.include_router(files_router)
