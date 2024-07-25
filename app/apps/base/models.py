import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import Mapped, declared_attr, mapped_column
from sqlalchemy.sql import func
from sqlalchemy import event

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


## base Apps are below


### ENROLLMENTS


class Enrollments(BaseEntity):
   """ Enrollments table description:
   - After a user has a successful payment for a subscription/plan/package, a new entry is created in the enrollments table.
   - This table contains with the user_id, business_id and the subscription/plan/package data, start_at, expired_at, is_deleted are also added in this table.
   - is_deleted will be true when the user cancels the subscription/plan/package.
   - The plan data is based on a json object(the json object is the plan record which bought by user).
   - start_at will be in the day zero, all plan started at the time of purchase.
   - expired_at will be calculate based on plan data of duration and start_at.
   - add a metadata for everything user want to add.
   - plans have a filed of "resources" that business charge user for them.
       - this filed contain a list of resources and amount of each resource. like  "resources : [ {  "resource": "image", "limit": 28 } ]"
   """


   __tablename__ = "enrollments"


   uid: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, unique=True, index=True)
   user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("User.uid"), index=True)
   business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("Business.uid"), index=True)
   plan: Mapped[dict] = mapped_column(JSON, nullable=False)
   start_at: Mapped[datetime] = mapped_column(default=datetime.now(timezone.utc))
   expired_at: Mapped[datetime] = mapped_column(default=lambda: None)
   is_deleted: Mapped[bool] = mapped_column(default=False)
   created_at: Mapped[datetime] = mapped_column(default=datetime.now(timezone.utc), index=True)
   updated_at: Mapped[datetime] = mapped_column(default=datetime.now(timezone.utc), onupdate=func.now())
   metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)


def calculate_expired_at(plan: dict) -> datetime:
   """
   Calculate the expired_at time based on the plan duration.
   The plan duration is in days.
   """
   if "duration" in plan:
       return datetime.now(timezone.utc) + timedelta(days=plan["duration"])
   else:
       raise ValueError("Missing duration in plan")




@event.listens_for(Enrollments.plan, "set", retval=True)
def calculate_expired_at(target, value, oldvalue, initiator):
   if value is not None and "duration" in value:
       target.expired_at = calculate_expired_at(value)
   return value




### USAGES


"""
- when user try to use a service/product that is not free, business will ask us if this user have any active enrollmemt to use this product or not.
- A function called "approve_usage" will check if this user have any active enrollmemt to use this product or not.
- "approve_usage" actions:
   - get all active(not expired) enrollments for user_id in the requested business_id
   -


"""




class Usages(ImmutableBase):
   """
   usages table description:
   - it is an immutable table.
   - the    function will call. the respond:
       - if yes, then it will create a new row in usages table.
       - if no, then the ValueError is "There are no sufficient plans to approve this request")
   - this table is contains with:
       - uid
       - created_at
       - metadata
       - is_deleted
       - business_id
       - user_id
       - enrollment_id
       - on_item
       - resource
       - volume
       - remain_resources( a list of resource and limit)
   """
   __tablename__ = "usages"


   uid: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, unique=True, index=True)
   created_at: Mapped[datetime] = mapped_column(default=datetime.now(timezone.utc), index=True)
   metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
   is_deleted: Mapped[bool] = mapped_column(default=False)
   business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("Business.uid"), index=True)
   user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("User.uid"), index=True)
   enrollment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("Enrollments.uid"), index=True)
   on_item: Mapped[str] = mapped_column(index=True)
   resource: Mapped[str] = mapped_column(index=True)
   volume: Mapped[int] = mapped_column(index=True)
   remain_resources: Mapped[dict] = mapped_column(JSON, nullable=False)

