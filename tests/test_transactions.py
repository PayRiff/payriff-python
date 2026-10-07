from datetime import date
from decimal import Decimal

import pytest

from payriff import PaymentStatus


def test_list_sends_filter_and_parses_page(server):
    server.ok("GET", "/api/v3/transactions?status=APPROVED&from=01.09.2026&to=30.09.2026&page=1&offset=20", {
        "content": [{
            "id": 5, "orderId": "ORD-1", "amount": 10.00, "currencyType": "AZN", "paymentStatus": "APPROVED",
            "card_brand": "VISA", "payment_way": "DIRECT", "extra_payment": 0.50, "createdDate": "2026-09-15 10:00:00",
        }],
        "totalElements": 41, "totalPages": 3, "number": 1, "size": 20, "first": False, "last": False,
        "pageable": {"pageNumber": 1}, "sort": {"sorted": False},
    })

    page = server.client().transactions.list(
        status=PaymentStatus.APPROVED, from_date=date(2026, 9, 1), to_date="2026-09-30", page=1, size=20,
    )

    assert (page.total_elements, page.total_pages, page.last) == (41, 3, False)
    tx = page.content[0]
    assert tx.order_id == "ORD-1"
    assert tx.card_brand == "VISA"
    assert tx.payment_way == "DIRECT"
    assert tx.extra_payment == Decimal("0.50")
    assert tx.payment_status is PaymentStatus.APPROVED
    assert tx.created_date == "2026-09-15 10:00:00"


def test_default_filter_requests_first_page(server):
    server.ok("GET", "/api/v3/transactions", {"content": [], "totalElements": 0})

    server.client().transactions.list()

    assert server.last.url == "/api/v3/transactions?page=0&offset=10"


@pytest.mark.parametrize("size", [0, 21, -1, True])
def test_size_must_be_within_server_cap(server, size):
    with pytest.raises(ValueError, match="^size must be 1-20$"):
        server.client().transactions.list(size=size)


def test_invalid_date_string_is_rejected(server):
    with pytest.raises(ValueError, match="^from_date must be a date or a YYYY-MM-DD string$"):
        server.client().transactions.list(from_date="01.09.2026")