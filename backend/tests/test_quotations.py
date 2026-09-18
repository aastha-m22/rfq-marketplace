"""Quotation submission, visibility isolation and the award flow."""

from datetime import date, timedelta

from tests.conftest import auth_header


def quote(client, token, rfq_id, price="1000.00", days=10, notes=None):
    return client.post(
        f"/api/rfqs/{rfq_id}/quotations",
        json={"price": price, "delivery_days": days, "notes": notes},
        headers=auth_header(token),
    )


def test_supplier_can_submit_a_quotation(client, supplier, rfq):
    resp = quote(client, supplier["access_token"], rfq["id"], notes="Ex-works Pune.")
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending"
    assert body["supplier"]["company_name"] == "Supplier Co"


def test_buyer_cannot_submit_a_quotation(client, buyer, rfq):
    assert quote(client, buyer["access_token"], rfq["id"]).status_code == 403


def test_quotation_requires_authentication(client, rfq):
    resp = client.post(
        f"/api/rfqs/{rfq['id']}/quotations", json={"price": "10.00", "delivery_days": 1}
    )
    assert resp.status_code == 401


def test_negative_price_is_rejected(client, supplier, rfq):
    assert quote(client, supplier["access_token"], rfq["id"], price="-50.00").status_code == 422


def test_zero_delivery_days_is_rejected(client, supplier, rfq):
    assert quote(client, supplier["access_token"], rfq["id"], days=0).status_code == 422


def test_resubmitting_updates_the_existing_quotation(client, supplier, buyer, rfq):
    first = quote(client, supplier["access_token"], rfq["id"], price="1000.00")
    second = quote(client, supplier["access_token"], rfq["id"], price="900.00")

    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]  # same row, revised

    listed = client.get(
        f"/api/rfqs/{rfq['id']}/quotations", headers=auth_header(buyer["access_token"])
    )
    assert len(listed.json()) == 1
    assert listed.json()[0]["price"] == "900.00"


def test_cannot_quote_after_the_deadline(client, buyer, supplier, db_session, rfq):
    from app.models import RFQ

    stale = db_session.get(RFQ, rfq["id"])
    stale.deadline = date.today() - timedelta(days=1)
    db_session.commit()

    resp = quote(client, supplier["access_token"], rfq["id"])
    assert resp.status_code == 409
    assert "deadline" in resp.json()["detail"].lower()


def test_cannot_quote_on_a_closed_rfq(client, buyer, supplier, rfq):
    client.patch(
        f"/api/rfqs/{rfq['id']}",
        json={"status": "closed"},
        headers=auth_header(buyer["access_token"]),
    )
    resp = quote(client, supplier["access_token"], rfq["id"])
    assert resp.status_code == 409


def test_buyer_sees_all_quotations_on_own_rfq_sorted_by_price(
    client, buyer, supplier, other_supplier, rfq
):
    quote(client, supplier["access_token"], rfq["id"], price="1500.00")
    quote(client, other_supplier["access_token"], rfq["id"], price="1100.00")

    resp = client.get(
        f"/api/rfqs/{rfq['id']}/quotations", headers=auth_header(buyer["access_token"])
    )
    prices = [q["price"] for q in resp.json()]
    assert prices == ["1100.00", "1500.00"]


def test_other_buyer_cannot_see_quotations(client, other_buyer, supplier, rfq):
    quote(client, supplier["access_token"], rfq["id"])
    resp = client.get(
        f"/api/rfqs/{rfq['id']}/quotations", headers=auth_header(other_buyer["access_token"])
    )
    assert resp.status_code == 404


def test_supplier_cannot_see_the_quotation_list(client, supplier, rfq):
    """A supplier must never see competitors' prices."""
    quote(client, supplier["access_token"], rfq["id"])
    resp = client.get(
        f"/api/rfqs/{rfq['id']}/quotations", headers=auth_header(supplier["access_token"])
    )
    assert resp.status_code == 403


def test_my_quotations_returns_only_own(client, supplier, other_supplier, rfq):
    quote(client, supplier["access_token"], rfq["id"], price="1500.00")
    quote(client, other_supplier["access_token"], rfq["id"], price="1100.00")

    mine = client.get("/api/quotations/mine", headers=auth_header(supplier["access_token"]))
    body = mine.json()
    assert len(body) == 1
    assert body[0]["price"] == "1500.00"
    assert body[0]["rfq"]["title"] == "500 steel brackets"


def test_accepting_rejects_siblings_and_awards_the_rfq(
    client, buyer, supplier, other_supplier, rfq
):
    winner = quote(client, supplier["access_token"], rfq["id"], price="1100.00").json()
    loser = quote(client, other_supplier["access_token"], rfq["id"], price="1500.00").json()

    resp = client.post(
        f"/api/quotations/{winner['id']}/accept", headers=auth_header(buyer["access_token"])
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"

    listed = {
        q["id"]: q["status"]
        for q in client.get(
            f"/api/rfqs/{rfq['id']}/quotations", headers=auth_header(buyer["access_token"])
        ).json()
    }
    assert listed[winner["id"]] == "accepted"
    assert listed[loser["id"]] == "rejected"

    detail = client.get(f"/api/rfqs/{rfq['id']}", headers=auth_header(buyer["access_token"]))
    assert detail.json()["status"] == "awarded"


def test_cannot_award_the_same_rfq_twice(client, buyer, supplier, rfq):
    q = quote(client, supplier["access_token"], rfq["id"]).json()
    first = client.post(
        f"/api/quotations/{q['id']}/accept", headers=auth_header(buyer["access_token"])
    )
    second = client.post(
        f"/api/quotations/{q['id']}/accept", headers=auth_header(buyer["access_token"])
    )
    assert first.status_code == 200
    assert second.status_code == 409


def test_other_buyer_cannot_accept(client, other_buyer, supplier, rfq):
    q = quote(client, supplier["access_token"], rfq["id"]).json()
    resp = client.post(
        f"/api/quotations/{q['id']}/accept", headers=auth_header(other_buyer["access_token"])
    )
    assert resp.status_code == 404


def test_supplier_cannot_accept_their_own_quotation(client, supplier, rfq):
    q = quote(client, supplier["access_token"], rfq["id"]).json()
    resp = client.post(
        f"/api/quotations/{q['id']}/accept", headers=auth_header(supplier["access_token"])
    )
    assert resp.status_code == 403


def test_rejected_quotation_cannot_be_revised(client, buyer, supplier, other_supplier, rfq):
    winner = quote(client, supplier["access_token"], rfq["id"], price="1100.00").json()
    quote(client, other_supplier["access_token"], rfq["id"], price="1500.00")
    client.post(
        f"/api/quotations/{winner['id']}/accept", headers=auth_header(buyer["access_token"])
    )

    # The RFQ is awarded, so the loser cannot undercut after the fact.
    resp = quote(client, other_supplier["access_token"], rfq["id"], price="900.00")
    assert resp.status_code == 409
