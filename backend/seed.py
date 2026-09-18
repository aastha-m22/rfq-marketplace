"""Populate the database with demo accounts and sample RFQs.

Run from the backend directory:  python seed.py

Safe to re-run: it clears the three tables first.
"""

from datetime import date, timedelta
from decimal import Decimal

from app.database import Base, SessionLocal, engine
from app.models import RFQ, Quotation, QuotationStatus, RFQStatus, User, UserRole
from app.security import hash_password

DEMO_PASSWORD = "password123"

BUYERS = [
    ("Aarav Sharma", "buyer@demo.com", "Sharma Industries"),
    ("Neha Verma", "buyer2@demo.com", "Verma Constructions"),
]

SUPPLIERS = [
    ("Rohit Nair", "supplier@demo.com", "Nair Metal Works"),
    ("Priya Menon", "supplier2@demo.com", "Menon Packaging Co"),
]

RFQS = [
    {
        "title": "500 galvanised steel brackets",
        "description": (
            "L-shaped galvanised steel brackets, 4mm thickness, powder coated "
            "RAL 7016. Must meet IS 2062 grade. Sample approval required before "
            "the full run."
        ),
        "quantity": 500,
        "unit": "pieces",
        "delivery_location": "Pune, Maharashtra",
        "days_out": 21,
    },
    {
        "title": "Corrugated shipping cartons - monthly supply",
        "description": (
            "5-ply corrugated cartons, 450x300x300mm, single colour flexo print. "
            "Recurring monthly requirement; quote per-unit price at this volume."
        ),
        "quantity": 10000,
        "unit": "cartons",
        "delivery_location": "Ludhiana, Punjab",
        "days_out": 14,
    },
    {
        "title": "Industrial LED high-bay lighting, 150W",
        "description": (
            "150W LED high-bay fixtures for a 2000 sqm warehouse retrofit. IP65, "
            "5000K, minimum 5-year warranty. Installation not required."
        ),
        "quantity": 80,
        "unit": "units",
        "delivery_location": "Chennai, Tamil Nadu",
        "days_out": 30,
    },
    {
        "title": "CNC machined aluminium housings",
        "description": (
            "6061-T6 aluminium enclosures machined to drawing, anodised black. "
            "Tolerance +/-0.05mm. Drawings shared after NDA."
        ),
        "quantity": 250,
        "unit": "pieces",
        "delivery_location": "Bengaluru, Karnataka",
        "days_out": 45,
    },
    {
        "title": "Cotton work uniforms with logo embroidery",
        "description": (
            "Two-piece cotton drill work uniforms, sizes S-XXL assorted, with "
            "chest logo embroidery. Size breakdown provided on request."
        ),
        "quantity": 300,
        "unit": "sets",
        "delivery_location": "Surat, Gujarat",
        "days_out": 10,
    },
]


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Clear children before parents so foreign keys stay satisfied.
        db.query(Quotation).delete()
        db.query(RFQ).delete()
        db.query(User).delete()
        db.commit()

        buyers = [
            User(
                name=n,
                email=e,
                password_hash=hash_password(DEMO_PASSWORD),
                role=UserRole.BUYER,
                company_name=c,
            )
            for n, e, c in BUYERS
        ]
        suppliers = [
            User(
                name=n,
                email=e,
                password_hash=hash_password(DEMO_PASSWORD),
                role=UserRole.SUPPLIER,
                company_name=c,
            )
            for n, e, c in SUPPLIERS
        ]
        db.add_all(buyers + suppliers)
        db.commit()

        rfqs = []
        for i, spec in enumerate(RFQS):
            rfq = RFQ(
                buyer_id=buyers[i % len(buyers)].id,
                title=spec["title"],
                description=spec["description"],
                quantity=spec["quantity"],
                unit=spec["unit"],
                delivery_location=spec["delivery_location"],
                deadline=date.today() + timedelta(days=spec["days_out"]),
                status=RFQStatus.OPEN,
            )
            rfqs.append(rfq)
        db.add_all(rfqs)
        db.commit()

        # A couple of quotations so the buyer dashboard is not empty on login.
        db.add_all(
            [
                Quotation(
                    rfq_id=rfqs[0].id,
                    supplier_id=suppliers[0].id,
                    price=Decimal("187500.00"),
                    delivery_days=18,
                    notes="Ex-works Pune. Sample dispatched within 4 days of PO.",
                    status=QuotationStatus.PENDING,
                ),
                Quotation(
                    rfq_id=rfqs[0].id,
                    supplier_id=suppliers[1].id,
                    price=Decimal("201000.00"),
                    delivery_days=12,
                    notes="Faster turnaround, freight included to your dock.",
                    status=QuotationStatus.PENDING,
                ),
                Quotation(
                    rfq_id=rfqs[1].id,
                    supplier_id=suppliers[1].id,
                    price=Decimal("164000.00"),
                    delivery_days=9,
                    notes="Price held for 3 months on a rolling monthly order.",
                    status=QuotationStatus.PENDING,
                ),
            ]
        )
        db.commit()

        print(f"Seeded {len(buyers)} buyers, {len(suppliers)} suppliers, {len(rfqs)} RFQs.")
        print(f"\nLog in with any of these (password: {DEMO_PASSWORD}):")
        for _, email, _ in BUYERS:
            print(f"  buyer    {email}")
        for _, email, _ in SUPPLIERS:
            print(f"  supplier {email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
