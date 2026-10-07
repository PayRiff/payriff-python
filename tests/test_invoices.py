from datetime import date, datetime
from decimal import Decimal

import pytest

from payriff import Currency, InvoiceStatus, Language


def test_create_sends_merchant_envelope(server):
    server.ok("POST", "/api/v2/invoices", {
        "id": 9, "invoiceUuid": "inv-uuid-1", "invoiceCode": "INV-001", "invoiceStatus": "PENDING",
        "paymentUrl": "https://pay.payriff.com/i/inv?type=preview", "amount": 15.00, "totalAmount": 15.30,
        "currencyType": "AZN", "languageType": "AZ", "expireDate": "2026-10-08T23:59:00",
    })

    invoice = server.client().invoices.create(
        amount=Decimal("15.00"),
        language=Language.AZ,
        full_name="JOHN DOE",
        phone_number="+994501234567",
        description="Consultation",
        expire_date=datetime(2026, 10, 8, 23, 59),
        approve_url="https://shop.az/ok",
        send_sms=False,
        metadata={"bookingRef": "B-77"},
    )

    assert server.last.json() == {
        "merchant": "ES1000000",
        "body": {
            "amount": 15.0, "currencyType": "AZN", "languageType": "AZ", "fullName": "JOHN DOE",
            "phoneNumber": "+994501234567", "description": "Consultation", "expireDate": "2026-10-08T23:59:00",
            "approveURL": "https://shop.az/ok", "sendSms": False, "metadata": {"bookingRef": "B-77"},
        },
    }
    assert invoice.invoice_uuid == "inv-uuid-1"
    assert invoice.status is InvoiceStatus.PENDING
    assert invoice.payment_url.endswith("?type=preview")
    assert invoice.currency is Currency.AZN
    assert invoice.language is Language.AZ
    assert invoice.expire_date == datetime(2026, 10, 8, 23, 59)


def test_amount_required_unless_dynamic(server):
    server.ok("POST", "/api/v2/invoices", {"invoiceUuid": "inv-2"})

    with pytest.raises(ValueError, match="^amount is required$"):
        server.client().invoices.create()
    server.client().invoices.create(amount_dynamic=True)
    assert server.last.json()["body"] == {"amountDynamic": True, "currencyType": "AZN"}


def test_get_sends_invoice_uuid_in_envelope(server):
    server.ok("POST", "/api/v2/get-invoice", {
        "invoiceUuid": "inv-uuid-1", "invoiceStatus": "COMPLETE", "amount": 15.00, "paymentDay": "2026-10-02",
        "createdDate": "2026-10-01T09:00:00.123", "metadata": "{}",
    })

    details = server.client().invoices.get("inv-uuid-1")

    assert server.last.json() == {"merchant": "ES1000000", "body": {"uuid": "inv-uuid-1"}}
    assert details.status is InvoiceStatus.COMPLETE
    assert details.payment_day == date(2026, 10, 2)