import base64
import json
from decimal import Decimal

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from payriff import CardData, PaymentStatus

PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PUBLIC_KEY_B64 = base64.b64encode(
    PRIVATE_KEY.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
).decode()


def decrypt(secret_key: str, encrypted_message: str) -> dict:
    oaep = padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
    key_and_iv = PRIVATE_KEY.decrypt(base64.b64decode(secret_key), oaep)
    return json.loads(AESGCM(key_and_iv[:32]).decrypt(key_and_iv[32:44], base64.b64decode(encrypted_message), None))


def test_direct_pay_encrypts_card_and_sends_secret_key(server):
    server.ok("POST", "/api/v3/directPay", {
        "orderId": "ORD-1", "threeDS": True, "redirect": True, "redirectUrl": "https://acs.bank/3ds",
        "transactionResponse": {"status": "CREATED", "requestRrn": "req-1"},
    })

    response = server.client(card_encryption_key=PUBLIC_KEY_B64).payments.direct_pay(
        amount=Decimal("1.00"),
        description="Order #1",
        callback_url="https://shop.az/cb",
        card_save=True,
        request_rrn="rrn-1",
        card=CardData(pan="4169741330151979", card_holder="JOHN DOE", expiry_month="11", expiry_year="2027", cvv="123"),
    )

    sent = server.last
    assert sent.headers["authorization"] == "app-key"
    assert sent.headers["x-request-rrn"] == "rrn-1"
    assert b"4169741330151979" not in sent.body and b"JOHN DOE" not in sent.body
    body = sent.json()
    payment_data = body.pop("paymentData")
    assert body == {"amount": 1.0, "operation": "PURCHASE", "currency": "AZN", "description": "Order #1",
                    "callbackUrl": "https://shop.az/cb"}
    assert payment_data["paymentWay"] == "DIRECT"
    assert payment_data["cardSave"] is True
    assert decrypt(sent.headers["x-secret-key"], payment_data["encryptedMessage"]) == {
        "pan": "4169741330151979", "cardHolder": "JOHN DOE", "expiryYear": "2027", "expiryMonth": "11", "cvv": "123",
    }
    assert response.order_id == "ORD-1"
    assert response.three_ds is True
    assert response.redirect is True
    assert response.redirect_url == "https://acs.bank/3ds"
    assert response.transaction.status == "CREATED"


def test_direct_pay_requires_card_data(server):
    with pytest.raises(ValueError, match="^card must be a CardData$"):
        server.client().payments.direct_pay(amount=1, description="x", card={"pan": "4169741330151979"})
    assert server.requests == []


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