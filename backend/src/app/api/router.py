from fastapi import APIRouter

from app.api.health import router as health_router
from app.catalog.api import router as catalog_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(catalog_router)
