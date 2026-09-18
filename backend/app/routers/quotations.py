"""Quotation endpoints.

Visibility rules enforced here:
  * A supplier sees only their own quotations, never a competitor's price.
  * A buyer sees every quotation on an RFQ they own, and none on anyone else's.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.deps import BuyerUser, DbSession, SupplierUser
from app.models import RFQ, Quotation, QuotationStatus, RFQStatus
from app.schemas import QuotationCreate, QuotationOut, QuotationWithRFQOut

router = APIRouter(tags=["quotations"])


def _get_rfq_or_404(db, rfq_id: int) -> RFQ:
    rfq = db.get(RFQ, rfq_id)
    if rfq is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RFQ not found")
    return rfq


@router.post(
    "/api/rfqs/{rfq_id}/quotations",
    response_model=QuotationOut,
    status_code=status.HTTP_201_CREATED,
)
def submit_quotation(
    rfq_id: int, payload: QuotationCreate, supplier: SupplierUser, db: DbSession
) -> QuotationOut:
    """Submit a quotation, or revise the one already submitted for this RFQ.

    The (rfq_id, supplier_id) unique constraint means a supplier has exactly
    one live quote per RFQ, so re-submitting is an update rather than an error.
    """
    rfq = _get_rfq_or_404(db, rfq_id)

    # Every one of these checks is server-side. The UI hides the form in these
    # cases too, but a hidden form is a convenience, not a security control.
    if rfq.status != RFQStatus.OPEN:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This RFQ is {rfq.status.value} and is no longer accepting quotations",
        )
    if rfq.is_expired:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The deadline for this RFQ has passed",
        )

    existing = db.scalar(
        select(Quotation).where(
            Quotation.rfq_id == rfq.id, Quotation.supplier_id == supplier.id
        )
    )

    if existing:
        if existing.status != QuotationStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Your quotation was already {existing.status.value} and cannot be changed",
            )
        existing.price = payload.price
        existing.delivery_days = payload.delivery_days
        existing.notes = payload.notes
        quotation = existing
    else:
        quotation = Quotation(
            rfq_id=rfq.id,
            supplier_id=supplier.id,
            price=payload.price,
            delivery_days=payload.delivery_days,
            notes=payload.notes,
        )
        db.add(quotation)

    try:
        db.commit()
    except IntegrityError:
        # Lost a race with a concurrent submit from the same supplier.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already submitted a quotation for this RFQ",
        )

    db.refresh(quotation)
    return QuotationOut.model_validate(quotation)


@router.get("/api/rfqs/{rfq_id}/quotations", response_model=list[QuotationOut])
def list_rfq_quotations(rfq_id: int, buyer: BuyerUser, db: DbSession) -> list[QuotationOut]:
    """All quotations on one of the buyer's own RFQs, cheapest first."""
    rfq = _get_rfq_or_404(db, rfq_id)
    if rfq.buyer_id != buyer.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RFQ not found")

    quotations = db.scalars(
        select(Quotation)
        .where(Quotation.rfq_id == rfq.id)
        .options(selectinload(Quotation.supplier))
        .order_by(Quotation.price.asc(), Quotation.delivery_days.asc())
    ).all()
    return [QuotationOut.model_validate(q) for q in quotations]


@router.get("/api/quotations/mine", response_model=list[QuotationWithRFQOut])
def my_quotations(
    supplier: SupplierUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[QuotationWithRFQOut]:
    quotations = db.scalars(
        select(Quotation)
        .where(Quotation.supplier_id == supplier.id)
        .options(selectinload(Quotation.supplier), selectinload(Quotation.rfq))
        .order_by(Quotation.created_at.desc())
        .limit(limit)
    ).all()
    return [QuotationWithRFQOut.model_validate(q) for q in quotations]


@router.post("/api/quotations/{quotation_id}/accept", response_model=QuotationOut)
def accept_quotation(quotation_id: int, buyer: BuyerUser, db: DbSession) -> QuotationOut:
    """Award the RFQ to one supplier.

    One transaction does three things: mark this quote accepted, reject every
    sibling, and move the RFQ to `awarded`. Either all of it lands or none of
    it does - there is no window where two quotes look accepted at once.
    """
    quotation = db.get(Quotation, quotation_id)
    if quotation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found"
        )

    rfq = db.get(RFQ, quotation.rfq_id)
    if rfq is None or rfq.buyer_id != buyer.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found"
        )

    if rfq.status == RFQStatus.AWARDED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This RFQ has already been awarded",
        )

    for sibling in db.scalars(select(Quotation).where(Quotation.rfq_id == rfq.id)).all():
        sibling.status = (
            QuotationStatus.ACCEPTED if sibling.id == quotation.id else QuotationStatus.REJECTED
        )

    rfq.status = RFQStatus.AWARDED
    db.commit()
    db.refresh(quotation)
    return QuotationOut.model_validate(quotation)
