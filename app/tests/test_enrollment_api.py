"""Enrollment and usage API tests."""

import json
import logging

import httpx
import pytest

from apps.enrollment.models import Enrollment
from tests.constants import StaticData

logger = logging.getLogger("tests.test_enrollment_api")

enrollment_endpoint = "/enrollments"
usage_endpoint = "/usages"


@pytest.mark.asyncio
async def test_usage_create(
    authenticated_client: httpx.AsyncClient,
    enrollments: list[Enrollment],
    constants: StaticData,
) -> None:
    """Test creating a usage record."""
    response = await authenticated_client.post(
        usage_endpoint,
        json={
            "asset": "image",
            "amount": 5,
            "user_id": constants.user_id_1_1,
        },
    )
    assert response.status_code == 201
    resp_json = response.json()
    logger.info("usage: %s", json.dumps(resp_json))


@pytest.mark.asyncio
async def test_usage_list(
    authenticated_client: httpx.AsyncClient,
    enrollments: list[Enrollment],
    constants: StaticData,
) -> None:
    """Test listing usage records."""
    response = await authenticated_client.get(
        usage_endpoint, params={"user_id": constants.user_id_1_1}
    )
    resp_json = response.json()
    logger.info("usage_list: %s", json.dumps(resp_json))
    assert response.status_code == 200
    assert isinstance(resp_json.get("items"), list)
    assert len(resp_json.get("items")) == 1
    item = resp_json.get("items")[0]
    item_id = item.get("uid")
    response = await authenticated_client.get(
        f"{usage_endpoint}/{item_id}",
    )
    resp_json = response.json()
    logger.info("usage: %s", json.dumps(resp_json))
    assert response.status_code == 200
    assert resp_json.get("uid") == item_id


@pytest.mark.asyncio
async def test_enrollment_endpoint_list(
    authenticated_client: httpx.AsyncClient,
    enrollments: list[Enrollment],
) -> None:
    """Test listing enrollment records."""
    response = await authenticated_client.get(
        enrollment_endpoint,
        params={"is_valid": False},
    )
    resp_json = response.json()
    logger.info("enrollment_list: %s %s", authenticated_client.base_url, resp_json)
    assert response.status_code == 200
    assert isinstance(resp_json.get("items"), list)
    assert len(resp_json.get("items")) == len(enrollments)
    item = resp_json.get("items")[0]
    item_id = item.get("uid")
    response = await authenticated_client.get(f"{enrollment_endpoint}/{item_id}")
    resp_json = response.json()
    assert response.status_code == 200
    assert resp_json.get("uid") == item_id
    logger.info("enrollment: %s", json.dumps(resp_json))


@pytest.mark.asyncio
async def test_enrollment_endpoint_create(
    authenticated_client: httpx.AsyncClient,
    enrollment_dicts: list[dict],
    constants: StaticData,
) -> None:
    """Test creating an enrollment record."""
    from json_advanced import json_encoder

    data = enrollment_dicts[0]
    data.update({
        "user_id": constants.user_id_1_2,
        "price": 0,
    })
    response = await authenticated_client.post(
        enrollment_endpoint,
        json=json.loads(json.dumps(data, cls=json_encoder.JSONSerializer)),
    )
    resp_json = response.json()
    logger.info("enrollment_create: %s %s", authenticated_client.base_url, resp_json)
    assert response.status_code == 201
