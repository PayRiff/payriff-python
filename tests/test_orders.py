from datetime import datetime
from decimal import Decimal

import pytest

from payriff import Currency, Installment, InstallmentPeriod, InstallmentProductType, Language, Operation, PaymentStatus

ORDER_INFO = {
    "orderId": "ORD-1",
    "amount": 10.50,
    "currencyType": "AZN",
    "merchantName": "Shop",
    "commission": 0.20,
    "commissionRate": 2.00,
    "operationType": "PURCHASE",
    "paymentStatus": "APPROVED",
    "auto": False,
    "createdDate": "2026-10-01T14:05:09.123456",
    "description": "Order #1",
    "metadata": '{"k":"v"}',
    "transactions": [{
        "uuid": "6f1c2a4e-0b7d-4c3e-9a51-2d8e7f6b1c90",
        "status": "APPROVED",
        "channel": "KAPITAL_BANK",
        "cardDetails": {"maskedPan": "416974******1979", "brand": "VISA", "bcryptedCardPan": "$2a$x"},
        "installment": {"type": "BIRKART", "period": "PERIOD_3"},
    }],
}


def test_create_sends_body_and_rrn_header(server):
    server.ok("POST", "/api/v3/orders", {
        "orderId": "ORD-1", "paymentUrl": "https://pay.payriff.com/ORD-1", "transactionId": 77,
        "comissionRate": 2.5, "amount": 10.00, "fee": 0.25, "totalAmount": 10.25,
    })

    response = server.client().orders.create(
        amount=Decimal("10.00"),
        language=Language.AZ,
        description="Order #1",
        callback_url="https://shop.az/cb",
        installment=Installment(InstallmentProductType.BIRKART, InstallmentPeriod.PERIOD_3),
        metadata={"cartId": "c-9"},
        request_rrn="rrn-1",
    )

    assert server.last.headers["authorization"] == "app-key"
    assert server.last.headers["x-request-rrn"] == "rrn-1"
    assert server.last.headers["content-type"] == "application/json"
    assert server.last.json() == {
        "amount": 10.0, "currency": "AZN", "language": "AZ", "operation": "PURCHASE", "description": "Order #1",
        "callbackUrl": "https://shop.az/cb", "installment": {"type": "BIRKART", "period": "PERIOD_3"},
        "metadata": {"cartId": "c-9"},
    }
    assert response.order_id == "ORD-1"
    assert response.payment_url == "https://pay.payriff.com/ORD-1"
    assert response.transaction_id == 77
    assert response.commission_rate == Decimal("2.5")
    assert response.total_amount == Decimal("10.25")


def test_create_omits_rrn_header_and_empty_maps(server):
    server.ok("POST", "/api/v3/orders", {"orderId": "ORD-1"})

    server.client().orders.create(amount=1, metadata={})

    assert "x-request-rrn" not in server.last.headers
    assert server.last.json() == {"amount": 1, "currency": "AZN", "operation": "PURCHASE"}


def test_amounts_keep_decimal_precision(server):
    server.ok("POST", "/api/v3/orders", {"orderId": "ORD-1"})

    server.client().orders.create(amount="10.10")

    assert b'"amount":10.1,' in server.last.body


def test_create_rejects_missing_amount(server):
    with pytest.raises(ValueError, match="^amount is required$"):
        server.client().orders.create(amount=None)
    assert server.requests == []


@pytest.mark.parametrize(
    ("method", "ident", "path"),
    [
        ("get", "ORD-1", "/api/v3/orders/ORD-1"),
        ("get_status", "ORD-1", "/api/v3/orders/ORD-1/status"),
        ("get_by_request_rrn", "rrn 1/2", "/api/v3/orders/rrn%201%2F2/rrn"),
    ],
)
def test_lookups_parse_order_info(server, method, ident, path):
    server.ok("GET", path, ORDER_INFO)

    order = getattr(server.client().orders, method)(ident)

    assert server.last.url == path
    assert order.order_id == "ORD-1"
    assert order.amount == Decimal("10.50")
    assert order.currency is Currency.AZN
    assert order.payment_status is PaymentStatus.APPROVED
    assert order.operation_type is Operation.PURCHASE
    assert order.created_date == datetime(2026, 10, 1, 14, 5, 9, 123456)
    assert order.metadata == '{"k":"v"}'
    tx = order.transactions[0]
    assert tx.uuid == "6f1c2a4e-0b7d-4c3e-9a51-2d8e7f6b1c90"
    assert tx.channel == "KAPITAL_BANK"
    assert tx.card_details.masked_pan == "416974******1979"
    assert tx.card_details.brand == "VISA"
    assert tx.installment.period is InstallmentPeriod.PERIOD_3


def test_unknown_enum_values_do_not_break_parsing(server):
    server.ok("GET", "/api/v3/orders/ORD-1", {
        "orderId": "ORD-1", "paymentStatus": "SOMETHING_NEW", "currencyType": "GBP", "transactions": None,
    })

    order = server.client().orders.get("ORD-1")

    assert order.payment_status is PaymentStatus.UNKNOWN
    assert order.currency is None
    assert order.transactions == []


def test_expire_sends_order_id_as_query(server):
    server.ok("PATCH", "/api/v3/expire-status", None)

    assert server.client().orders.expire("ORD-1") is None
    assert server.last.method == "PATCH"
    assert server.last.url == "/api/v3/expire-status?orderId=ORD-1"


def test_refund_sends_body(server):
    server.ok("POST", "/api/v3/refund", None)

    server.client().orders.refund("ORD-1", amount=Decimal("5.00"), refund_reason="damaged")

    assert server.last.json() == {"orderId": "ORD-1", "amount": 5.0, "refundReason": "damaged"}


def test_complete_sends_body(server):
    server.ok("POST", "/api/v3/complete", None)

    server.client().orders.complete("ORD-1", amount=Decimal("7.00"))

    assert server.last.json() == {"orderId": "ORD-1", "amount": 7.0}