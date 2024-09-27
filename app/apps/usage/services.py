import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from bson import UUID_SUBTYPE, Binary
from pymongo import ASCENDING, DESCENDING

from apps.enrollment.models import Enrollment
from apps.enrollment.schemas import AcquisitionType, Bundle, FreemiumQuota


async def get_or_create_freemium_enrollment(
    business_name: str, user_id: uuid.UUID, freemium_quotas: FreemiumQuota
) -> Enrollment:
    now = datetime.now()
    # Check if the user has an active freemium enrolment
    freemium_enrollment = await Enrollment.find_one(
        {
            "business_name": business_name,
            "user_id": user_id,
            "acquisition_type": "freemium",
            "status": "active",
            "started_at": {"$lte": now},
            "expired_at": {"$gt": now},  # Still active for the current period
        }
    )

    if freemium_enrollment:
        return freemium_enrollment

    freemium_enrollment = Enrollment(
        user_id=user_id,
        business_name=business_name,
        acquisition_type=AcquisitionType.freemium,
        status="active",
        started_at=now,
        expired_at=now + timedelta(days=freemium_quotas.period_days),
        bundles=freemium_quotas.bundles,
        variant=freemium_quotas.variant,
    )
    await freemium_enrollment.save()
    return freemium_enrollment


async def get_freemium_quota(business_name):
    return None
    FreemiumQuota(bundles=[Bundle(asset="token", quota=20)], days=1, variant=None)


async def use_freemium_quota(business_name, user_id, asset, amount, variant=None):
    freemium_quota = await get_freemium_quota(business_name)
    if freemium_quota is None:
        return

    # Step 1: Get or create freemium enrolment
    freemium_enrollment: Enrollment = await get_or_create_freemium_enrollment(
        business_name=business_name,
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


async def use_enrollment_quota(enrollment: Enrollment, asset: str, amount: Decimal):
    """
    Use a specified quota from the enrollment's leftover bundles for a given asset.

    :param enrollment: The enrollment object containing the bundles.
    :param asset: The asset for which quota is being consumed.
    :param amount: The amount of quota to consume.
    :return: A tuple with the updated enrollment, the amount used, and the updated leftover bundles.
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

    # If the bundle's quota is larger than the amount to use, deduct the amount and return
    if matching_bundle.quota >= amount:
        matching_bundle.quota -= amount
        return enrollment, amount, leftover_bundles

    # If the bundle's quota is less than or equal to the amount, use the full bundle and remove it
    leftover_bundles.pop(matching_bundle_index)
    return enrollment, matching_bundle.quota, leftover_bundles


async def get_active_enrollments(
    business_name: str,
    user_id: uuid.UUID,
    asset: str,
    variant: str = None,
    enrollment_id: uuid.UUID = None,
) -> list[Enrollment]:
    now = datetime.now()
    user_id = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
    user_id = Binary.from_uuid(user_id, UUID_SUBTYPE)
    base_query = {
        "business_name": business_name,
        "user_id": user_id,
        "is_deleted": False,
        "started_at": {"$lt": now},
        "status": "active",
        "$and": [
            {
                "$or": [
                    {
                        "acquisition_type": "purchase",
                    },
                    {
                        "acquisition_type": "borrowed",
                        "due_date": {"$gt": now},
                        "is_paid": False,
                    },
                ]
            },
            {
                "$or": [
                    {"expired_at": {"$gt": now}},  # expire_at after now
                    {"expired_at": None},  # or expire_at is None
                ]
            },
            {
                "$or": [
                    {"variant": None},  # variant is None
                    {"variant": variant},  # or variant matches given variant
                ]
            },
        ],
        "bundles.asset": asset,
    }
    if enrollment_id:
        base_query["uid"] = enrollment_id

    pipeline = [
        {"$match": base_query},
        {
            "$addFields": {
                "expired_at_null": {
                    "$cond": {
                        "if": {"$eq": ["$expired_at", None]},
                        "then": 1,
                        "else": 0,
                    }
                }
            }
        },
        {
            "$sort": {
                "variant": DESCENDING,  # Sort by variant
                "expired_at_null": ASCENDING,  # Sort nulls last (1 for null, 0 for non-null)
                "expired_at": ASCENDING,  # Sort by expired_at for non-null values
            }
        },
    ]

    # pipeline_result: list[dict] = await Enrollment.aggregate(pipeline).to_list()
    active_enrollments = [
        Enrollment(**record) async for record in Enrollment.aggregate(pipeline)
    ]
    return active_enrollments

    # active_enrollments: list[Enrollment] = (
    #     await Enrollment.find(base_query)
    #     .sort([("variant", DESCENDING), ("expired_at", ASCENDING)])
    #     .to_list()
    # )


async def select_enrollment(
    business_name: str,
    user_id: uuid.UUID,
    asset: str,
    amount: Decimal = Decimal(1),
    variant: str = None,
    enrollment_id: uuid.UUID = None,
) -> list[tuple[Enrollment, Decimal]]:
    residual = amount
    selected_enrollments = []

    freemium = await use_freemium_quota(
        business_name=business_name,
        user_id=user_id,
        asset=asset,
        amount=amount,
        variant=variant,
    )
    if freemium:
        freemium_enrollment, freemium_quota, leftover_bundles = freemium
        selected_enrollments.append(
            (freemium_enrollment, freemium_quota, leftover_bundles)
        )
        residual -= freemium_quota

    active_enrollments = await get_active_enrollments(
        business_name=business_name,
        user_id=user_id,
        asset=asset,
        variant=variant,
        enrollment_id=enrollment_id,
    )

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
            return selected_enrollments

    return selected_enrollments
