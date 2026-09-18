"""Pydantic request/response schemas.

These are the validation boundary: anything that reaches a route handler has
already been checked for type, length and range. Response models also act as a
whitelist - `password_hash` can never leak because it is not declared here.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import QuotationStatus, RFQStatus, UserRole

# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    # 72 bytes is bcrypt's hard limit; anything longer would be silently ignored.
    password: str = Field(min_length=8, max_length=72)
    role: UserRole
    company_name: str | None = Field(default=None, max_length=160)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("name", "company_name")
    @classmethod
    def strip_text(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: UserRole
    company_name: str | None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# --------------------------------------------------------------------------
# RFQ
# --------------------------------------------------------------------------


class RFQCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    quantity: int = Field(gt=0, le=10_000_000)
    unit: str = Field(default="units", min_length=1, max_length=40)
    delivery_location: str = Field(min_length=2, max_length=200)
    deadline: date

    @field_validator("deadline")
    @classmethod
    def deadline_in_future(cls, v: date) -> date:
        if v < date.today():
            raise ValueError("Deadline cannot be in the past")
        return v

    @field_validator("title", "description", "delivery_location", "unit")
    @classmethod
    def strip_text(cls, v: str) -> str:
        return v.strip()


class RFQUpdate(BaseModel):
    """Partial update.

    Which of these fields are actually accepted depends on whether the RFQ has
    quotations yet - see `routers/rfqs.py`. Once suppliers have quoted, the
    commercial terms are frozen so nobody is bidding against a moving target.
    """

    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, min_length=10, max_length=5000)
    quantity: int | None = Field(default=None, gt=0, le=10_000_000)
    unit: str | None = Field(default=None, min_length=1, max_length=40)
    delivery_location: str | None = Field(default=None, min_length=2, max_length=200)
    deadline: date | None = None
    status: RFQStatus | None = None

    @field_validator("deadline")
    @classmethod
    def deadline_in_future(cls, v: date | None) -> date | None:
        if v is not None and v < date.today():
            raise ValueError("Deadline cannot be in the past")
        return v


class BuyerPublic(BaseModel):
    """What a supplier is allowed to see about a buyer. No email address."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    company_name: str | None


class RFQOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    quantity: int
    unit: str
    delivery_location: str
    deadline: date
    status: RFQStatus
    created_at: datetime
    updated_at: datetime
    buyer: BuyerPublic
    is_expired: bool
    quotation_count: int = 0


class RFQListOut(BaseModel):
    items: list[RFQOut]
    total: int
    page: int
    page_size: int


# --------------------------------------------------------------------------
# Quotation
# --------------------------------------------------------------------------


class QuotationCreate(BaseModel):
    price: Decimal = Field(gt=0, le=Decimal("9999999999.99"), decimal_places=2)
    delivery_days: int = Field(gt=0, le=3650)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("notes")
    @classmethod
    def strip_notes(cls, v: str | None) -> str | None:
        return v.strip() if v else None


class SupplierPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    company_name: str | None


class RFQSummary(BaseModel):
    """Trimmed RFQ, embedded in a supplier's own quotation list."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    status: RFQStatus
    deadline: date


class QuotationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rfq_id: int
    price: Decimal
    delivery_days: int
    notes: str | None
    status: QuotationStatus
    created_at: datetime
    updated_at: datetime
    supplier: SupplierPublic


class QuotationWithRFQOut(QuotationOut):
    rfq: RFQSummary


class ErrorOut(BaseModel):
    detail: str
