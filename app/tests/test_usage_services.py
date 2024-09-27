import time
import uuid

import pytest

from apps.usage.services import select_enrollment
from tests.constants import StaticData

uid = lambda i: uuid.UUID(f"{i:032}")


@pytest.mark.asyncio
async def test_select_enrollment_normal(constants: StaticData, enrollments):
    business_name = constants.business_name_1
    user_id = uuid.UUID(constants.user_id_1_1)
    asset = "image"
    amount = 5
    variant = None
    enrollment_id = None
    enrollment_quotas = await select_enrollment(
        business_name=business_name,
        user_id=user_id,
        asset=asset,
        amount=amount,
        variant=variant,
        enrollment_id=enrollment_id,
    )
    assert enrollment_quotas is not None
    assert type(enrollment_quotas) == list
    assert len(enrollment_quotas) == 1
    assert enrollment_quotas[0] is not None
    assert type(enrollment_quotas[0]) == tuple
    assert enrollment_quotas[0][0].uid == uid(4)


@pytest.mark.asyncio
async def test_select_enrollment_large(constants: StaticData, enrollments):
    enrollment_quotas = await select_enrollment(
        business_name=constants.business_name_1,
        user_id=uuid.UUID(constants.user_id_1_1),
        asset="image",
        amount=15,
    )
    assert enrollment_quotas is not None
    assert type(enrollment_quotas) == list
    assert len(enrollment_quotas) == 2
    assert enrollment_quotas[0] is not None
    assert type(enrollment_quotas[0]) == tuple
    assert enrollment_quotas[0][0].uid == uid(4)
    assert enrollment_quotas[1][0].uid == uid(1)


@pytest.mark.asyncio
async def test_select_enrollment_large_variant(constants: StaticData, enrollments):
    enrollment_quotas = await select_enrollment(
        business_name=constants.business_name_1,
        user_id=uuid.UUID(constants.user_id_1_1),
        asset="image",
        amount=15,
        variant="variant",
    )
    assert enrollment_quotas is not None
    assert type(enrollment_quotas) == list
    assert len(enrollment_quotas) == 2
    assert enrollment_quotas[0] is not None
    assert type(enrollment_quotas[0]) == tuple
    assert enrollment_quotas[0][0].uid == uid(3)
    assert enrollment_quotas[1][0].uid == uid(4)


@pytest.mark.asyncio
async def test_select_enrollment_delayed(constants: StaticData, enrollments):
    time.sleep(2)
    enrollment_quotas = await select_enrollment(
        business_name=constants.business_name_1,
        user_id=uuid.UUID(constants.user_id_1_1),
        asset="image",
        amount=5,
    )
    assert enrollment_quotas is not None
    assert type(enrollment_quotas) == list
    assert len(enrollment_quotas) == 1
    assert enrollment_quotas[0] is not None
    assert type(enrollment_quotas[0]) == tuple
    assert enrollment_quotas[0][0].uid == uid(2)
