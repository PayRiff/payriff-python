import pytest

from payriff import (
    ApiError,
    AuthenticationError,
    InsufficientBalanceError,
    Payriff,
    PayoutLimitError,
    PayriffConnectionError,
    PaymentStatus,
    RequestRejectedError,
    ValidationError,
    __version__,
)


def test_unwraps_payload_on_success(server):
    server.ok("GET", "/api/v3/orders/ORD-1", {"orderId": "ORD-1", "paymentStatus": "APPROVED"})

    order = server.client().orders.get("ORD-1")

    assert order.order_id == "ORD-1"
    assert order.payment_status is PaymentStatus.APPROVED


def test_sends_auth_and_client_headers(server):
    server.ok("GET", "/api/v3/orders/ORD-1", {"orderId": "ORD-1"})

    server.client().orders.get("ORD-1")

    headers = server.last.headers
    assert headers["authorization"] == "app-key"
    assert headers["user-agent"] == f"payriff-python/{__version__}"
    assert headers["accept"] == "application/json"
    assert "content-type" not in headers


def test_encodes_path_segments_and_query(server):
    server.ok("PATCH", "/api/v3/expire-status", None)

    server.client().orders.expire("ORD 1/2")

    assert server.last.url == "/api/v3/expire-status?orderId=ORD%201%2F2"


def test_rejects_blank_path_segment_before_sending(server):
    with pytest.raises(ValueError, match="^order_id must not be blank$"):
        server.client().orders.get(" ")
    assert server.requests == []


def test_merchant_envelope_requires_merchant_id(server):
    with pytest.raises(ValueError, match="^merchant_id must be configured on Payriff for this operation$"):
        server.client(merchant_id=None).invoices.get("inv-1")
    assert server.requests == []


@pytest.mark.parametrize(
    ("status", "code", "error_type"),
    [
        (200, "15000", ApiError),
        (401, "14010", AuthenticationError),
        (401, "14013", AuthenticationError),
        (200, "14014", AuthenticationError),
        (401, "14015", AuthenticationError),
        (400, "15400", ValidationError),
        (400, "99999", ValidationError),
        (403, "99999", AuthenticationError),
        (402, "01000", RequestRejectedError),
        (402, "01200", InsufficientBalanceError),
        (402, "01300", PayoutLimitError),
        (402, "01400", PayoutLimitError),
        (402, "01500", PayoutLimitError),
        (500, "15000", ApiError),
        (503, "15000", ApiError),
    ],
)
def test_maps_failures_to_typed_errors(server, status, code, error_type):
    server.stub("GET", "/api/v3/orders/ORD-1", status=status,
                body={"code": code, "message": "Failure reason", "responseId": "resp-1"})

    with pytest.raises(ApiError) as info:
        server.client().orders.get("ORD-1")

    e = info.value
    assert type(e) is error_type
    assert str(e) == "Failure reason"
    assert (e.http_status, e.code, e.response_id) == (status, code, "resp-1")


def test_missing_message_falls_back_to_http_status(server):
    server.stub("GET", "/api/v3/orders/ORD-1", status=500, body={"code": "15000"})

    with pytest.raises(ApiError, match=r"^Payriff request failed \(HTTP 500\)$"):
        server.client().orders.get("ORD-1")


def test_non_json_error_body_keeps_status_and_truncates(server):
    server.stub("GET", "/api/v3/orders/ORD-1", status=502, headers={"Content-Type": "text/html"}, body="x" * 600)

    with pytest.raises(ApiError) as info:
        server.client().orders.get("ORD-1")

    assert info.value.http_status == 502
    assert info.value.code is None
    assert str(info.value) == "x" * 500 + "..."


def test_success_status_without_envelope_is_rejected(server):
    server.stub("GET", "/api/v3/orders/ORD-1", body={"orderId": "ORD-1"})

    with pytest.raises(ApiError, match="^Unexpected response from Payriff$"):
        server.client().orders.get("ORD-1")


def test_redirects_are_not_followed(server):
    server.stub("GET", "/api/v3/orders/ORD-1", status=302, headers={"Location": "/api/v3/orders/OTHER"},
                body={"code": "15000", "message": "Redirect"})

    with pytest.raises(ApiError, match="^Redirect$"):
        server.client().orders.get("ORD-1")
    assert len(server.requests) == 1


def test_download_returns_bytes(server):
    server.stub("GET", "/api/v3/acquiring/receipt/ORD-1", headers={"Content-Type": "application/pdf"}, body=b"%PDF-1.7")

    assert server.client().orders.download_receipt("ORD-1") == b"%PDF-1.7"
    assert server.last.headers["accept"] == "application/pdf, application/json"


def test_download_maps_envelope_error(server):
    server.stub("GET", "/api/v3/acquiring/receipt/ORD-1", status=400, body={"code": "15400", "message": "Receipt not found"})

    with pytest.raises(ValidationError):
        server.client().orders.download_receipt("ORD-1")


def test_connection_failure_raises_connection_error():
    client = Payriff("app-key", base_url="http://127.0.0.1:1")

    with pytest.raises(PayriffConnectionError) as info:
        client.orders.get("ORD-1")
    assert info.value.http_status == 0


def test_timeout_raises_connection_error():
    client = Payriff("app-key", base_url="http://10.255.255.1", timeout=0.05)

    with pytest.raises(PayriffConnectionError):
        client.orders.get("ORD-1")