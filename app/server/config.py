"""FastAPI server configuration."""

import os
from pathlib import Path

import dotenv
from ufaas_fastapi_business.core.config import Settings as BaseSettings

dotenv.load_dotenv()


class Settings(BaseSettings):
    """Server config settings."""

    base_dir: Path = Path(__file__).resolve().parent.parent
    base_path: str = "/api/v1/apps/saas"
    coverage_dir: Path = base_dir / "htmlcov"
    currency: str = "IRR"

    app_id: str = os.getenv("APP_ID")
    app_secret: str = os.getenv("APP_SECRET")
    app_scopes: str = os.getenv("APP_SCOPES", default="[]")
    app_auth_expiry: int = 60  # 1 minute
    business_domains_url = (
        os.getenv(
            "UFAAS_BUSINESS_DOMAINS_URL",
            "https://business.ufaas.io/api/v1/apps/business",
        )
        + "/businesses/"
    )
