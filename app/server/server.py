from apps.enrollment.routes import router as enrollment_router
from apps.usage.routes import router as usage_router
from fastapi_mongo_base.core import app_factory

from . import config

app = app_factory.create_app(settings=config.Settings(), original_host_middleware=True)
app.include_router(enrollment_router, prefix=f"{config.Settings.base_path}")
app.include_router(usage_router, prefix=f"{config.Settings.base_path}")

# from fastapi.staticfiles import StaticFiles

# app.mount(
#     "/coverage", StaticFiles(directory=config.Settings.coverage_dir), name="coverage"
# )
