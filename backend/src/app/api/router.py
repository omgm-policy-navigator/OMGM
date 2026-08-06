from fastapi import APIRouter

from app.api.admin import router as admin_router
from app.api.health import router as health_router
from app.catalog.api import router as catalog_router
from app.modules.ai.api import router as ai_router
from app.modules.sessions.api import router as session_router

api_router = APIRouter()
api_router.include_router(admin_router)
api_router.include_router(health_router)
api_router.include_router(ai_router)
api_router.include_router(catalog_router)
api_router.include_router(session_router)
