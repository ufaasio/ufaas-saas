import json
import logging
import uuid

import httpx
import json_advanced as json
import pytest

from tests.constants import StaticData

uid = lambda i: uuid.UUID(f"{i:032}")

base_route = "/api/v1/apps/saas"
enrollment_endpoint = f"{base_route}/enrollments/"
usage_endpoint = f"{base_route}/usages/"


@pytest.mark.asyncio
async def test_usage_create(
    client: httpx.AsyncClient,
    auth_headers_business,
    enrollments,
    businesses,
    constants: StaticData,
):
    try:
        response = await client.post(
            usage_endpoint,
            headers=auth_headers_business,
            json={
                "asset": "image",
                "amount": 5,
                "user_id": constants.user_id_1_1,
            },
        )
        resp_json = response.json()
        logging.info(f"usage: {json.dumps(resp_json)}")
    except Exception as e:
        logging.error(f"usage: {e}")


@pytest.mark.asyncio
async def test_usage_list(
    client: httpx.AsyncClient,
    auth_headers_business,
    enrollments,
    businesses,
    constants: StaticData,
):
    response = await client.get(usage_endpoint, headers=auth_headers_business)
    resp_json = response.json()
    logging.info(f"usage_list: {json.dumps(resp_json)}")
    assert response.status_code == 200
    assert type(resp_json.get("items")) == list
    assert len(resp_json.get("items")) == 1
    item = resp_json.get("items")[0]
    item_id = item.get("uid")
    response = await client.get(
        f"{usage_endpoint}{item_id}", headers=auth_headers_business
    )
    resp_json = response.json()
    assert response.status_code == 200
    assert resp_json.get("uid") == item_id
    logging.info(f"usage: {json.dumps(resp_json)}")


@pytest.mark.asyncio
async def test_enrollment_endpoint_list(
    client: httpx.AsyncClient, auth_headers_business, enrollments
):
    response = await client.get(enrollment_endpoint, headers=auth_headers_business)
    resp_json = response.json()
    logging.info(f"enrollment_list: {client.base_url} {resp_json}")
    assert response.status_code == 200
    assert type(resp_json.get("items")) == list
    assert len(resp_json.get("items")) == len(enrollments)
    item = resp_json.get("items")[0]
    item_id = item.get("uid")
    response = await client.get(
        f"{enrollment_endpoint}{item_id}", headers=auth_headers_business
    )
    resp_json = response.json()
    assert response.status_code == 200
    assert resp_json.get("uid") == item_id
    logging.info(f"enrollment: {json.dumps(resp_json)}")


@pytest.mark.asyncio
async def test_enrollment_endpoint_create(
    client: httpx.AsyncClient,
    auth_headers_business,
    enrollment_dicts,
    constants: StaticData,
):
    data = enrollment_dicts[0]
    data.update(
        {
            "user_id": constants.user_id_1_2,
            "price": 0,
        }
    )
    response = await client.post(
        enrollment_endpoint,
        headers=auth_headers_business,
        content=json.dumps(data),
    )
    resp_json = response.json()
    logging.info(f"enrollment_create: {client.base_url} {resp_json}")
    assert response.status_code == 201
