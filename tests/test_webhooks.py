import json
from datetime import datetime

import pytest

from payriff import PaymentStatus, parse_order_callback

CALLBACK = (
    '{"payload":{"orderId":"ORD-1","invoiceUuid":"inv-1","amount":10.5,'
    '"currencyType":"AZN","paymentStatus":"APPROVED","operationType":"PURCHASE","auto":false,'
    '"createdDate":"2026-10-01T14:05:09.123","customFields":{"x":"y"},'
    '"transactions":[{"uuid":"6f1c2a4e-0b7d-4c3e-9a51-2d8e7f6b1c90","status":"APPROVED",'
    '"createdDate":"2026-10-01T14:05:10.000"}]},'
    '"code":"00000","message":"Operation performed successfully","route":"/dashboard","responseId":"http-nio-1"}'
)


@pytest.mark.parametrize("body", [CALLBACK, CALLBACK.encode(), json.loads(CALLBACK)], ids=["str", "bytes", "dict"])
def test_parses_gson_serialized_callback(body):
    order = parse_order_callback(body)

    assert order.order_id == "ORD-1"
    assert order.payment_status is PaymentStatus.APPROVED
    assert order.invoice_uuid == "inv-1"
    assert order.created_date == datetime(2026, 10, 1, 14, 5, 9, 123000)
    assert len(order.transactions) == 1


@pytest.mark.parametrize("body", ["", "not json", "{}", '{"payload":null}', '{"payload":{"amount":1}}', "[]", '{"payload":[]}'])
def test_rejects_non_callback_bodies(body):
    with pytest.raises(ValueError, match="^Not a Payriff order callback$"):
        parse_order_callback(body)