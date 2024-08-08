import uuid
from datetime import datetime, timezone

from apps.base.models import ImmutableBase
from apps.enrollments.models import Enrollments
from sqlalchemy import ForeignKey, event
from sqlalchemy.future import select
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func


#### Start of Usages ####
class Usages(ImmutableBase):
    """
    the Usages is an immutable table. using class ImmutableBusinessOwnedEntity.
    """

    __tablename__ = "usages"

    enrollment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("enrollments.uid"), index=True
    )
    resource: Mapped[str] = mapped_column(index=True)
    volume: Mapped[int] = mapped_column()
    on_item: Mapped[str] = mapped_column(index=True)

    @classmethod
    def __init_subclass__(cls):
        super().__init_subclass__()
        event.listen(cls, "before_insert", cls.check_enrollment_condition)

    @classmethod
    def check_enrollment_condition(cls, mapper, connection, target):
        """
        This function checks if there is a valid enrollment that can be used for the requested usage.
        If there is one, it returns it as a valid enrollment. Otherwise, it raises a ValueError.

        The function checks the following items from the usages request:
        - user_id
        - business_id
        - on_item
        - resource: It checks if the requested resource exists in the remain_resources dictionary of the enrollment.
          The remain_resources is a dictionary that contains several resources and their corresponding values in the enrollment.
          For example: {"cpu": 1, "memory": 2, "disk": 3}.
          If the requested resource is not found in the remain_resources, a ValueError is raised mentioning the resource name.

        - expired_at: It checks if the expired_at field of the enrollment is greater than the current time.

        - volume: It checks if the requested volume is less than or equal to the remain resource value of the resource in the enrollment.
          If there is not enough resource value in the remain_resources, a ValueError is raised mentioning the resource name,
          the remain resource volume, and mentioning that it is remaining.

        at last, If there are multiple enrollments, the one with the smallest expired_at will be returned.
        """
        current_time = datetime.now(timezone.utc)
        requested_resource = target.resource
        requested_volume = target.volume
        requested_business_id = target.business_id
        requested_user_id = target.user_id
        requested_on_item = target.on_item

        enrollments = Enrollments.query.filter(
            Enrollments.user_id == requested_user_id,
            Enrollments.business_id == requested_business_id,
            Enrollments.on_item == requested_on_item,
            Enrollments.expired_at > current_time,
            func.jsonb_exists(Enrollments.remain_resources, requested_resource),
        ).all()
        if enrollments is None:
            raise ValueError("There is no valid enrollment for the requested usage.")

        valid_enrollments = None
        for enrollment in enrollments:

            if requested_volume > enrollment.remain_resources[requested_resource]:
                raise ValueError(
                    f"{requested_resource} has {enrollment.remain_resources[requested_resource]} resources remain, but requested {requested_volume} resources. it is remaining."
                )

            if (
                valid_enrollment is None
                or enrollment.expired_at < valid_enrollment.expired_at
            ):
                valid_enrollments.append(enrollment)

        if valid_enrollments is None:
            raise ValueError("There is no valid enrollment for the requested usage.")

        if len(valid_enrollments) > 1:
            valid_enrollments.sort(key=lambda enrollment: enrollment.expired_at)
            valid_enrollment = valid_enrollments[0]
        else:
            valid_enrollment = valid_enrollments[0]

        return valid_enrollment

    @classmethod
    def write_usage(cls, mapper, connection, target):
        """
        a function to approve write a record on usages table if there is any valid enrollment by the response of check_enrollment_condition function.
        """
        enrollment_id = cls.check_enrollment_condition(mapper, connection, target)
        target.enrollment_id = enrollment_id

    @classmethod
    def change_enrollment_resource(cls, mapper, connection, target, change_type):
        """
        change the "reduce_enrollment_resource" to "change_enrollment_resource"
        as input get an enrollments_id and requested usage record and change_type : decrease or increase.
        change the the limit of resource in remain_resources in enrollment by corosponding value of resource in usage resource.
        """
        if change_type not in ["decrease", "increase"]:
            raise ValueError("change_type must be 'decrease' or 'increase'")
        enrollment = connection.execute(
            select(Enrollments).where(Enrollments.uid == target.enrollment_id)
        ).first()
        remain_resources = enrollment.remain_resources
        resource_volume = remain_resources[target.resource]
        if change_type == "decrease":
            remain_resources[target.resource] = resource_volume - target.volume
        elif change_type == "increase":
            remain_resources[target.resource] = resource_volume + target.volume
        connection.execute(
            Enrollments.update()
            .where(Enrollments.uid == target.enrollment_id)
            .values(remain_resources=remain_resources)
        )


#### End of Usages ####
