import json
import logging
import uuid

from tests.constants import StaticData

import httpx
import pytest

uid = lambda i: uuid.UUID(f"{i:032}")

base_route = "/api/v1/apps/saas"
enrollment_endpoint = f"{base_route}/enrollments/"
usage_endpoint = f"{base_route}/usages/"


@pytest.mark.asyncio
async def test_usage_create(
    client: httpx.AsyncClient, auth_headers_business, enrollments, businesses, constants: StaticData
):
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
    logging.info(f"usage: {json.dumps(resp_json, indent=4)}")


@pytest.mark.asyncio
async def test_enrollment_endpoint_list(
    client: httpx.AsyncClient, auth_headers_business, enrollments
):
    response = await client.get(enrollment_endpoint, headers=auth_headers_business)
    resp_json = response.json()
    logging.info(
        f"enrollment_list: {client.base_url} {json.dumps(resp_json, indent=4)}"
    )
    assert response.status_code == 200
    assert type(resp_json.get("items")) == list
    assert len(resp_json.get("items")) == len(enrollments)
