import logging
from contextlib import asynccontextmanager

import fastapi
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mongo_base.core import db, exceptions
from ufaas_fastapi_business.core import middlewares
from usso.fastapi.integration import EXCEPTION_HANDLERS as USSO_EXCEPTION_HANDLERS

from . import config


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):  # type: ignore
    """Initialize application services."""
    await db.init_mongo_db()
    config.Settings().config_logger()

    logging.info("Startup complete")
    yield
    logging.info("Shutdown complete")


app = fastapi.FastAPI(
    title=config.Settings.project_name.replace("-", " ").title(),
    # description=DESCRIPTION,
    version="0.1.0",
    contact={
        "name": "Mahdi Kiani",
        "url": "https://github.com/ufaasio/ufaas-saas",
        "email": "mahdikiany@gmail.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://github.com/ufaasio/ufaas-saas/blob/main/LICENSE",
    },
    openapi_url=f"{config.Settings.base_path}/openapi.json",
    docs_url=f"{config.Settings.base_path}/docs",
    redoc_url=f"{config.Settings.base_path}/redoc",
    lifespan=lifespan,
)

for exc_class, handler in (
    exceptions.EXCEPTION_HANDLERS | USSO_EXCEPTION_HANDLERS
).items():
    app.exception_handler(exc_class)(handler)

origins = [
    "http://localhost:8000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(middlewares.OriginalHostMiddleware)


from apps.enrollment.routes import router as enrollment_router
from apps.usage.routes import router as usage_router

app.include_router(enrollment_router, prefix=f"{config.Settings.base_path}")
app.include_router(usage_router, prefix=f"{config.Settings.base_path}")

from fastapi.staticfiles import StaticFiles

app.mount(
    "/coverage", StaticFiles(directory=config.Settings.coverage_dir), name="coverage"
)


@app.get(f"{config.Settings.base_path}/health")
async def health(request: fastapi.Request):
    request.headers.get("x-original-host", "!not found!")
    request.headers.get("X-Forwarded-Host", "forwarded_host")
    request.headers.get("X-Forwarded-Proto", "forwarded_proto")
    request.headers.get("X-Forwarded-For", "forwarded_for")

    return {
        "status": "up",
        # "host": request.url.hostname,
        # "host2": request.base_url.hostname,
        # "original_host": original_host,
        # "forwarded_host": forwarded_host,
        # "forwarded_proto": forwarded_proto,
        # "forwarded_for": forwarded_for,
    }


@app.get(f"{config.Settings.base_path}/logs", include_in_schema=False)
async def logs():
    from collections import deque

    with open(config.Settings.base_dir / "logs" / "info.log", "rb") as f:
        last_100_lines = deque(f, maxlen=100)

    return [line.decode("utf-8") for line in last_100_lines]
