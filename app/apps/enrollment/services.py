"""Enrollment services."""

from datetime import datetime, timedelta
from decimal import Decimal

from pymongo import ASCENDING, DESCENDING

from apps.config.models import Configuration
from apps.enrollment.models import Enrollment
from apps.enrollment.schemas import AcquisitionType, Bundle


async def get_active_enrollments(
    tenant_id: str,
    user_id: str,
    asset: str,
    variant: str | None = None,
    enrollment_id: str | None = None,
) -> list[Enrollment]:
    """Get active enrollments for a user and asset."""
    base_query = Enrollment.get_active_enrollments_base_query(
        tenant_id=tenant_id,
        user_id=user_id,
        asset=asset,
        variant=variant,
        enrollment_id=enrollment_id,
    )

    pipeline = [
        {"$match": base_query},
        {
            "$addFields": {
                "expiry_sort": {"$ifNull": ["$expire_at", datetime(9999, 12, 31)]}
            }
        },
        {"$sort": {"variant": DESCENDING, "expiry_sort": ASCENDING}},
    ]

    active_enrollments = [
        Enrollment(**record) async for record in Enrollment.aggregate(pipeline)
    ]

    return active_enrollments


async def borrow_enrollment(
    tenant_id: str,
    user_id: str,
    asset: str,
    amount: Decimal,
    variant: str | None = None,
) -> Enrollment:
    """Create a borrowed enrollment for a user."""
    now = datetime.now() - timedelta(minutes=1)
    config = (await Configuration.get_config(tenant_id)) or Configuration(
        tenant_id=tenant_id
    )
    borrowed_enrollment = Enrollment(
        user_id=user_id,
        tenant_id=tenant_id,
        acquisition_type=AcquisitionType.borrowed,
        status="active",
        start_at=now,
        expire_at=now + timedelta(minutes=30),
        bundles=[Bundle(asset=asset, quota=amount)],
        variant=variant,
        due_date=now
        + timedelta(days=config.default_borrow_period)
        + timedelta(minutes=30),
    )
    await borrowed_enrollment.save()
    return borrowed_enrollment
