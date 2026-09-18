"""RFQ creation, authorization, search and the edit-freeze rule."""

from datetime import date, timedelta

from tests.conftest import auth_header


def test_buyer_can_create_an_rfq(client, buyer, rfq_payload):
    resp = client.post(
        "/api/rfqs", json=rfq_payload, headers=auth_header(buyer["access_token"])
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == rfq_payload["title"]
    assert body["status"] == "open"
    assert body["quotation_count"] == 0


def test_supplier_cannot_create_an_rfq(client, supplier, rfq_payload):
    resp = client.post(
        "/api/rfqs", json=rfq_payload, headers=auth_header(supplier["access_token"])
    )
    assert resp.status_code == 403


def test_creating_an_rfq_requires_authentication(client, rfq_payload):
    assert client.post("/api/rfqs", json=rfq_payload).status_code == 401


def test_past_deadline_is_rejected(client, buyer, rfq_payload):
    rfq_payload["deadline"] = (date.today() - timedelta(days=1)).isoformat()
    resp = client.post(
        "/api/rfqs", json=rfq_payload, headers=auth_header(buyer["access_token"])
    )
    assert resp.status_code == 422


def test_zero_quantity_is_rejected(client, buyer, rfq_payload):
    rfq_payload["quantity"] = 0
    resp = client.post(
        "/api/rfqs", json=rfq_payload, headers=auth_header(buyer["access_token"])
    )
    assert resp.status_code == 422


def test_supplier_browse_shows_open_rfqs(client, supplier, rfq):
    resp = client.get("/api/rfqs", headers=auth_header(supplier["access_token"]))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == rfq["id"]


def test_browse_does_not_leak_buyer_email(client, supplier, rfq):
    resp = client.get("/api/rfqs", headers=auth_header(supplier["access_token"]))
    buyer_obj = resp.json()["items"][0]["buyer"]
    assert "email" not in buyer_obj
    assert buyer_obj["company_name"] == "Buyer Co"


def test_search_matches_title(client, supplier, rfq):
    hit = client.get("/api/rfqs?q=brackets", headers=auth_header(supplier["access_token"]))
    assert hit.json()["total"] == 1

    miss = client.get("/api/rfqs?q=zzzznothing", headers=auth_header(supplier["access_token"]))
    assert miss.json()["total"] == 0
    assert miss.json()["items"] == []


def test_search_is_case_insensitive(client, supplier, rfq):
    resp = client.get("/api/rfqs?q=BRACKETS", headers=auth_header(supplier["access_token"]))
    assert resp.json()["total"] == 1


def test_location_filter(client, supplier, rfq):
    hit = client.get("/api/rfqs?location=Pune", headers=auth_header(supplier["access_token"]))
    assert hit.json()["total"] == 1

    miss = client.get("/api/rfqs?location=Berlin", headers=auth_header(supplier["access_token"]))
    assert miss.json()["total"] == 0


def test_pagination_splits_results(client, buyer, supplier, rfq_payload):
    for i in range(3):
        client.post(
            "/api/rfqs",
            json={**rfq_payload, "title": f"Bulk order number {i}"},
            headers=auth_header(buyer["access_token"]),
        )
    resp = client.get(
        "/api/rfqs?page=1&page_size=2", headers=auth_header(supplier["access_token"])
    )
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2


def test_my_rfqs_only_returns_own(client, buyer, other_buyer, rfq):
    mine = client.get("/api/rfqs/mine", headers=auth_header(buyer["access_token"]))
    assert mine.json()["total"] == 1

    theirs = client.get("/api/rfqs/mine", headers=auth_header(other_buyer["access_token"]))
    assert theirs.json()["total"] == 0


def test_supplier_cannot_list_my_rfqs(client, supplier):
    resp = client.get("/api/rfqs/mine", headers=auth_header(supplier["access_token"]))
    assert resp.status_code == 403


def test_owner_can_edit_rfq_with_no_quotes(client, buyer, rfq):
    resp = client.patch(
        f"/api/rfqs/{rfq['id']}",
        json={"quantity": 750},
        headers=auth_header(buyer["access_token"]),
    )
    assert resp.status_code == 200
    assert resp.json()["quantity"] == 750


def test_other_buyer_cannot_edit_and_gets_404_not_403(client, other_buyer, rfq):
    """404, not 403 - a stranger should not learn that this id exists."""
    resp = client.patch(
        f"/api/rfqs/{rfq['id']}",
        json={"quantity": 1},
        headers=auth_header(other_buyer["access_token"]),
    )
    assert resp.status_code == 404


def test_commercial_terms_freeze_once_quoted(client, buyer, supplier, rfq):
    client.post(
        f"/api/rfqs/{rfq['id']}/quotations",
        json={"price": "1200.00", "delivery_days": 10},
        headers=auth_header(supplier["access_token"]),
    )
    blocked = client.patch(
        f"/api/rfqs/{rfq['id']}",
        json={"quantity": 999},
        headers=auth_header(buyer["access_token"]),
    )
    assert blocked.status_code == 409

    # Description stays editable - it clarifies rather than changes the deal.
    allowed = client.patch(
        f"/api/rfqs/{rfq['id']}",
        json={"description": "Clarification: brackets must be RAL 7016 grey."},
        headers=auth_header(buyer["access_token"]),
    )
    assert allowed.status_code == 200


def test_deadline_can_be_extended_but_not_shortened_after_quotes(client, buyer, supplier, rfq):
    client.post(
        f"/api/rfqs/{rfq['id']}/quotations",
        json={"price": "1200.00", "delivery_days": 10},
        headers=auth_header(supplier["access_token"]),
    )
    later = (date.today() + timedelta(days=30)).isoformat()
    assert (
        client.patch(
            f"/api/rfqs/{rfq['id']}",
            json={"deadline": later},
            headers=auth_header(buyer["access_token"]),
        ).status_code
        == 200
    )

    sooner = (date.today() + timedelta(days=2)).isoformat()
    assert (
        client.patch(
            f"/api/rfqs/{rfq['id']}",
            json={"deadline": sooner},
            headers=auth_header(buyer["access_token"]),
        ).status_code
        == 409
    )


def test_empty_patch_is_rejected(client, buyer, rfq):
    resp = client.patch(
        f"/api/rfqs/{rfq['id']}", json={}, headers=auth_header(buyer["access_token"])
    )
    assert resp.status_code == 400


def test_status_cannot_be_set_to_awarded_directly(client, buyer, rfq):
    resp = client.patch(
        f"/api/rfqs/{rfq['id']}",
        json={"status": "awarded"},
        headers=auth_header(buyer["access_token"]),
    )
    assert resp.status_code == 400


def test_delete_works_only_before_any_quote(client, buyer, supplier, rfq):
    client.post(
        f"/api/rfqs/{rfq['id']}/quotations",
        json={"price": "900.00", "delivery_days": 7},
        headers=auth_header(supplier["access_token"]),
    )
    blocked = client.delete(
        f"/api/rfqs/{rfq['id']}", headers=auth_header(buyer["access_token"])
    )
    assert blocked.status_code == 409


def test_missing_rfq_returns_404(client, buyer):
    resp = client.get("/api/rfqs/999999", headers=auth_header(buyer["access_token"]))
    assert resp.status_code == 404
