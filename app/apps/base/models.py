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
"""
Plans/subscriptions/packages table description:
We are not supporting Plans/subscriptions/packages for now.
But we have a suggestion for the it's data model.
The data model for plans/subscriptions/packages is as follows:
- uid: Unique identifier for the plan (uuid)
- created_at: Date and time the plan was created (datetime)
- updated_at: Date and time the plan was last updated (datetime)
- metadata: Additional metadata for the plan (null)
- is_deleted: Indicates if the plan is active or not (false)
- business_id: Unique identifier for the business (uuid)
- name: Name of the plan (e.g., "20G monthly")
- description: Description of the plan (e.g., "Unlimited data for 20GB")
- price: Price of the plan (e.g., 100)
- currency: Currency of the price (e.g., "KT")
- is_active: Indicates if the plan is active for enrollment (true or false)
- category: Category of the plan (empty string)
- data: Container for plan details
  - duration: Duration of the plan in days (e.g., 90)
  - resources: List of resource limits
    - resource: Name of the resource (e.g., "API Calls")
    - limit: Amount of the resource limit (e.g., 1000)
  - on_items: List of specific items (null or empty)
"""

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



class Usages(ImmutableBase):
   """
   usages table description:
   - it is an immutable table.
   - After "approve_usage" respond yes, it will create a new row in usages table.
   - it has a "type" attribute, the possible values are:
        - "ENROLLMENT" : when user enrolled for a subscription/plan/package. in this case the "metadata" will contain the plan data and remain_resources will increase in comparision with the previous record in usages table.
        - "USAGE" : when user try to use a product that included in the subscription/plan/package. in this case the remain_resources will decrease in comparision with the previous record in usages table.
   - this table is contains with:
       - uid
       - created_at
       - metadata
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
   business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("Business.uid"), index=True)
   user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("User.uid"), index=True)
   enrollment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("Enrollments.uid"), index=True)
   on_item: Mapped[str] = mapped_column(index=True)
   resource: Mapped[str] = mapped_column(index=True)
   volume: Mapped[int] = mapped_column(index=True)
   remain_resources: Mapped[dict] = mapped_column(JSON, nullable=False)




    """
    A function called "add_enrollment_to_usages" add an enrollment to usages table.
    After an enrollment added to enrollments table, there should be a new record in usages table.
    For a user_id in a business_id and on_item, resource and volume, create a new record in usages table. if there is a similar record in usages table, then increase the remain_resources by the new volume. if there is not, create a new record.
    Args:
        user_id (uuid.UUID): The ID of the user.
        business_id (uuid.UUID): The ID of the business.
        on_item (str): The specific item to check.
        resource (str): The resource that user requested to make a usage.
        volume (int): The volume that user requested to make a usage.
    """
    

def usage_checker(user_id: uuid.UUID, business_id: uuid.UUID, on_item=None, resource=None, volume=None):
    """
    A function called "usage_checker" checks if a user has an active enrollment that can fulfill the requested usage.
    Args:
        user_id (uuid.UUID): The ID of the user.
        business_id (uuid.UUID): The ID of the business.
        on_item (str, optional): The specific item to check. Defaults to None.
        resource (str): The resource that user requested to make a usage.
        volume (int): The volume that user requested to make a usage.

    Returns:
        Tuple[Enrollments, Dict[str, int]]: The enrollment and remaining resources if the usage can be fulfilled.
        Tuple[None, str]: An error message if the usage cannot be fulfilled.
    - The function performs the following steps:
        - Get all active enrollments for the user in the requested business.
        - If an on_item is specified, filter the enrollments.plan.data.on_item to include only those
          that have the requested on_item.
        - Select the enrollment that expires soonest.
        - filter Usages table with the selected enrollment id. From Usages.remain_resources.resource table, Check if the remaining resources volume in the selected enrollment can satisfy
          the requested usage. 
        - If enough resource volume are available, return the enrollment_id and current
          remaining resources.
        - If no enrollment can satisfy the request, return an error message.
    """
    


