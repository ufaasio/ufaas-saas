"""Usage services."""

from datetime import datetime, timedelta
from decimal import Decimal

from fastapi_mongo_base.errors import PaymentRequiredError

from apps.enrollment.models import Enrollment
from apps.enrollment.schemas import AcquisitionType, Bundle, FreemiumQuota
from apps.enrollment.services import borrow_enrollment, get_active_enrollments

from .models import Usage
from .schemas import UsageConsumption


async def get_or_create_freemium_enrollment(
    tenant_id: str, user_id: str, freemium_quotas: FreemiumQuota
) -> Enrollment:
    now = datetime.now()
    # Check if the user has an active freemium enrolment
    freemium_enrollment = await Enrollment.find_one({
        "tenant_id": tenant_id,
        "user_id": user_id,
        "acquisition_type": "freemium",
        "status": "active",
        "starte_at": {"$lte": now},
        "expire_at": {"$gt": now},  # Still active for the current period
    })

    if freemium_enrollment:
        return freemium_enrollment

    freemium_enrollment = Enrollment(
        user_id=user_id,
        tenant_id=tenant_id,
        acquisition_type=AcquisitionType.freemium,
        status="active",
        start_at=now,
        expire_at=now + timedelta(days=freemium_quotas.period_days),
        bundles=freemium_quotas.bundles,
        variant=freemium_quotas.variant,
    )
    await freemium_enrollment.save()
    return freemium_enrollment


async def get_freemium_quota(tenant_id: str) -> object:  # ruff:ignore[unused-async]
    return None
    FreemiumQuota(bundles=[Bundle(asset="token", quota=20)], days=1, variant=None)


async def use_freemium_quota(
    tenant_id: str,
    user_id: str,
    asset: str,
    amount: Decimal,
    variant: str | None = None,
) -> None:
    freemium_quota = await get_freemium_quota(tenant_id)
    if freemium_quota is None:
        return

    # Step 1: Get or create freemium enrolment
    freemium_enrollment: Enrollment = await get_or_create_freemium_enrollment(
        tenant_id=tenant_id,
        user_id=user_id,
        asset=asset,
        freemium_quota=freemium_quota,
        variant=variant,
    )

    # Consume from freemium quota first
    if freemium_enrollment:
        return await use_enrollment_quota(
            enrollment=freemium_enrollment, asset=asset, amount=amount
        )

    return


async def use_enrollment_quota(
    enrollment: Enrollment, asset: str, amount: Decimal
) -> tuple[Enrollment, Decimal, list[Bundle]]:
    """
    Use a specified quota from the enrollment's leftover bundles for a given asset.

    :param enrollment: The enrollment object containing the bundles.
    :param asset: The asset for which quota is being consumed.
    :param amount: The amount of quota to consume.
    :return: A tuple with the updated enrollment, the amount used,
    and the updated leftover bundles.
    """
    # Retrieve the leftover bundles associated with the enrollment
    leftover_bundles = await enrollment.get_leftover_bundles()

    # Find the first bundle matching the specified asset
    matching_bundle_index = None
    for i, bundle in enumerate(leftover_bundles):
        if bundle.asset == asset:
            matching_bundle_index = i
            break
    else:
        # No matching bundle found, return without modifying anything
        return

    matching_bundle = leftover_bundles[matching_bundle_index]

    # If the bundle's quota is larger than the amount to use,
    # deduct the amount and return
    if matching_bundle.quota >= amount:
        matching_bundle.quota -= amount
        return enrollment, amount, leftover_bundles

    # If the bundle's quota is less than or equal to the amount,
    # use the full bundle and remove it
    leftover_bundles.pop(matching_bundle_index)
    return enrollment, matching_bundle.quota, leftover_bundles


async def select_enrollment(
    tenant_id: str,
    user_id: str,
    asset: str,
    amount: Decimal = Decimal(1),
    variant: str | None = None,
    enrollment_id: str | None = None,
) -> tuple[list[tuple[Enrollment, Decimal]], Decimal]:
    residual = amount
    selected_enrollments = []

    active_enrollments = await get_active_enrollments(
        tenant_id=tenant_id,
        user_id=user_id,
        asset=asset,
        variant=variant,
        enrollment_id=enrollment_id,
    )

    import logging

    logging.info("%s\n%s", datetime.now(), Enrollment.summaries(active_enrollments))

    for enrollment in active_enrollments:
        using = await use_enrollment_quota(
            enrollment=enrollment, asset=asset, amount=residual
        )
        if not using:
            continue

        enrollment, using_quota, leftover_bundles = using
        residual -= using_quota
        selected_enrollments.append((enrollment, using_quota, leftover_bundles))
        if residual == 0:
            break

    return selected_enrollments, residual


async def create_usage(
    tenant_id: str,
    user_id: str,
    asset: str,
    amount: Decimal = Decimal(1),
    variant: str | None = None,
    enrollment_id: str | None = None,
    meta_data: dict | None = None,
    borrow: bool = False,
) -> Usage:
    enrollment_quotas, residual = await select_enrollment(
        tenant_id=tenant_id,
        user_id=user_id,
        asset=asset,
        amount=amount,
        variant=variant,
        enrollment_id=enrollment_id,
    )

    if not borrow and residual > 0:
        raise PaymentRequiredError(
            error_core="insufficient_enrollment",
            detail=(
                "Not enough available resources in active enrollments for the usage"
            ),
            message={
                "en": (
                    "Not enough available resources in active enrollments for the usage"
                ),
                "fa": "موجودی فعال، برای استفاده مورد نظر موجود نیست",
            },
        )
    elif borrow and residual > 0:
        borrowed_enrollment = await borrow_enrollment(
            tenant_id, user_id, asset, residual, variant
        )
        enrollment_quotas.append((borrowed_enrollment, residual, []))

    consumptions: list[Usage] = []
    for enrollment, quota, leftover_bundles in enrollment_quotas:
        # create usage
        consumption = UsageConsumption(
            enrollment_id=enrollment.uid,
            amount=quota,
            leftover_bundles=leftover_bundles,
        )
        consumptions.append(consumption)

    item = Usage(
        tenant_id=tenant_id,
        user_id=user_id,
        asset=asset,
        amount=quota,
        variant=variant,
        meta_data=meta_data,
        consumptions=consumptions,
    )
    return item
