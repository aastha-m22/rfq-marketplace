"""RFQ endpoints.

Route order matters: `/api/rfqs/mine` is declared before `/api/rfqs/{rfq_id}`,
otherwise FastAPI would try to parse "mine" as an integer id.
"""

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import selectinload

from app.deps import BuyerUser, CurrentUser, DbSession
from app.models import RFQ, Quotation, RFQStatus
from app.schemas import RFQCreate, RFQListOut, RFQOut, RFQUpdate

router = APIRouter(prefix="/api/rfqs", tags=["rfqs"])

# Fields a buyer may still change after suppliers have started quoting.
# Freezing the rest means nobody is bidding against a moving target.
EDITABLE_AFTER_QUOTES = {"description", "deadline", "status"}


def _serialize(rfq: RFQ, quotation_count: int) -> RFQOut:
    return RFQOut.model_validate(
        {
            **{c.name: getattr(rfq, c.name) for c in rfq.__table__.columns},
            "buyer": rfq.buyer,
            "is_expired": rfq.is_expired,
            "quotation_count": quotation_count,
        }
    )


def _with_counts(db, stmt: Select) -> list[RFQOut]:
    """Run an RFQ query and attach each row's quotation count.

    The count is a correlated scalar subquery so the whole page costs one
    round trip instead of one extra query per RFQ (the N+1 trap).
    """
    count_sq = (
        select(func.count(Quotation.id))
        .where(Quotation.rfq_id == RFQ.id)
        .correlate(RFQ)
        .scalar_subquery()
    )
    rows = db.execute(
        stmt.add_columns(count_sq.label("quotation_count")).options(selectinload(RFQ.buyer))
    ).all()
    return [_serialize(rfq, count) for rfq, count in rows]


def _get_rfq_or_404(db, rfq_id: int) -> RFQ:
    rfq = db.get(RFQ, rfq_id)
    if rfq is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RFQ not found")
    return rfq


def _count_quotes(db, rfq_id: int) -> int:
    return db.scalar(select(func.count(Quotation.id)).where(Quotation.rfq_id == rfq_id)) or 0


@router.post("", response_model=RFQOut, status_code=status.HTTP_201_CREATED)
def create_rfq(payload: RFQCreate, buyer: BuyerUser, db: DbSession) -> RFQOut:
    rfq = RFQ(**payload.model_dump(), buyer_id=buyer.id)
    db.add(rfq)
    db.commit()
    db.refresh(rfq)
    return _serialize(rfq, 0)


@router.get("", response_model=RFQListOut)
def browse_rfqs(
    user: CurrentUser,
    db: DbSession,
    q: Annotated[str | None, Query(max_length=200, description="Search title and description")] = None,
    location: Annotated[str | None, Query(max_length=200)] = None,
    rfq_status: Annotated[RFQStatus | None, Query(alias="status")] = None,
    include_expired: bool = False,
    sort: Literal["newest", "deadline"] = "newest",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 10,
) -> RFQListOut:
    """Browse the marketplace.

    Suppliers use this to find work. Buyers can see it too, but their own
    RFQs live at /api/rfqs/mine.
    """
    stmt = select(RFQ)

    if rfq_status is not None:
        stmt = stmt.where(RFQ.status == rfq_status)
    else:
        # The default view is "things I can still quote on".
        stmt = stmt.where(RFQ.status == RFQStatus.OPEN)

    if not include_expired:
        stmt = stmt.where(RFQ.deadline >= date.today())

    if q:
        # ILIKE keeps the search case-insensitive on Postgres; SQLAlchemy maps
        # it to LOWER(...) LIKE on SQLite, so local dev behaves the same.
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(or_(RFQ.title.ilike(pattern), RFQ.description.ilike(pattern)))

    if location:
        stmt = stmt.where(RFQ.delivery_location.ilike(f"%{location.strip()}%"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    order = RFQ.deadline.asc() if sort == "deadline" else RFQ.created_at.desc()
    stmt = stmt.order_by(order, RFQ.id.desc()).offset((page - 1) * page_size).limit(page_size)

    return RFQListOut(items=_with_counts(db, stmt), total=total, page=page, page_size=page_size)


@router.get("/mine", response_model=RFQListOut)
def my_rfqs(
    buyer: BuyerUser,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> RFQListOut:
    base = select(RFQ).where(RFQ.buyer_id == buyer.id)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    stmt = base.order_by(RFQ.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    return RFQListOut(items=_with_counts(db, stmt), total=total, page=page, page_size=page_size)


@router.get("/{rfq_id}", response_model=RFQOut)
def get_rfq(rfq_id: int, user: CurrentUser, db: DbSession) -> RFQOut:
    rfq = _get_rfq_or_404(db, rfq_id)
    return _serialize(rfq, _count_quotes(db, rfq.id))


@router.patch("/{rfq_id}", response_model=RFQOut)
def update_rfq(rfq_id: int, payload: RFQUpdate, buyer: BuyerUser, db: DbSession) -> RFQOut:
    rfq = _get_rfq_or_404(db, rfq_id)

    # 404 rather than 403 for someone else's RFQ: a stranger should not be able
    # to learn that a given id exists at all.
    if rfq.buyer_id != buyer.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RFQ not found")

    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update"
        )

    quote_count = _count_quotes(db, rfq.id)
    if quote_count > 0:
        frozen = sorted(set(changes) - EDITABLE_AFTER_QUOTES)
        if frozen:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"This RFQ already has {quote_count} quotation(s); "
                    f"{', '.join(frozen)} can no longer be changed. "
                    "Close it and post a new RFQ instead."
                ),
            )

    if "deadline" in changes and changes["deadline"] < rfq.deadline and quote_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A deadline can only be extended once suppliers have quoted",
        )

    if changes.get("status") == RFQStatus.AWARDED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An RFQ becomes awarded by accepting a quotation, not by direct edit",
        )

    for field, value in changes.items():
        setattr(rfq, field, value)

    db.commit()
    db.refresh(rfq)
    return _serialize(rfq, quote_count)


@router.delete("/{rfq_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rfq(rfq_id: int, buyer: BuyerUser, db: DbSession) -> None:
    rfq = _get_rfq_or_404(db, rfq_id)
    if rfq.buyer_id != buyer.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RFQ not found")

    if _count_quotes(db, rfq.id) > 0:
        # Suppliers have invested effort; deleting would destroy their record.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An RFQ with quotations cannot be deleted. Close it instead.",
        )

    db.delete(rfq)
    db.commit()
