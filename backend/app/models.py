"""SQLAlchemy ORM models.

Three tables: users, rfqs, quotations.

Design notes
------------
* A user has exactly one role. A single account is either a buyer or a
  supplier, never both - this keeps authorization checks unambiguous.
* `quotations` has a UNIQUE (rfq_id, supplier_id) constraint so a supplier
  cannot spam an RFQ with multiple quotes. They update their existing one.
* Money is stored as Numeric(12, 2), never float, to avoid rounding errors.
* Composite index on (status, deadline) backs the supplier browse query,
  which always filters on both.
"""

from __future__ import annotations

import enum
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def enum_column(enum_cls: type[enum.Enum]) -> SAEnum:
    """Portable enum column.

    native_enum=False stores a VARCHAR guarded by a CHECK constraint instead of
    a Postgres ENUM type. Two reasons: the same DDL works on SQLite for local
    dev and tests, and adding a value later is an ordinary constraint change
    rather than an ALTER TYPE that locks the table.

    values_callable persists the lowercase `.value` ("buyer"), not the member
    name ("BUYER"), so what is in the database matches what the API returns.
    """
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=20,
        values_callable=lambda e: [member.value for member in e],
    )


class UserRole(str, enum.Enum):
    BUYER = "buyer"
    SUPPLIER = "supplier"


class RFQStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    AWARDED = "awarded"


class QuotationStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # Stored lowercase; unique index makes the login lookup O(log n).
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(enum_column(UserRole), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    rfqs: Mapped[list["RFQ"]] = relationship(back_populates="buyer", cascade="all, delete-orphan")
    quotations: Mapped[list["Quotation"]] = relationship(
        back_populates="supplier", cascade="all, delete-orphan"
    )


class RFQ(Base):
    __tablename__ = "rfqs"

    id: Mapped[int] = mapped_column(primary_key=True)
    buyer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit: Mapped[str] = mapped_column(String(40), nullable=False, default="units")
    delivery_location: Mapped[str] = mapped_column(String(200), nullable=False)
    deadline: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[RFQStatus] = mapped_column(
        enum_column(RFQStatus), default=RFQStatus.OPEN, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    buyer: Mapped[User] = relationship(back_populates="rfqs")
    quotations: Mapped[list["Quotation"]] = relationship(
        back_populates="rfq", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_rfq_quantity_positive"),
        # Supplier browse filters on status and orders/filters by deadline.
        Index("ix_rfqs_status_deadline", "status", "deadline"),
    )

    @property
    def is_expired(self) -> bool:
        return self.deadline < date.today()

    @property
    def accepts_quotes(self) -> bool:
        """An RFQ takes new quotes only while open and before its deadline."""
        return self.status == RFQStatus.OPEN and not self.is_expired


class Quotation(Base):
    __tablename__ = "quotations"

    id: Mapped[int] = mapped_column(primary_key=True)
    rfq_id: Mapped[int] = mapped_column(
        ForeignKey("rfqs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    delivery_days: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[QuotationStatus] = mapped_column(
        enum_column(QuotationStatus), default=QuotationStatus.PENDING, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    rfq: Mapped[RFQ] = relationship(back_populates="quotations")
    supplier: Mapped[User] = relationship(back_populates="quotations")

    __table_args__ = (
        # One quote per supplier per RFQ - enforced by the database, not just
        # by application code, so a race between two requests cannot bypass it.
        UniqueConstraint("rfq_id", "supplier_id", name="uq_quotation_rfq_supplier"),
        CheckConstraint("price > 0", name="ck_quotation_price_positive"),
        CheckConstraint("delivery_days > 0", name="ck_quotation_delivery_positive"),
    )
