import uuid

from core.exceptions import BaseHTTPException
from fastapi import APIRouter, Depends
from server.db import AsyncSession, get_session
from sqlalchemy import select

from .models import Enrollments, Usages
from .schemas import UsageSchema

router = APIRouter(prefix="/usages", tags=["Usage"])

#### Usages APIs ####


##### get list of Usages #####


@router.get("/", response_model=list[UsageSchema])
async def get_filtered_usages(
    business_id: uuid.UUID,
    user_id=None,
    resource=None,
    volume=None,
    on_item=None,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Usages).filter_by(business_id=business_id)
    if user_id:
        stmt = stmt.filter_by(user_id=user_id)
    if resource:
        stmt = stmt.filter_by(resource=resource)
    if volume:
        stmt = stmt.filter_by(volume=volume)
    if on_item:
        stmt = stmt.filter_by(on_item=on_item)

    result = await session.execute(stmt)
    return result.scalars().all()


async def get_usages(
    business_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
    resource: str | None = None,
    volume: int | None = None,
    on_item: str | None = None,
):
    """Rerurn list of Usages"""
    query = Usages.query.filter_by(business_id=business_id)
    if user_id:
        query = query.filter_by(user_id=user_id)
    if resource:
        query = query.filter_by(resource=resource)
    if volume:
        query = query.filter_by(volume=volume)
    if on_item:
        query = query.filter_by(on_item=on_item)
    return query.all()


##### get single Usages ####
@router.get("/{usages_id}", response_model=UsageSchema)
async def get_usage(usages_id: uuid.UUID):
    """Rerurn single Usages"""
    return Usages.query.get(usages_id)


##### create an Usage ####
@router.post("/", response_model=uuid.UUID)
async def create_usage(
    user_id: uuid.UUID,
    business_id: uuid.UUID,
    on_item: str,
    resource: str,
    volume: int,
):
    """Create an Usage"""
    try:
        enrollment_id = Usages.check_enrollment_condition(
            None,
            None,
            None,
            Usages(
                user_id=user_id,
                business_id=business_id,
                on_item=on_item,
                resource=resource,
                volume=volume,
            ),
        )
        usage = Usages(
            user_id=user_id,
            business_id=business_id,
            on_item=on_item,
            resource=resource,
            volume=volume,
            enrollment_id=enrollment_id,
        )
        db.session.add(usage)
        db.session.commit()
        Usages.change_enrollment_resource(
            None,
            None,
            Usages(
                change_type="decrease",
                enrollment_id=enrollment_id,
                resource=resource,
                volume=volume,
            ),
        )
        db.session.commit()
        return usage.uid
    except ValueError as e:
        raise fastapi.HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise fastapi.HTTPException(status_code=500, detail=str(e)) from e


##### delete an Usage ####
"""
To support CRUD operations (Create, Read, Update, Delete) with a maturity level of 2, we will develop endpoints based on the models defined in `app/apps/base/models.py`.

The Usages table is immutable, meaning we cannot modify any record directly. When deleting a usage, we will perform the following steps:

1. Accept a `usage_id` as input.
2. Retrieve the corresponding usage record.
3. If the usage record is not found, raise an HTTP exception with a status code of 404 and a detail message indicating that the usage was not found.
4. Retrieve the Enrollments record associated with the usage.
5. Increase the corresponding resource in the Enrollments record's `remain_resources` using the "change_enrollment_resource" function with the "change_type" set to "increase".
6. Commit the changes to the database.
7. Return the `usage_id` as the response.

The purpose of this endpoint is to reverse the effect of creating a usage by decreasing the corresponding resource in the Enrollments record's `remain_resources`.
"""


@router.delete("/{usage_id}", response_model=uuid.UUID)
async def delete_usage(
    usage_id: uuid.UUID,
):
    """Delete an Usage"""
    usage = Usages.query.get(usage_id)
    if not usage:
        raise BaseHTTPException(
            status_code=404, error="item_not_found", message="Usage not found"
        )
    enrollment = Enrollments.query.get(usage.enrollment_id)
    Usages.change_enrollment_resource(
        None,
        None,
        Usages(
            change_type="increase",
            enrollment_id=enrollment.uid,
            resource=usage.resource,
            volume=usage.volume,
        ),
    )
    db.session.commit()
    return usage_id
