from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

PRODUCTION_CARD_ENCRYPTION_KEY = (
    "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAxRq5a+44T6Dac60XmVRQ/7cpPyFsBnamXbJlRVJk8CnES5Re5tVMohyD0hZr"
    "3zcQj+bxodYB4zZpQTPlrXvFBC3zz+rXnGlevxBQ6W2d3QC9q8vWH8p3ZOwTO3qVvDSHH9o+hMMRNbJ7kueq/KZlX/F+bjZ23CZw7iXE"
    "GQT3HYVYnnHsvpaguYDteWBag2sPPLLsVjeB3zhTfQ7OsWp5XTkDuRwLugHPvs6RHLcwGCnodukWyvwUaEUQR/kMGC+RbMsAIVkcLMP5"
    "csfR3Xo7Gi98+i44iLN00f7gE8QvEmvv8xDspyTAjDEL1a5gK7TijJ3yLG/Bwa1rr1uskYy7lwIDAQAB"
)

_AES_KEY_BYTES = 32
_IV_BYTES = 12
_SEPARATORS = re.compile(r"[\s-]")


def _digits(value: object, field: str) -> str:
    if value is None:
        raise ValueError(f"{field} is required")
    v = _SEPARATORS.sub("", str(value))
    if not v.isdigit() or not v.isascii():
        raise ValueError(f"{field} must contain digits only")
    return v


@dataclass(frozen=True, repr=False)
class CardData:
    pan: str
    card_holder: str
    expiry_month: str | int
    expiry_year: str | int
    cvv: str

    def __post_init__(self) -> None:
        pan = _digits(self.pan, "pan")
        if not 12 <= len(pan) <= 19:
            raise ValueError("pan must contain 12-19 digits")
        if self.card_holder is None:
            raise ValueError("card_holder is required")
        month = int(_digits(self.expiry_month, "expiry_month"))
        if not 1 <= month <= 12:
            raise ValueError("expiry_month must be 1-12")
        year = _digits(self.expiry_year, "expiry_year")
        if len(year) == 2:
            year = "20" + year
        elif len(year) != 4:
            raise ValueError("expiry_year must have 2 or 4 digits")
        cvv = _digits(self.cvv, "cvv")
        if not 3 <= len(cvv) <= 4:
            raise ValueError("cvv must contain 3-4 digits")
        object.__setattr__(self, "pan", pan)
        object.__setattr__(self, "card_holder", str(self.card_holder).strip())
        object.__setattr__(self, "expiry_month", f"{month:02d}")
        object.__setattr__(self, "expiry_year", year)
        object.__setattr__(self, "cvv", cvv)

    def __repr__(self) -> str:
        return f"CardData(pan={self.pan[:6]}******{self.pan[-4:]}, expiry={self.expiry_month}/{self.expiry_year})"

    __str__ = __repr__

    def to_json(self) -> bytes:
        return json.dumps(
            {
                "pan": self.pan,
                "cardHolder": self.card_holder,
                "expiryYear": self.expiry_year,
                "expiryMonth": self.expiry_month,
                "cvv": self.cvv,
            },
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")


def parse_public_key(base64_or_pem: str) -> rsa.RSAPublicKey:
    body = re.sub(
        r"\s",
        "",
        base64_or_pem.replace("-----BEGIN PUBLIC KEY-----", "").replace("-----END PUBLIC KEY-----", ""),
    )
    try:
        key = serialization.load_der_public_key(base64.b64decode(body, validate=True))
    except Exception as e:
        raise ValueError("Invalid RSA public key") from e
    if not isinstance(key, rsa.RSAPublicKey):
        raise ValueError("Invalid RSA public key")
    return key


@dataclass(frozen=True)
class EncryptedCard:
    encrypted_message: str
    secret_key: str


class CardEncryptor:
    def __init__(self, public_key: rsa.RSAPublicKey):
        self._public_key = public_key

    def encrypt(self, card: CardData) -> EncryptedCard:
        aes_key = bytearray(os.urandom(_AES_KEY_BYTES))
        iv = bytearray(os.urandom(_IV_BYTES))
        try:
            ciphertext = AESGCM(bytes(aes_key)).encrypt(bytes(iv), card.to_json(), None)
            secret = self._public_key.encrypt(
                bytes(aes_key + iv),
                padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
            )
            return EncryptedCard(
                encrypted_message=base64.b64encode(ciphertext).decode("ascii"),
                secret_key=base64.b64encode(secret).decode("ascii"),
            )
        finally:
            aes_key[:] = bytes(len(aes_key))
            iv[:] = bytes(len(iv))