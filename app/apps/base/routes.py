
from typing import Any, Generic, Type, TypeVar

from fastapi import APIRouter, BackgroundTasks, Request

from core.exceptions import BaseHTTPException
from server.config import Settings

# from .handlers import create_dto
from .models import BaseEntity, TaskBaseEntity


"""
Based on models developed in app>apps>base>models.py
write CRUP Endpoints with maturity level 2
"""
#### Enrollments APIs ####


##### get list of Enrollments #####

router = APIRouter()


@router.get("/enrollments", response_model=list[Enrollments])
async def get_enrollments(
    """ Rerurn list of Enrollments """
    business_id: uuid.UUID,
    user_id: Optional[uuid.UUID] = None,
    started_at: Optional[datetime] = None,
    expired_at: Optional[datetime] = None,
    plan: Optional[dict] = None,
    on_item: Optional[str] = None,
    resources: Optional[dict] = None,
    settings: Settings = fastapi.Depends(Settings),
):
    query = Enrollments.query.filter_by(business_id=business_id)
    if user_id:
        query = query.filter_by(user_id=user_id)
    if started_at:
        query = query.filter(Enrollments.started_at >= started_at)
    if expired_at:
        query = query.filter(Enrollments.expired_at <= expired_at)
    if plan:
        query = query.filter(Enrollments.plan == plan)
    if on_item:
        query = query.filter_by(on_item=on_item)
    if resources:
        for resource_name, resource_value in resources.items():
            query = query.filter(
                func.jsonb_extract_path_text(Enrollments.resources, resource_name)
                == str(resource_value)
            )
    return query.all()


##### get single Enrollments ####
@router.get("/enrollments/{enrollments_id}", response_model=Enrollments)
async def get_enrollment(
    """ Rerurn single Enrollments """
    enrollments_id: uuid.UUID, settings: Settings = fastapi.Depends(Settings)
):
    return Enrollments.query.get(enrollments_id)


##### create an Enrollment ####
@router.post("/enrollments", response_model=Enrollments)
async def create_enrollment(
    """ Create an Enrollments """"
    business_id: uuid.UUID,
    user_id: uuid.UUID,
    invoice_id: uuid.UUID,
    plan: dict,
    on_item: str,
    resources: dict,
    settings: Settings = fastapi.Depends(Settings),
):
    enrollment = Enrollments(
        business_id=business_id,
        user_id=user_id,
        invoice_id=invoice_id,
        plan=plan,
        on_item=on_item,
        resources=resources,
    )

    db.session.add(enrollment)
    db.session.commit()
    return enrollment

##### update an Enrollment ####
@router.put("/enrollments/{enrollments_id}", response_model=Enrollments)
async def update_enrollment(
    """ Update an Enrollments """
    enrollments_id: uuid.UUID,
    business_id: uuid.UUID,
    user_id: uuid.UUID,
    invoice_id: uuid.UUID,
    plan: dict,
    on_item: str,
    resources: dict,
    settings: Settings = fastapi.Depends(Settings),
):
    enrollment = Enrollments.query.get(enrollments_id)
    enrollment.business_id = business_id
    enrollment.user_id = user_id
    enrollment.invoice_id = invoice_id
    enrollment.plan = plan
    enrollment.on_item = on_item
    enrollment.resources = resources

    db.session.commit()
    return enrollment


##### delete an Enrollment ####
@router.delete("/enrollments/{enrollments_id}", response_model=Enrollments)
async def delete_enrollment(
    """ Delete an Enrollments """
    enrollments_id: uuid.UUID,
    settings: Settings = fastapi.Depends(Settings),
):
    enrollment = Enrollments.query.get(enrollments_id)
    enrollment.is_deleted = True

    db.session.commit()
    return enrollment


#### Usages APIs ####

##### get list of Usages #####
@router.get("/usages", response_model=list[Usages])
async def get_usages(
    """ Rerurn list of Usages """
    business_id: uuid.UUID,
    user_id: Optional[uuid.UUID] = None,
    resource: Optional[str] = None,
    volume: Optional[int] = None,
    on_item: Optional[str] = None,
    settings: Settings = fastapi.Depends(Settings),
):
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
@router.get("/usages/{usages_id}", response_model=Usages)
async def get_usage(usages_id: uuid.UUID, settings: Settings = fastapi.Depends(Settings)):
    """ Rerurn single Usages """
    return Usages.query.get(usages_id)


##### create an Usage ####
@router.post("/usages", response_model=uuid.UUID)
async def create_usage(
    """ Create an Usage """
    user_id: uuid.UUID,
    business_id: uuid.UUID,
    on_item: str,
    resource: str,
    volume: int,
    settings: Settings = fastapi.Depends(Settings),
):
    try:
        enrollment_id = Usages.check_enrollment_condition(None, None, None, Usages(
            user_id=user_id,
            business_id=business_id,
            on_item=on_item,
            resource=resource,
            volume=volume,
        ))
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
        Usages.change_enrollment_resource(None, None, Usages(
            change_type="decrease",
            enrollment_id=enrollment_id,
            resource=resource,
            volume=volume,
        ))
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
@router.delete("/usages/{usage_id}", response_model=uuid.UUID)
async def delete_usage(
    """ Delete an Usage """
    usage_id: uuid.UUID,
    settings: Settings = fastapi.Depends(Settings),
):
    usage = Usages.query.get(usage_id)
    if not usage:
        raise fastapi.HTTPException(status_code=404, detail="Usage not found")
    enrollment = Enrollments.query.get(usage.enrollment_id)
    Usages.change_enrollment_resource(None, None, Usages(
        change_type="increase",
        enrollment_id=enrollment.uid,
        resource=usage.resource,
        volume=usage.volume,
    ))
    db.session.commit()
    return usage_id

