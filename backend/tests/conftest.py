"""Test fixtures.

Each test gets a fresh in-memory SQLite database, so tests are isolated and
order-independent. `get_db` is overridden to hand out the test session.
"""

import os
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("JWT_SECRET", "test-secret-long-enough-for-hs256-hmac-key-abcdef")

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        # StaticPool keeps one connection, so the in-memory DB survives
        # across the sessions opened during a single test.
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def register(client, email, role, password="password123", name=None, company=None):
    resp = client.post(
        "/api/auth/register",
        json={
            "name": name or email.split("@")[0].title(),
            "email": email,
            "password": password,
            "role": role,
            "company_name": company or f"{role.title()} Co",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def buyer(client):
    return register(client, "buyer@example.com", "buyer")


@pytest.fixture
def other_buyer(client):
    return register(client, "buyer2@example.com", "buyer")


@pytest.fixture
def supplier(client):
    return register(client, "supplier@example.com", "supplier")


@pytest.fixture
def other_supplier(client):
    return register(client, "supplier2@example.com", "supplier")


@pytest.fixture
def rfq_payload():
    return {
        "title": "500 steel brackets",
        "description": "Galvanised steel brackets, 4mm, powder coated.",
        "quantity": 500,
        "unit": "pieces",
        "delivery_location": "Pune, India",
        "deadline": (date.today() + timedelta(days=14)).isoformat(),
    }


@pytest.fixture
def rfq(client, buyer, rfq_payload):
    resp = client.post(
        "/api/rfqs", json=rfq_payload, headers=auth_header(buyer["access_token"])
    )
    assert resp.status_code == 201, resp.text
    return resp.json()
