from __future__ import annotations

from ._transport import Transport
from .card import PRODUCTION_CARD_ENCRYPTION_KEY, CardEncryptor, parse_public_key
from .resources import CardsApi, InvoicesApi, OrdersApi, PaymentsApi, PayoutsApi, TransactionsApi

PRODUCTION_URL = "https://api.payriff.com"


class Payriff:
    def __init__(
        self,
        app_key: str,
        *,
        merchant_id: str | None = None,
        timeout: float = 60.0,
        card_encryption_key: str | None = None,
        base_url: str = PRODUCTION_URL,
    ):
        if not isinstance(app_key, str) or not app_key.strip():
            raise ValueError("app_key is required")
        if timeout <= 0:
            raise ValueError("timeout must be a positive number of seconds")
        transport = Transport(base_url, app_key, merchant_id, timeout)
        encryptor = CardEncryptor(parse_public_key(card_encryption_key or PRODUCTION_CARD_ENCRYPTION_KEY))
        self.orders = OrdersApi(transport)
        self.payments = PaymentsApi(transport, encryptor)
        self.cards = CardsApi(transport)
        self.transactions = TransactionsApi(transport)
        self.payouts = PayoutsApi(transport)
        self.invoices = InvoicesApi(transport)