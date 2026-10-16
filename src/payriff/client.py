from __future__ import annotations

from ._transport import Transport
from .models import Region
from .resources import CardsApi, InvoicesApi, OrdersApi, PaymentsApi, PayoutsApi, TransactionsApi


class Payriff:
    def __init__(
        self,
        app_key: str,
        *,
        merchant_id: str | None = None,
        timeout: float = 60.0,
        region: Region = Region.AZERBAIJAN,
        base_url: str | None = None,
    ):
        if not isinstance(app_key, str) or not app_key.strip():
            raise ValueError("app_key is required")
        if timeout <= 0:
            raise ValueError("timeout must be a positive number of seconds")
        region = Region(region)
        transport = Transport(base_url or region.base_url, app_key, merchant_id, timeout)
        self.orders = OrdersApi(transport, region.currency)
        self.payments = PaymentsApi(transport, region.currency)
        self.cards = CardsApi(transport)
        self.transactions = TransactionsApi(transport)
        self.payouts = PayoutsApi(transport)
        self.invoices = InvoicesApi(transport, region.currency)