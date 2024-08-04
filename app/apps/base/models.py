import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import Mapped, declared_attr, mapped_column
from sqlalchemy.sql import func

# Base = declarative_base()


@as_declarative()
class BaseEntity:
    id: Any
    __name__: str
    __abstract__ = True

    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    uid: Mapped[uuid.UUID] = mapped_column(
        # pgUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        # DateTime,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), onupdate=func.now()
    )
    is_deleted: Mapped[bool] = mapped_column(
        default=False
    )  # Column(Boolean, default=False)
    metadata: Mapped[dict | None] = mapped_column(
        nullable=True
    )  # Column(JSON, nullable=True)
    # name: Mapped[str | None] = mapped_column(nullable=True)

    # def __init__(self, **kwargs):
    #     super().__init__(**kwargs)
    #     self.uid = uuid.uuid4()
    #     self.created_at = datetime.now(timezone.utc)
    #     self.updated_at = datetime.now(timezone.utc)
    #     self.is_deleted = False
    #     self.metadata = None


class ImmutableBase(BaseEntity):
    __abstract__ = True

    @staticmethod
    def prevent_update(mapper, connection, target):
        if connection.in_transaction() and target.id is not None:
            raise ValueError("Updates are not allowed for this object")

    @classmethod
    def __declare_last__(cls):
        event.listen(cls, "before_update", cls.prevent_update)


Base = BaseEntity


class OwnedEntity(BaseEntity):
    __abstract__ = True

    user_id: Mapped[uuid.UUID] = mapped_column(index=True)
    # Column(pgUUID(as_uuid=True), index=True)


class BusinessEntity(BaseEntity):
    __abstract__ = True

    business_id: Mapped[uuid.UUID] = mapped_column(index=True)
    # Column(pgUUID(as_uuid=True), index=True)


class BusinessOwnedEntity(BaseEntity):
    __abstract__ = True

    business_id: Mapped[uuid.UUID] = mapped_column(index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(index=True)


class OwnedEntity(BaseEntity):
    __abstract__ = True

    owner_id: Mapped[uuid.UUID] = mapped_column(index=True)


class BusinessEntity(BaseEntity):
    __abstract__ = True

    business_id: Mapped[uuid.UUID] = mapped_column(index=True)


class BusinessOwnedEntity(BusinessEntity, OwnedEntity):
    __abstract__ = True

    # owner_id: Mapped[uuid.UUID] = mapped_column(index=True)
    # business_id: Mapped[uuid.UUID] = mapped_column(index=True)


class ImmutableBase(BaseEntity):
    __abstract__ = True

    @staticmethod
    def prevent_update(mapper, connection, target):
        if connection.in_transaction() and target.id is not None:
            raise ValueError("Updates are not allowed for this object")

    @classmethod
    def __declare_last__(cls):
        event.listen(cls, "before_update", cls.prevent_update)


class ImmutableOwnedEntity(ImmutableBase, OwnedEntity):
    __abstract__ = True


class ImmutableBusinessEntity(ImmutableBase, BusinessEntity):
    __abstract__ = True


class ImmutableBusinessOwnedEntity(ImmutableBase, BusinessOwnedEntity):
    __abstract__ = True

#### End of BaseModel ####


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
    started_at: Mapped[datetime] = mapped_column(default=datetime.now(timezone.utc), index=True)
    expired_at: Mapped[datetime] = mapped_column(index=True)
    plan: Mapped[dict] = mapped_column(nullable=True)
    on_item: Mapped[str] = mapped_column(nullable=True)
    resources: Mapped[dict] = mapped_column(nullable=True)
    remain_resources: Mapped[dict] = mapped_column(nullable=True)

    @validates("expired_at")
    def expired_at_calculator(self, key, expired_at):
        if expired_at is None:
            plan = self.plan
            if plan is None:
                return None
            duration = plan.get("duration")
            if duration is None:
                return None
            started_at = self.started_at
            if started_at is None:
                return None
            return started_at + timedelta(days=duration)
        return expired_at
    @classmethod
    def __init_subclass__(cls):
        super().__init_subclass__()
        event.listen(cls, 'before_insert', cls.set_remain_resource)

    @classmethod
    def set_remain_resource(cls, mapper, connection, target):
        """
        at the moment of record creation the remain_resources is empthy. it should give the value of "enrollments.resources" at that momnet once.
        """
        enrollment = connection.execute(
            select(Enrollments).where(
                Enrollments.uid == target.enrollment_id
            )
        ).first()
        target.remain_resources = enrollment.resources.copy()

    
##### End of Enrollments ####

#### Start of Usages ####
class Usages(ImmutableBase):
    """
    the Usages is an immutable table. using class ImmutableBusinessOwnedEntity.
    """
    __tablename__ = "usages"

    enrollment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("enrollments.uid"), index=True)
    resource: Mapped[str] = mapped_column(index=True)
    volume: Mapped[int] = mapped_column()
    on_item: Mapped[str] = mapped_column(index=True)

    @classmethod
    def __init_subclass__(cls):
        super().__init_subclass__()
        event.listen(cls, 'before_insert', cls.check_enrollment_condition)

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
            func.jsonb_exists(Enrollments.remain_resources, requested_resource)
        ).all()
        if enrollments is None:
            raise ValueError("There is no valid enrollment for the requested usage.")
        
        valid_enrollments = None
        for enrollment in enrollments:
                        
            if requested_volume > enrollment.remain_resources[requested_resource]:
                raise ValueError(f"{requested_resource} has {enrollment.remain_resources[requested_resource]} resources remain, but requested {requested_volume} resources. it is remaining.")
            
            if valid_enrollment is None or enrollment.expired_at < valid_enrollment.expired_at:
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
            select(Enrollments).where(
                Enrollments.uid == target.enrollment_id
            )
        ).first()
        remain_resources = enrollment.remain_resources
        resource_volume = remain_resources[target.resource]
        if change_type == "decrease":
            remain_resources[target.resource] = resource_volume - target.volume
        elif change_type == "increase":
            remain_resources[target.resource] = resource_volume + target.volume
        connection.execute(
            Enrollments.update().where(
                Enrollments.uid == target.enrollment_id
            ).values(
                remain_resources=remain_resources
            )
        )

#### End of Usages ####

