"""FastAPI application setup."""

from fastapi import APIRouter
from fastapi_mongo_base.core import app_factory

from apps.enrollment.routes import router as enrollment_router
from apps.usage.routes import router as usage_router

from . import config

app = app_factory.create_app(
    settings=config.Settings()
)
server_router = APIRouter()

for router in [enrollment_router, usage_router]:
    server_router.include_router(router)

app.include_router(server_router, prefix=config.Settings.base_path)
