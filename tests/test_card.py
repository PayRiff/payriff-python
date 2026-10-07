import base64
import json
import textwrap

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from payriff import CardData, Payriff
from payriff.card import PRODUCTION_CARD_ENCRYPTION_KEY, CardEncryptor, parse_public_key

PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OAEP = padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)


def decrypt(secret_key: str, encrypted_message: str) -> bytes:
    key_and_iv = PRIVATE_KEY.decrypt(base64.b64decode(secret_key), OAEP)
    assert len(key_and_iv) == 44
    return AESGCM(key_and_iv[:32]).decrypt(key_and_iv[32:], base64.b64decode(encrypted_message), None)


CARD = dict(pan="4169 7413 3015 1979", card_holder=" JOHN DOE ", expiry_month="1", expiry_year="27", cvv="123")


def test_encrypted_card_decrypts_with_payriff_scheme():
    encrypted = CardEncryptor(PRIVATE_KEY.public_key()).encrypt(CardData(**CARD))

    assert decrypt(encrypted.secret_key, encrypted.encrypted_message) == (
        b'{"pan":"4169741330151979","cardHolder":"JOHN DOE","expiryYear":"2027","expiryMonth":"01","cvv":"123"}'
    )


def test_every_call_uses_fresh_key_material():
    encryptor = CardEncryptor(PRIVATE_KEY.public_key())

    a = encryptor.encrypt(CardData(**CARD))
    b = encryptor.encrypt(CardData(**CARD))

    assert a.encrypted_message != b.encrypted_message
    assert a.secret_key != b.secret_key


def test_parses_base64_and_pem_keys():
    pem = "-----BEGIN PUBLIC KEY-----\n" + "\n".join(textwrap.wrap(PRODUCTION_CARD_ENCRYPTION_KEY, 64)) + "\n-----END PUBLIC KEY-----\n"

    assert parse_public_key(PRODUCTION_CARD_ENCRYPTION_KEY).key_size == 2048
    assert parse_public_key(pem).key_size == 2048


def test_rejects_invalid_encryption_key():
    with pytest.raises(ValueError, match="^Invalid RSA public key$"):
        Payriff("k", card_encryption_key="not-a-key")


def test_rejects_non_rsa_key():
    from cryptography.hazmat.primitives.asymmetric import ec

    ec_key = ec.generate_private_key(ec.SECP256R1()).public_key()
    der = ec_key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)

    with pytest.raises(ValueError, match="^Invalid RSA public key$"):
        parse_public_key(base64.b64encode(der).decode())


def test_normalizes_input():
    card = CardData(pan="4169-7413-3015-1979", card_holder="JOHN DOE", expiry_month=11, expiry_year=2027, cvv="1234")

    assert json.loads(card.to_json()) == {
        "pan": "4169741330151979", "cardHolder": "JOHN DOE", "expiryYear": "2027", "expiryMonth": "11", "cvv": "1234",
    }


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"pan": "4169"}, "pan must contain 12-19 digits"),
        ({"pan": "4169741330151979000000"}, "pan must contain 12-19 digits"),
        ({"pan": "4169a41330151979"}, "pan must contain digits only"),
        ({"expiry_month": "13"}, "expiry_month must be 1-12"),
        ({"expiry_month": "0"}, "expiry_month must be 1-12"),
        ({"expiry_year": "202"}, "expiry_year must have 2 or 4 digits"),
        ({"cvv": "12"}, "cvv must contain 3-4 digits"),
        ({"cvv": None}, "cvv is required"),
        ({"card_holder": None}, "card_holder is required"),
    ],
)
def test_rejects_invalid_input(override, message):
    with pytest.raises(ValueError, match=f"^{message}$"):
        CardData(**{**CARD, **override})


def test_repr_masks_sensitive_data():
    text = repr(CardData(**CARD))

    assert text == "CardData(pan=416974******1979, expiry=01/2027)"
    assert "123" not in text
    assert str(CardData(**CARD)) == text