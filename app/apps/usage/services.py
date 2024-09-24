import uuid
from datetime import datetime
from decimal import Decimal

from bson import UUID_SUBTYPE, Binary
from pymongo import ASCENDING, DESCENDING

from apps.enrollment.models import Enrollment


async def select_enrollment(
    business_name: str,
    user_id: uuid.UUID,
    asset: str,
    amount: Decimal = Decimal(1),
    variant: str = None,
    enrollment_id: uuid.UUID = None,
) -> list[tuple[Enrollment, Decimal]]:
    now = datetime.now()
    user_id = Binary.from_uuid(user_id, UUID_SUBTYPE)
    base_query = {
        "business_name": business_name,
        "user_id": user_id,
        "is_deleted": False,
        "status": "active",
        "started_at": {"$lt": now},
        "$and": [
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

    # active_enrollments: list[Enrollment] = (
    #     await Enrollment.find(base_query)
    #     .sort([("variant", DESCENDING), ("expired_at", ASCENDING)])
    #     .to_list()
    # )

    residual = amount
    selected_enrollments = []
    for enrollment in active_enrollments:
        leftover_bundles = await enrollment.get_leftover_bundles()
        for bundle in leftover_bundles:
            if bundle.asset != asset:
                continue
            using_quota = min(bundle.quota, residual)
            selected_enrollments.append((enrollment, using_quota))
            residual -= using_quota
            if residual == 0:
                return selected_enrollments
