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
class Enrollments(BaseEntity):
    """
    enrollments is a mutable table using class BaseEntity.
    the model is mentiond in selected text.
    the "plan" field is an object. inner of plan, there is a field called "duration". the "expired_at" field of enrollments should be calculate by here using "duration" field of plan. add duration to "started_at".
    the "plan" field is also has a field "resources". the "remain_resource" field of enrollments is set to be equal to "resources" field of plan at the moment of record creation.
    
    """
    __tablename__ = "enrollments"

    uid: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True, unique=True)
    business_id: Mapped[uuid.UUID] = mapped_column(index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(index=True)
    invoice_id: Mapped[uuid.UUID] = mapped_column(index=True)
    started_at: Mapped[datetime] = mapped_column(default=datetime.now(timezone.utc), index=True)
    expired_at: Mapped[datetime] = mapped_column(index=True)
    plan: Mapped[dict] = mapped_column(nullable=True)
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
        target.remain_resources = target.plan.get('resources', {})

    
##### End of Enrollments ####

#### Start of Usages ####
class Usages(ImmutableBase):
    """
    the Usages is an immutable table. using class ImmutableBase.
    """
    __tablename__ = "usages"

    business_id: Mapped[uuid.UUID] = mapped_column(index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(index=True)
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
        a function to check if there is any enrollment that can be used for the requested usage.
        If there is one, so return it as a valid enrollment. Otherwise, if there is no valid enrollment, raise ValueError.
        """        
        enrollments = connection.execute(
            select(Enrollments).where(
                Enrollments.user_id == target.user_id,
                Enrollments.business_id == target.business_id,
                Enrollments.on_item == target.on_item,
                Enrollments.expired_at > datetime.now(timezone.utc)
            )
        ).all()
        if not enrollments:
            raise ValueError("No valid enrollment found")
        enrollment = min(enrollments, key=lambda e: e.expired_at)
        remain_resources = enrollment.remain_resources
        if remain_resources is None:
            raise ValueError("No remain resources found")
        resource_volume = remain_resources.get(target.resource)
        if resource_volume is None:
            raise ValueError("No resource volume found")
        if resource_volume < target.volume:
            raise ValueError("Remain resource volume is not enough")
        return enrollment.uid

    
    @classmethod
    def write_usage(cls, mapper, connection, target):
        """
        a function to approve write a record on usages table if there is any valid enrollment by the response of check_enrollment_condition function.
        """
        enrollment_id = cls.check_enrollment_condition(mapper, connection, target)
        target.enrollment_id = enrollment_id

    @classmethod
    def reduce_enrollment_resource(cls, mapper, connection, target):
        """
        when a record is created on usages table, we need to reduce the resource volume of the enrollment by the volume of the usage.
        """
        enrollment = connection.execute(
            select(Enrollments).where(
                Enrollments.uid == target.enrollment_id
            )
        ).first()
        remain_resources = enrollment.remain_resources
        resource_volume = remain_resources[target.resource]
        remain_resources[target.resource] = resource_volume - target.volume
        connection.execute(
            Enrollments.update().where(
                Enrollments.uid == target.enrollment_id
            ).values(
                remain_resources=remain_resources
            )
        )

#### End of Usages ####

