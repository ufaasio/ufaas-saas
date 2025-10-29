"""FastAPI server configuration."""

import dataclasses
import os
from pathlib import Path

import dotenv
from fastapi_mongo_base.core import config

dotenv.load_dotenv()


@dataclasses.dataclass
class Settings(config.Settings):
    project_name: str = os.getenv("PROJECT_NAME")
    base_dir: Path = Path(__file__).resolve().parent.parent
    base_path: str = "/api/saas/v1"

    redis_uri: str = os.getenv("REDIS_URI", default="redis://redis:6379")
    usso_base_url: str = os.getenv("USSO_BASE_URL", default="https://usso.uln.me")
    accounting_service_url: str = os.getenv(
        "ACCOUNTING_SERVICE_URL", default="https://wallets.uln.me"
    )

    @classmethod
    def get_log_config(cls, console_level: str = "INFO", **kwargs: object) -> dict:
        log_config = {
            "formatters": {
                "standard": {
                    "format": "[{levelname} {name} : {filename}:{lineno} : {asctime} -> {funcName:10}] {message}",  # noqa: E501
                    "style": "{",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": console_level,
                    "formatter": "standard",
                },
                "file": {
                    "class": "logging.FileHandler",
                    "level": "INFO",
                    "formatter": "standard",
                    "filename": "logs/app.log",
                },
            },
            "loggers": {
                "": {
                    "handlers": [
                        "console",
                        "file",
                    ],
                    "level": console_level,
                    "propagate": True,
                },
            },
            "version": 1,
        }
        return log_config
