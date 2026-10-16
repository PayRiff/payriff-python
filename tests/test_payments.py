from decimal import Decimal

from payriff import PaymentStatus


def test_auto_pay_sends_explicit_currency_and_one_click_flag(server):
    server.ok("POST", "/api/v3/autoPay", {
        "orderId": "ORD-2", "amount": 3.00, "paymentStatus": "APPROVED", "auto": True,
        "createdDate": "2026-10-01T10:00:00.000000", "transactionResponseDto": {"threeDS": False},
    })

    response = server.client().payments.auto_pay(
        card_uuid="card-uuid-1",
        amount=Decimal("3.00"),
        description="Subscription",
        one_click_payment=True,
        request_rrn="rrn-2",
    )

    assert server.last.headers["x-request-rrn"] == "rrn-2"
    assert server.last.json() == {
        "cardUuid": "card-uuid-1", "amount": 3.0, "operation": "PURCHASE", "currency": "AZN",
        "description": "Subscription", "isOneCLickPayment": True,
    }
    assert response.order_id == "ORD-2"
    assert response.payment_status is PaymentStatus.APPROVED
    assert response.auto is True
    assert response.transaction_response.three_ds is False