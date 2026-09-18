"""Authentication: registration, login, token handling."""

from tests.conftest import auth_header, register


def test_register_returns_token_and_user(client):
    data = register(client, "new@example.com", "buyer")
    assert data["access_token"]
    assert data["user"]["email"] == "new@example.com"
    assert data["user"]["role"] == "buyer"


def test_password_hash_is_never_returned(client):
    data = register(client, "secret@example.com", "buyer")
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]


def test_duplicate_email_is_rejected(client):
    register(client, "dupe@example.com", "buyer")
    resp = client.post(
        "/api/auth/register",
        json={
            "name": "Dupe",
            "email": "dupe@example.com",
            "password": "password123",
            "role": "supplier",
        },
    )
    assert resp.status_code == 409


def test_email_is_normalized_to_lowercase(client):
    register(client, "mixed@example.com", "buyer")
    # Registering the same address in different case must collide.
    resp = client.post(
        "/api/auth/register",
        json={
            "name": "Mixed",
            "email": "MIXED@example.com",
            "password": "password123",
            "role": "buyer",
        },
    )
    assert resp.status_code == 409


def test_short_password_is_rejected(client):
    resp = client.post(
        "/api/auth/register",
        json={"name": "Weak", "email": "weak@example.com", "password": "short", "role": "buyer"},
    )
    assert resp.status_code == 422


def test_invalid_role_is_rejected(client):
    resp = client.post(
        "/api/auth/register",
        json={
            "name": "Admin",
            "email": "admin@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    assert resp.status_code == 422


def test_login_succeeds_with_correct_password(client, buyer):
    resp = client.post(
        "/api/auth/login",
        json={"email": "buyer@example.com", "password": "password123"},
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_login_fails_with_wrong_password(client, buyer):
    resp = client.post(
        "/api/auth/login", json={"email": "buyer@example.com", "password": "wrongpassword"}
    )
    assert resp.status_code == 401


def test_login_does_not_reveal_whether_email_exists(client, buyer):
    """Unknown email and wrong password must be indistinguishable."""
    unknown = client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": "password123"}
    )
    wrong = client.post(
        "/api/auth/login", json={"email": "buyer@example.com", "password": "wrongpassword"}
    )
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"]


def test_me_requires_a_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_rejects_a_garbage_token(client):
    resp = client.get("/api/auth/me", headers=auth_header("not-a-real-token"))
    assert resp.status_code == 401


def test_me_returns_the_current_user(client, supplier):
    resp = client.get("/api/auth/me", headers=auth_header(supplier["access_token"]))
    assert resp.status_code == 200
    assert resp.json()["email"] == "supplier@example.com"
