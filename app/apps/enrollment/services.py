import uuid
from datetime import datetime, timedelta

from pymongo import ASCENDING, DESCENDING

from apps.config.models import Configuration
from apps.enrollment.models import Enrollment
from apps.enrollment.schemas import AcquisitionType, Bundle


async def get_active_enrollments(
    business_name: str,
    user_id: uuid.UUID,
    asset: str,
    variant: str = None,
    enrollment_id: uuid.UUID = None,
) -> list[Enrollment]:
    base_query = Enrollment.get_active_enrollments_base_query(
        business_name=business_name,
        user_id=user_id,
        asset=asset,
        variant=variant,
        enrollment_id=enrollment_id,
    )
    base_query.append(
        {
            "$or": [
                {"variant": None},  # variant is None
                {"variant": variant},  # or variant matches given variant
            ]
        },
    )

    pipeline = [
        {"$match": {"$and": base_query}},
        {
            "$addFields": {
                "expire_at_null": {
                    "$cond": {
                        "if": {"$eq": ["$expire_at", None]},
                        "then": 1,
                        "else": 0,
                    }
                }
            }
        },
        {
            "$sort": {
                "variant": DESCENDING,  # Sort by variant
                "expire_at_null": ASCENDING,  # Sort nulls last (1 for null, 0 for non-null)
                "expire_at": ASCENDING,  # Sort by expire_at for non-null values
            }
        },
    ]

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


async def borrow_enrollment(business_name, user_id, asset, amount, variant):
    now = datetime.now() - timedelta(minutes=1)
    config = (await Configuration.get_config(business_name)) or Configuration(
        business_name=business_name
    )
    borrowed_enrollment = Enrollment(
        user_id=user_id,
        business_name=business_name,
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
