from decimal import Decimal

import pytest

from payriff import InsufficientBalanceError, TransferState

PAYOUT = dict(
    transfer_amount=Decimal("25.00"),
    description="Refund to customer",
    full_name="JOHN DOE",
    fin_code="1AB2C3D",
    card_pan="4169741330151979",
    request_rrn="po-1",
)


def test_create_wraps_body_in_merchant_envelope(server):
    server.ok("POST", "/api/v3/payout", {
        "_final": "true", "state": "SUCCESS", "currentDepositBalance": 975.00, "walletHistoryId": 321, "bankName": "KAPITAL",
    })

    result = server.client().payouts.create(**PAYOUT, idempotency_key="idem-po-1")

    assert server.last.headers["x-idempotency-key"] == "idem-po-1"
    assert server.last.json() == {
        "merchant": "ES1000000",
        "body": {"transferAmount": 25.0, "description": "Refund to customer", "fullName": "JOHN DOE",
                 "finCode": "1AB2C3D", "cardPan": "4169741330151979", "requestRrn": "po-1"},
    }
    assert result.final_state == "true"
    assert result.state == "SUCCESS"
    assert result.wallet_history_id == 321
    assert result.current_deposit_balance == Decimal("975.00")


def test_create_maps_insufficient_balance(server):
    server.stub("POST", "/api/v3/payout", status=402, body={"code": "01200", "message": "Insufficient wallet balance"})

    with pytest.raises(InsufficientBalanceError, match="^Insufficient wallet balance$"):
        server.client().payouts.create(**PAYOUT)


def test_amount_below_minimum_is_rejected(server):
    with pytest.raises(ValueError, match="^transfer_amount must be at least 1$"):
        server.client().payouts.create(**{**PAYOUT, "transfer_amount": Decimal("0.99")})
    assert server.requests == []


def test_get_by_request_rrn_parses_status(server):
    server.ok("GET", "/api/v3/payout/info/po-1", {
        "state": "IN_PROGRESS", "transferAmount": 25.00, "bankName": "KAPITAL",
        "createdDate": "2026-10-01T10:00:00.000+00:00", "formattedDate": "01.10.2026 10:00:00",
    })

    status = server.client().payouts.get_by_request_rrn("po-1")

    assert status.state is TransferState.IN_PROGRESS
    assert status.formatted_date == "01.10.2026 10:00:00"


def test_check_cardholder_normalizes_pan(server):
    server.ok("POST", "/api/v3/payout/check-cardholder", "J*** D**")

    assert server.client().payouts.check_cardholder("4169 7413 3015 1979") == "J*** D**"
    assert server.last.json() == {"cardPan": "4169741330151979"}


def test_check_cardholder_rejects_short_pan(server):
    with pytest.raises(ValueError, match="^card_pan must be a 16-digit number$"):
        server.client().payouts.check_cardholder("4169")


def test_list_parses_payout_page(server):
    server.ok("GET", "/api/v3/payouts?status=SUCCESS&page=0&offset=10", {
        "content": [{"id": 1, "requestRrn": "po-1", "transferAmount": 25.00, "fee": 0.25, "state": "SUCCESS",
                     "createdDate": "2026-10-01T10:00:00"}],
        "totalElements": 1, "totalPages": 1, "number": 0, "size": 10, "first": True, "last": True,
    })

    page = server.client().payouts.list(status=TransferState.SUCCESS)

    assert [p.request_rrn for p in page.content] == ["po-1"]
    assert page.content[0].state is TransferState.SUCCESS


def test_download_receipt_returns_pdf(server):
    server.stub("GET", "/api/v3/payout/receipt/po-1", headers={"Content-Type": "application/pdf"}, body=b"%PDF-")

    assert server.client().payouts.download_receipt("po-1") == b"%PDF-"