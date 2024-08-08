import uuid
from datetime import datetime

from fastapi import APIRouter
from sqlalchemy.sql import func

from .models import Enrollments
from .schemas import EnrollmentSchema

router = APIRouter(prefix="/enrollments", tags=["Enrollment"])

##### get list of Enrollments #####


@router.get("/enrollments", response_model=list[EnrollmentSchema])
async def get_enrollments(
    business_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
    started_at: datetime | None = None,
    expired_at: datetime | None = None,
    plan: dict | None = None,
    on_item: str | None = None,
    resources: dict | None = None,
):
    """Rerurn list of Enrollments"""
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
@router.get("/enrollments/{enrollments_id}", response_model=EnrollmentSchema)
async def get_enrollment(enrollments_id: uuid.UUID):
    """Rerurn single Enrollments"""
    return Enrollments.query.get(enrollments_id)


##### create an Enrollment ####
@router.post("/enrollments", response_model=EnrollmentSchema)
async def create_enrollment(
    business_id: uuid.UUID,
    user_id: uuid.UUID,
    invoice_id: uuid.UUID,
    plan: dict,
    on_item: str,
    resources: dict,
):
    """Create an Enrollments"""
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
@router.put("/enrollments/{enrollments_id}", response_model=EnrollmentSchema)
async def update_enrollment(
    enrollments_id: uuid.UUID,
    business_id: uuid.UUID,
    user_id: uuid.UUID,
    invoice_id: uuid.UUID,
    plan: dict,
    on_item: str,
    resources: dict,
):
    """Update an Enrollments"""
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
@router.delete("/enrollments/{enrollments_id}", response_model=EnrollmentSchema)
async def delete_enrollment(
    enrollments_id: uuid.UUID,
):
    """Delete an Enrollments"""
    enrollment = Enrollments.query.get(enrollments_id)
    enrollment.is_deleted = True

    db.session.commit()
    return enrollment
