import time
import uuid
from datetime import datetime, timedelta

import pytest
import pytest_asyncio

from apps.enrollment.models import Enrollment
from apps.usage.services import select_enrollment
from tests.constants import StaticData

uid = lambda i: uuid.UUID(f"{i:032}")


@pytest_asyncio.fixture(scope="module", autouse=True)
async def enrollments(constants: StaticData):
    now = datetime.now()
    await Enrollment(
        uid=uid(1),
        created_at=now - timedelta(seconds=10),
        business_name=constants.business_name_1,
        user_id=constants.user_id_1_1,
        status="active",
        price=0,
        expired_at=now + timedelta(seconds=10),
        bundles=[dict(asset="image", quota=10)],
    ).save()
    await Enrollment(
        uid=uid(2),
        created_at=now - timedelta(seconds=10),
        business_name=constants.business_name_1,
        user_id=constants.user_id_1_1,
        status="active",
        price=0,
        expired_at=None,
        bundles=[dict(asset="image", quota=10)],
    ).save()
    await Enrollment(
        uid=uid(3),
        created_at=now - timedelta(seconds=10),
        business_name=constants.business_name_1,
        user_id=constants.user_id_1_1,
        status="active",
        price=0,
        expired_at=now + timedelta(seconds=11),
        bundles=[dict(asset="image", quota=10)],
        variant="variant",
    ).save()
    await Enrollment(
        uid=uid(4),
        created_at=now - timedelta(seconds=10),
        business_name=constants.business_name_1,
        user_id=constants.user_id_1_1,
        status="active",
        price=0,
        expired_at=now + timedelta(seconds=2),
        bundles=[dict(asset="image", quota=10), dict(asset="text", quota=10)],
    ).save()
    await Enrollment(
        uid=uid(5),
        created_at=now - timedelta(seconds=10),
        business_name=constants.business_name_1,
        user_id=constants.user_id_1_1,
        status="active",
        price=0,
        expired_at=now + timedelta(seconds=1),
        bundles=[dict(asset="text", quota=10)],
    ).save()


@pytest.mark.asyncio
async def test_select_enrollment_normal(constants: StaticData):
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
async def test_select_enrollment_large(constants: StaticData):
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
async def test_select_enrollment_large_variant(constants: StaticData):
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
async def test_select_enrollment_delayed(constants: StaticData):
    time.sleep(10)
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
