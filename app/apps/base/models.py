import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, event, select
from sqlalchemy.ext.asyncio import AsyncSession
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
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), onupdate=func.now()
    )
    is_deleted: Mapped[bool] = mapped_column(default=False)
    meta_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # name: Mapped[str | None] = mapped_column(nullable=True)

    @classmethod
    async def get_item(
        cls,
        session: AsyncSession,
        uid: uuid.UUID,
        user_id: uuid.UUID = None,
        business_name: str = None,
    ):
        query = select(cls).filter_by(uid=uid, is_deleted=False)

        # Apply user_id filtering if the model has a user_id attribute
        if hasattr(cls, "user_id"):
            if user_id is None:
                raise ValueError("User is required for this model")
            query = query.filter_by(user_id=user_id)
        if hasattr(cls, "business_name"):
            if business_name is None:
                raise ValueError("Business name is required for this model")
            query = query.filter_by(business_name=business_name)

        # Execute the query
        result = await session.execute(query)
        item = result.scalar_one_or_none()
        return item


Base = BaseEntity


class OwnedEntity(BaseEntity):
    __abstract__ = True

    user_id: Mapped[uuid.UUID] = mapped_column(index=True)


class BusinessEntity(BaseEntity):
    __abstract__ = True

    business_name: Mapped[str] = mapped_column(index=True)


class BusinessOwnedEntity(OwnedEntity, BusinessEntity):
    __abstract__ = True


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
