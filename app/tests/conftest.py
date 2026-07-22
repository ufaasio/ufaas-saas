"""Test fixtures and configuration."""

import asyncio
import logging
import os
from collections.abc import AsyncGenerator, Generator
from datetime import datetime, timedelta
from unittest import mock

os.environ.setdefault("PROJECT_NAME", "saas")
if not os.environ.get("API_KEY"):
    os.environ["API_KEY"] = "test-api-key"

import httpx
import pytest
import pytest_asyncio
from beanie import init_beanie
from fastapi_mongo_base import models as base_mongo_models
from fastapi_mongo_base.utils import usso_routes
from fastapi_mongo_base.utils.basic import get_all_subclasses
from usso import UserData
from usso.auth import UssoAuth

from apps.enrollment.models import Enrollment
from server.config import Settings
from server.server import app as fastapi_app
from tests.constants import StaticData

logger = logging.getLogger("tests.conftest")


@pytest.fixture(scope="session", autouse=True)
def setup_debugpy() -> None:
    """Set up debugpy for remote debugging."""
    if os.getenv("DEBUGPY", "False").lower() in ("true", "1", "yes"):
        import debugpy  # ruff:ignore[debugger]

        debugpy.listen(("127.0.0.1", 3020))  # ruff:ignore[debugger]
        logger.info("Waiting for debugpy client")
        debugpy.wait_for_client()  # ruff:ignore[debugger]


@pytest.fixture(scope="session", autouse=True)
def mock_usso() -> Generator[None]:
    """Mock USSO auth so tests do not call external HTTP services."""

    def mock_user_data(self: UssoAuth, api_key: str) -> UserData:
        return UserData(
            sub=StaticData.user_id_1_1,
            tenant_id=StaticData.tenant_id_1,
            scopes=["*:*"],
        )

    async def mock_get_user(
        self: usso_routes.AbstractUSSORouterBase,
        request: object,
        **kwargs: object,
    ) -> UserData:
        await asyncio.sleep(0)
        return UserData(
            sub=StaticData.user_id_1_1,
            tenant_id=StaticData.tenant_id_1,
            scopes=["*:*"],
        )

    patchers = [
        mock.patch.object(UssoAuth, "user_data_from_api_key", mock_user_data),
        mock.patch.object(
            usso_routes.AbstractUSSORouterBase,
            "get_user",
            mock_get_user,
        ),
    ]
    for patcher in patchers:
        patcher.start()
    yield
    for patcher in patchers:
        patcher.stop()


@pytest.fixture(scope="session")
def mongo_client() -> AsyncGenerator[object]:
    """Fixture providing a mock MongoDB client."""
    from mongomock_motor import AsyncMongoMockClient

    yield AsyncMongoMockClient()


async def init_db(mongo_client: object) -> None:
    """Initialize the database with Beanie."""
    database = mongo_client.get_database("test_db")
    original_list_collection_names = database.list_collection_names

    async def list_collection_names(*args: object, **kwargs: object) -> list[str]:
        # Beanie 2 / PyMongo pass kwargs mongomock_motor does not accept.
        kwargs.pop("authorizedCollections", None)
        kwargs.pop("nameOnly", None)
        return await original_list_collection_names(*args, **kwargs)

    database.list_collection_names = list_collection_names
    await init_beanie(
        database=database,
        document_models=get_all_subclasses(base_mongo_models.BaseEntity),
    )


@pytest_asyncio.fixture(scope="session", autouse=True)
async def db(mongo_client: object) -> AsyncGenerator[None]:
    """Fixture providing a test database."""
    Settings.config_logger()
    logger.info("Initializing database")
    await init_db(mongo_client)
    logger.info("Database initialized")
    yield
    logger.info("Cleaning up database")


@pytest_asyncio.fixture(scope="session")
async def client() -> AsyncGenerator[httpx.AsyncClient]:
    """Fixture to provide an AsyncClient for FastAPI app."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=fastapi_app),
        base_url=f"{Settings.root_url}{Settings.base_path}",
    ) as ac:
        yield ac


@pytest_asyncio.fixture(scope="session")
async def authenticated_client(
    client: httpx.AsyncClient,
) -> AsyncGenerator[httpx.AsyncClient]:
    """Fixture providing an authenticated HTTP client."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=fastapi_app),
        base_url=client.base_url,
        headers={"x-api-key": os.environ["API_KEY"]},
    ) as ac:
        yield ac


@pytest.fixture(scope="session")
def constants() -> StaticData:
    """Fixture providing static test data."""
    return StaticData()


@pytest.fixture(scope="module")
def enrollment_dicts() -> list[dict]:
    """Fixture providing enrollment test data."""
    now = datetime.now()

    enrollment_dicts = []
    enrollment_dicts.append({
        "expire_at": now + timedelta(seconds=2),
        "bundles": [{"asset": "image", "quota": 10}],
    })
    enrollment_dicts.append({
        "expire_at": None,
        "bundles": [{"asset": "image", "quota": 10}],
    })
    enrollment_dicts.append({
        "expire_at": now + timedelta(seconds=11),
        "bundles": [{"asset": "image", "quota": 10}],
        "variant": "variant",
    })
    enrollment_dicts.append({
        "expire_at": now + timedelta(seconds=1),
        "bundles": [{"asset": "image", "quota": 10}, {"asset": "text", "quota": 10}],
    })
    enrollment_dicts.append({
        "expire_at": now + timedelta(seconds=100),
        "bundles": [{"asset": "text", "quota": 10}],
    })
    return enrollment_dicts


def uid(i: int) -> str:
    """Generate a zero-padded UID string."""
    return f"{i:032}"


@pytest_asyncio.fixture(scope="module")
async def enrollments(
    constants: StaticData, enrollment_dicts: list[dict]
) -> AsyncGenerator[list[Enrollment]]:
    """Fixture providing enrollment test data."""
    from apps.enrollment.models import Enrollment

    now = datetime.now()

    try:
        enrollments = []
        for i, enrollment_dict in enumerate(enrollment_dicts):
            enrollment = await Enrollment.get_item(
                uid=uid(i + 1),
                tenant_id=constants.tenant_id_1,
                user_id=None,
                ignore_user_id=True,
            )
            if enrollment:
                await enrollment.delete()

            enrollment = Enrollment(
                uid=uid(i + 1),
                created_at=now - timedelta(seconds=2),
                tenant_id=constants.tenant_id_1,
                user_id=constants.user_id_1_1,
                status="active",
                price=0,
                **enrollment_dict,
            )
            await enrollment.save()
            enrollments.append(enrollment)
    except Exception:
        import traceback

        traceback_str = "".join(traceback.format_tb(
            __import__("sys").exc_info()[2]
        ))
        logger.exception("create base enrollments: \n%s", traceback_str)
    yield enrollments

    for enrollment in enrollments:
        await enrollment.delete()
