import uuid
from datetime import datetime

from apps.enrollment.models import Enrollment
from bson import UUID_SUBTYPE, Binary
from pymongo import ASCENDING, DESCENDING


async def get_active_enrollments(
    business_name: str,
    user_id: uuid.UUID,
    asset: str,
    variant: str = None,
    enrollment_id: uuid.UUID = None,
) -> list[Enrollment]:
    # base_query = Enrollment.get_active_enrollments_base_query(
    #     business_name=business_name,
    #     user_id=user_id,
    #     asset=asset,
    #     variant=variant,
    #     enrollment_id=enrollment_id,
    # )
    now = datetime.now()

    base_query = {
        "business_name": business_name,
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
    }
    if enrollment_id:
        base_query["uid"] = enrollment_id

    if user_id:
        user_id = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        user_id = Binary.from_uuid(user_id, UUID_SUBTYPE)
        base_query["user_id"] = user_id

    if asset:
        base_query["bundles.asset"] = asset

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
