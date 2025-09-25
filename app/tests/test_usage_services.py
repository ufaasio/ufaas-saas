import asyncio

import pytest

from apps.enrollment.models import Enrollment
from apps.usage.services import select_enrollment
from tests.constants import StaticData

from .conftest import uid


@pytest.mark.asyncio
async def test_select_enrollment_normal(
    constants: StaticData, enrollments: list[Enrollment]
) -> None:
    tenant_id = constants.tenant_id_1
    user_id = constants.user_id_1_1
    asset = "image"
    amount = 5
    variant = None
    enrollment_id = None
    enrollment_quotas, _residual = await select_enrollment(
        tenant_id=tenant_id,
        user_id=user_id,
        asset=asset,
        amount=amount,
        variant=variant,
        enrollment_id=enrollment_id,
    )
    import logging
    from datetime import datetime

    logging.info("%s %s", datetime.now(), enrollment_quotas)
    assert enrollment_quotas is not None
    assert isinstance(enrollment_quotas, list)
    assert len(enrollment_quotas) == 1
    assert enrollment_quotas[0] is not None
    assert isinstance(enrollment_quotas[0], tuple)
    assert enrollment_quotas[0][0].uid == uid(4)


@pytest.mark.asyncio
async def test_select_enrollment_large(
    constants: StaticData, enrollments: list[Enrollment]
) -> None:
    enrollment_quotas, _residual = await select_enrollment(
        tenant_id=constants.tenant_id_1,
        user_id=constants.user_id_1_1,
        asset="image",
        amount=15,
    )
    assert enrollment_quotas is not None
    assert isinstance(enrollment_quotas, list)
    assert len(enrollment_quotas) == 2
    assert enrollment_quotas[0] is not None
    assert isinstance(enrollment_quotas[0], tuple)
    assert enrollment_quotas[0][0].uid == uid(4)
    assert enrollment_quotas[1][0].uid == uid(1)


@pytest.mark.asyncio
async def test_select_enrollment_large_variant(
    constants: StaticData, enrollments: list[Enrollment]
) -> None:
    enrollment_quotas, _residual = await select_enrollment(
        tenant_id=constants.tenant_id_1,
        user_id=constants.user_id_1_1,
        asset="image",
        amount=15,
        variant="variant",
    )
    assert enrollment_quotas is not None
    assert isinstance(enrollment_quotas, list)
    assert len(enrollment_quotas) == 2
    assert enrollment_quotas[0] is not None
    assert isinstance(enrollment_quotas[0], tuple)
    assert enrollment_quotas[0][0].uid == uid(3)
    assert enrollment_quotas[1][0].uid == uid(4)


@pytest.mark.asyncio
async def test_select_enrollment_delayed(
    constants: StaticData, enrollments: list[Enrollment]
) -> None:
    await asyncio.sleep(2)
    enrollment_quotas, _residual = await select_enrollment(
        tenant_id=constants.tenant_id_1,
        user_id=constants.user_id_1_1,
        asset="image",
        amount=5,
    )
    assert enrollment_quotas is not None
    assert isinstance(enrollment_quotas, list)
    assert len(enrollment_quotas) == 1
    assert enrollment_quotas[0] is not None
    assert isinstance(enrollment_quotas[0], tuple)
    assert enrollment_quotas[0][0].uid == uid(2)
