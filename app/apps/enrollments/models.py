import uuid
from datetime import datetime, timedelta, timezone

from apps.base.models import BusinessOwnedEntity
from pydantic import field_validator
from sqlalchemy import JSON, event
from sqlalchemy.future import select
from sqlalchemy.orm import Mapped, mapped_column


#### Start of Enrollments ####
class Enrollments(BusinessOwnedEntity):
    """
    enrollments is a mutable table using class BusinessOwnedEntity.
    the model is mentiond in selected text.
    the "plan" field is an object. inner of plan, there is a field called "duration". the "expired_at" field of enrollments should be calculate by here using "duration" field of plan. add duration to "started_at".
    the "plan" field is also has a field "resources". the "remain_resource" field of enrollments is set to be equal to "resources" field of plan at the moment of record creation.
    """

    __tablename__ = "enrollments"

    invoice_id: Mapped[uuid.UUID] = mapped_column(index=True)
    started_at: Mapped[datetime] = mapped_column(
        default=datetime.now(timezone.utc), index=True
    )
    expired_at: Mapped[datetime] = mapped_column(index=True)
    plan: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    on_item: Mapped[str] = mapped_column(nullable=True)
    resources: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )
    remain_resources: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    @field_validator("expired_at")
    def expired_at_calculator(cls, expired_at):
        if expired_at is None:
            plan = cls.plan
            if plan is None:
                return None
            duration = plan.get("duration")
            if duration is None:
                return None
            started_at = cls.started_at
            if started_at is None:
                return None
            return started_at + timedelta(days=duration)
        return expired_at

    @classmethod
    def __init_subclass__(cls):
        super().__init_subclass__()
        event.listen(cls, "before_insert", cls.set_remain_resource)

    @classmethod
    def set_remain_resource(cls, mapper, connection, target):
        """
        at the moment of record creation the remain_resources is empthy. it should give the value of "enrollments.resources" at that momnet once.
        """
        enrollment = connection.execute(
            select(Enrollments).where(Enrollments.uid == target.enrollment_id)
        ).first()
        target.remain_resources = enrollment.resources.copy()


##### End of Enrollments ####
