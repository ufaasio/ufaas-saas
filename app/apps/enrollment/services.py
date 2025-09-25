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
        # {
        #     "$addFields": {
        #         "expire_at_null": {
        #             "$cond": {
        #                 "if": {"$eq": ["$expire_at", None]},
        #                 "then": 1,
        #                 "else": 0,
        #             }
        #         }
        #     }
        # },
        # {
        #     "$sort": {
        #         "variant": DESCENDING,  # Sort by variant
        #         # Sort nulls last (1 for null, 0 for non-null)
        #         "expire_at_null": ASCENDING,
        #         "expire_at": ASCENDING,  # Sort by expire_at for non-null values
        #     }
        # },
    ]

    import logging

    logging.info(pipeline)

    # pipeline_result: list[dict] = await Enrollment.aggregate(pipeline).to_list()
    active_enrollments = [
        Enrollment(**record) async for record in Enrollment.aggregate(pipeline)
    ]

    # import logging
    # import json_advanced as json

    # all_enrollments = await Enrollment.find({}).to_list()

    # logging.info(
    #     "\n".join(
    #         [
    #             f"Active enrollments: {active_enrollments}",
    #             # f"{len(all_enrollments)}: {json.dumps(all_enrollments, indent=2)}",
    #             # f"{json.dumps(pipeline, indent=2)}",
    #         ]
    #     )
    # )

    return active_enrollments

    # active_enrollments: list[Enrollment] = (
    #     await Enrollment.find(base_query)
    #     .sort([("variant", DESCENDING), ("expire_at", ASCENDING)])
    #     .to_list()
    # )


async def borrow_enrollment(
    tenant_id: str,
    user_id: str,
    asset: str,
    amount: Decimal,
    variant: str | None = None,
) -> Enrollment:
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
