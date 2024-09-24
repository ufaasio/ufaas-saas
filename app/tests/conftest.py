import logging
import os
from typing import AsyncGenerator

import debugpy
import httpx
import pytest
import pytest_asyncio
from beanie import init_beanie
from fastapi_mongo_base import models as base_mongo_models

from server.config import Settings
from server.server import app as fastapi_app
from tests.constants import StaticData
from utils.basic import get_all_subclasses


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
        app=fastapi_app, base_url="http://test.ufaas.io"
    ) as ac:
        yield ac


@pytest_asyncio.fixture(scope="session")
async def access_token_business():
    data = {"refresh_token": StaticData.refresh_token}
    async with httpx.AsyncClient(base_url="https://sso.ufaas.io") as client:
        response = await client.post("/auth/refresh", json=data)
        return response.json()["access_token"]


@pytest_asyncio.fixture(scope="session")
async def access_token_user():
    data = {"refresh_token": StaticData.refresh_token_user}
    async with httpx.AsyncClient(base_url="https://sso.ufaas.io") as client:
        response = await client.post("/auth/refresh", json=data)
        return response.json()["access_token"]


@pytest_asyncio.fixture(scope="session")
async def auth_headers_business(access_token_business):
    return {"Authorization": f"Bearer {access_token_business}"}


@pytest.fixture(scope="module")
def constants():
    return StaticData()
