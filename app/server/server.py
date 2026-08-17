"""FastAPI application factory."""

import tomllib
from pathlib import Path

from fastapi import APIRouter
from fastapi_mongo_base.core import app_factory

from apps.enrollment.routes import router as enrollment_router
from apps.usage.routes import router as usage_router

from . import config

_PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"
with _PYPROJECT.open("rb") as _pyproject:
    _APP_VERSION = tomllib.load(_pyproject)["project"]["version"]

app = app_factory.create_app(
    settings=config.Settings(),  # ,  lifespan_func=lifespan,
    version=_APP_VERSION,
)
server_router = APIRouter()

for router in [enrollment_router, usage_router]:
    server_router.include_router(router)

app.include_router(server_router, prefix=config.Settings.base_path)
