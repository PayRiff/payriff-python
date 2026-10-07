from decimal import Decimal

import pytest

from payriff import CardSaveStatus, Language


def test_save_sends_body_and_idempotency_key(server):
    server.ok("POST", "/api/v3/cards/save", {
        "cardSaveId": "0b6e1f6a-3c1d-4f5e-8a2b-9c7d6e5f4a3b", "orderId": "ORD-CS",
        "paymentUrl": "https://pay.payriff.com/ORD-CS", "amount": 0.10, "currency": "AZN", "status": "CREATED",
    })

    response = server.client().cards.save(
        customer_ref="cust-1", callback_url="https://shop.az/cards/cb", language=Language.AZ, idempotency_key="idem-1",
    )

    assert server.last.headers["x-idempotency-key"] == "idem-1"
    assert server.last.json() == {"customerRef": "cust-1", "callbackUrl": "https://shop.az/cards/cb", "language": "AZ"}
    assert response.card_save_id == "0b6e1f6a-3c1d-4f5e-8a2b-9c7d6e5f4a3b"
    assert response.status is CardSaveStatus.CREATED
    assert response.amount == Decimal("0.10")


def test_save_requires_callback_url(server):
    with pytest.raises(ValueError, match="^callback_url is required$"):
        server.client().cards.save(customer_ref="c", callback_url=None)


def test_get_save_parses_verified_card(server):
    server.ok("GET", "/api/v3/cards/save/cs-1", {
        "cardSaveId": "cs-1", "status": "VERIFIED", "cardUuid": "card-1", "verifiedDate": "2026-10-01T10:01:30.5",
    })

    details = server.client().cards.get_save("cs-1")

    assert details.status is CardSaveStatus.VERIFIED
    assert details.card_uuid == "card-1"
    assert details.verified_date is not None


def test_list_returns_cards_for_customer(server):
    server.ok("GET", "/api/v3/cards/save?customerRef=cust%201", [
        {"cardUuid": "card-1", "maskedPan": "416974******1979", "cardBrand": "VISA"},
        {"cardUuid": "card-2", "maskedPan": "540000******0001", "cardBrand": "MASTERCARD"},
    ])

    cards = server.client().cards.list("cust 1")

    assert [c.card_uuid for c in cards] == ["card-1", "card-2"]


def test_list_returns_empty_for_null_payload(server):
    server.ok("GET", "/api/v3/cards/save", None)

    assert server.client().cards.list("cust-1") == []


def test_delete_calls_card_endpoint(server):
    server.ok("DELETE", "/api/v3/cards/card-1", True)

    server.client().cards.delete("card-1")

    assert (server.last.method, server.last.url) == ("DELETE", "/api/v3/cards/card-1")