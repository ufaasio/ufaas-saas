import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi_mongo_base.core import app_factory

from apps.enrollment.routes import router as enrollment_router
from apps.usage.routes import router as usage_router

from . import config


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:  # noqa: RUF029
    """Initialize application services."""
    # await db.init_mongo_db()
    logging.info("Startup complete")
    yield
    logging.info("Shutdown complete")


app = app_factory.create_app(
    settings=config.Settings()  # ,  lifespan_func=lifespan,
)
server_router = APIRouter()

for router in [
    enrollment_router,
    usage_router,
]:
    server_router.include_router(router)

app.include_router(server_router, prefix=config.Settings.base_path)
