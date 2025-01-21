import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import AsyncGenerator

import debugpy
import httpx
import pytest
import pytest_asyncio
from beanie import init_beanie
from fastapi_mongo_base import models as base_mongo_models
from fastapi_mongo_base.utils.basic import get_all_subclasses
from ufaas_fastapi_business.models import Business
from usso.session import UssoSession

from server.config import Settings
from server.server import app as fastapi_app
from tests.constants import StaticData


@pytest.fixture(scope="session", autouse=True)
def setup_debugpy():
    if os.getenv("DEBUGPY", "False").lower() in ("true", "1", "yes"):
        debugpy.listen(("0.0.0.0", 3020))
        debugpy.wait_for_client()


@pytest.fixture(scope="session")
def mongo_client():
    from mongomock_motor import AsyncMongoMockClient

    mongo_client = AsyncMongoMockClient()
    yield mongo_client

    # from testcontainers.mongodb import MongoDbContainer
    # from motor.motor_asyncio import AsyncIOMotorClient
    # mongo = MongoDbContainer("mongo:latest")
    # mongo.start()
    # mongo_uri = mongo.get_connection_url()
    # mongo_client = AsyncIOMotorClient(mongo_uri)
    # yield mongo_client
    # mongo.stop()

    # with MongoDbContainer("mongo:latest") as mongo:
    #     mongo_uri = mongo.get_connection_url()
    #     mongo_client = AsyncIOMotorClient(mongo_uri)
    #     yield mongo_client


# Async setup function to initialize the database with Beanie
async def init_db(mongo_client):
    database = mongo_client.get_database("test_db")
    await init_beanie(
        database=database,
        document_models=get_all_subclasses(base_mongo_models.BaseEntity),
    )


@pytest_asyncio.fixture(scope="session", autouse=True)
async def db(mongo_client):
    Settings.config_logger()
    logging.info("Initializing database")
    await init_db(mongo_client)
    logging.info("Database initialized")
    yield
    logging.info("Cleaning up database")


@pytest_asyncio.fixture(scope="session")
async def client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Fixture to provide an AsyncClient for FastAPI app."""

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=fastapi_app),
        base_url="http://test.ufaas.io",
    ) as ac:
        yield ac


@pytest.fixture(scope="session")
def constants():
    return StaticData()


@pytest.fixture(scope="module")
def enrollment_dicts():
    now = datetime.now()

    enrollment_dicts = []
    enrollment_dicts.append(
        dict(
            expire_at=now + timedelta(seconds=2),
            bundles=[dict(asset="image", quota=10)],
        )
    )
    enrollment_dicts.append(
        dict(expire_at=None, bundles=[dict(asset="image", quota=10)])
    )
    enrollment_dicts.append(
        dict(
            expire_at=now + timedelta(seconds=11),
            bundles=[dict(asset="image", quota=10)],
            variant="variant",
        )
    )
    enrollment_dicts.append(
        dict(
            expire_at=now + timedelta(seconds=1),
            bundles=[dict(asset="image", quota=10), dict(asset="text", quota=10)],
        )
    )
    enrollment_dicts.append(
        dict(
            expire_at=now + timedelta(seconds=100),
            bundles=[dict(asset="text", quota=10)],
        )
    )
    return enrollment_dicts


@pytest_asyncio.fixture(scope="module")
async def enrollments(constants: StaticData, enrollment_dicts):
    from apps.enrollment.models import Enrollment

    uid = lambda i: uuid.UUID(f"{i:032}")

    now = datetime.now()

    try:
        enrollments = []
        for i, enrollment_dict in enumerate(enrollment_dicts):
            enrollment = await Enrollment.get_item(
                uid=uid(i + 1), business_name=constants.business_name_1, user_id=None
            )
            if enrollment:
                await enrollment.delete()

            enrollment = Enrollment(
                uid=uid(i + 1),
                created_at=now - timedelta(seconds=2),
                business_name=constants.business_name_1,
                user_id=uuid.UUID(constants.user_id_1_1),
                status="active",
                price=0,
                **enrollment_dict,
            )
            await enrollment.save()
            enrollments.append(enrollment)
    except Exception as e:
        import traceback

        traceback_str = "".join(traceback.format_tb(e.__traceback__))

        logging.error(f"create base enrollments: \n{traceback_str}\n{e}")
    yield enrollments

    for enrollment in enrollments:
        await enrollment.delete()


@pytest_asyncio.fixture(scope="session")
async def business(constants: StaticData):
    data = dict(
        name=StaticData.business_name_1,
        domain="test.ufaas.io",
        user_id=StaticData.user_id_1_1,
        uid=StaticData.business_id_1,
    )
    bus = await Business.get_by_origin(data["domain"])

    yield bus


@pytest_asyncio.fixture(scope="session")
async def access_token_business():
    usso_session = UssoSession(
        usso_base_url="https://sso.ufaas.io",
        usso_api_key=StaticData.usso_api_key,
        user_id=StaticData.user_id_1_1,
    )
    return usso_session.access_token


@pytest_asyncio.fixture(scope="session")
async def access_token_user():
    usso_session = UssoSession(
        usso_base_url="https://sso.ufaas.io",
        usso_api_key=StaticData.usso_api_key,
        user_id=StaticData.user_id_1_2,
    )
    return usso_session.access_token
