# Payriff Python SDK

Python client for the Payriff merchant API: orders, direct (host-to-host) card payments, saved cards,
transactions, payouts and invoices.

- Python 3.10 or newer
- One runtime dependency (`cryptography`, for card encryption)
- Fully typed
- Talks to `https://api.payriff.com`

## Installation

```bash
pip install payriff-python
```

The import name is `payriff`.

## Quick start

```python
import os
from decimal import Decimal

from payriff import Payriff

payriff = Payriff(os.environ["PAYRIFF_APP_KEY"])

order = payriff.orders.create(
    amount=Decimal("10.00"),
    description="Order #1001",
    callback_url="https://shop.example/payriff/callback",
    request_rrn="order-1001",
)

# Send the customer to the hosted payment page
payment_url = order.payment_url
```

Create one `Payriff` instance and reuse it. It is safe to share between threads.

## Configuration

| Argument | Required | Default | Notes |
|---|---|---|---|
| `app_key` | yes | — | Application key from the Payriff dashboard. |
| `merchant_id` | for payouts and invoices | — | Merchant ID (e.g. `ES1000000`). |
| `timeout` | no | `60.0` | Socket timeout in seconds. Bank operations can take tens of seconds. |
| `card_encryption_key` | no | built-in Payriff key | Only if Payriff rotates the card-encryption key. Base64 or PEM. |

Keep the app key in an environment variable or secret store. Never commit it.

## Orders

```python
from payriff import Currency, Language, Operation

created = payriff.orders.create(
    amount=Decimal("25.00"),
    currency=Currency.AZN,            # default AZN
    operation=Operation.PRE_AUTH,     # default PURCHASE
    language=Language.AZ,
    description="Booking #77",
    callback_url="https://shop.example/payriff/callback",
    metadata={"bookingId": "77"},
)

info = payriff.orders.get(created.order_id)
by_ref = payriff.orders.get_by_request_rrn("order-1001")   # the request_rrn you sent on create

payriff.orders.complete(created.order_id, amount=Decimal("25.00"))
payriff.orders.refund(created.order_id, amount=Decimal("5.00"), refund_reason="Partial return")
payriff.orders.expire(created.order_id)                    # cancel an unpaid order

receipt_pdf: bytes = payriff.orders.download_receipt(created.order_id)
```

`OrderInfo.payment_status` is a `PaymentStatus` such as `APPROVED`, `DECLINED`, `PREAUTH_APPROVED` or
`REFUNDED`. If Payriff adds a status that this SDK version does not know, it returns
`PaymentStatus.UNKNOWN` instead of failing.

Amounts are returned as `Decimal`. You can pass `Decimal`, `int`, `float` or a numeric string.

## Direct payments (host-to-host)

You collect the card details yourself, and the SDK encrypts them before sending
(AES-256-GCM + RSA-OAEP). Raw card data never leaves your server in clear text, but your
systems still handle card data, so PCI DSS requirements apply to you.

```python
from payriff import CardData

result = payriff.payments.direct_pay(
    amount=Decimal("1.00"),
    description="Order #1002",
    callback_url="https://shop.example/payriff/callback",
    request_rrn="order-1002",
    card=CardData(
        pan="4169 7413 3015 1979",
        card_holder="JOHN DOE",
        expiry_month="11",
        expiry_year="27",
        cvv="123",
    ),
)

if result.redirect:
    # 3-D Secure: send the customer's browser to result.redirect_url.
    # The final status arrives via your callback or payriff.orders.get(result.order_id).
    pass
```

`CardData` strips spaces and dashes, pads the month (`1` → `01`), expands a 2-digit year (`27` → `2027`)
and rejects malformed values before any network call. Its `repr()` masks the PAN and omits the CVV.

### Charging a saved card

```python
charge = payriff.payments.auto_pay(
    card_uuid=saved_card_uuid,
    amount=Decimal("9.99"),
    description="Monthly subscription",
    request_rrn="sub-2026-10",
)
```

## Saved cards

```python
import uuid

from payriff import CardSaveStatus

session = payriff.cards.save(
    customer_ref="customer-42",
    callback_url="https://shop.example/payriff/card-saved",
    idempotency_key=str(uuid.uuid4()),
)
# Redirect the customer to session.payment_url to verify the card.

details = payriff.cards.get_save(session.card_save_id)
if details.status is CardSaveStatus.VERIFIED:
    card_uuid = details.card_uuid   # store it; use with auto_pay

cards = payriff.cards.list("customer-42")
payriff.cards.delete(cards[0].card_uuid)
```

## Transactions

```python
from datetime import date

from payriff import PaymentStatus

page = payriff.transactions.list(
    status=PaymentStatus.APPROVED,
    from_date=date(2026, 9, 1),
    to_date=date(2026, 9, 30),
    page=0,
    size=20,                     # server maximum is 20
)

for tx in page.content:
    print(tx.order_id, tx.amount)
```

## Payouts

Payouts require `merchant_id` on the client.

```python
from payriff import TransferState

payriff = Payriff(os.environ["PAYRIFF_APP_KEY"], merchant_id=os.environ["PAYRIFF_MERCHANT_ID"])

masked_name = payriff.payouts.check_cardholder("4169741330151979")   # e.g. "J*** D**"

payout = payriff.payouts.create(
    transfer_amount=Decimal("50.00"),   # minimum 1
    description="Refund for order #1001",
    full_name="JOHN DOE",
    fin_code="1AB2C3D",
    card_pan="4169741330151979",
    request_rrn="payout-1001",
    idempotency_key="payout-1001",
)

status = payriff.payouts.get_by_request_rrn("payout-1001")
history = payriff.payouts.list(status=TransferState.SUCCESS)
receipt = payriff.payouts.download_receipt("payout-1001")
```

## Invoices

Invoices require `merchant_id` on the client.

```python
from datetime import datetime, timedelta

invoice = payriff.invoices.create(
    amount=Decimal("15.00"),
    full_name="JOHN DOE",
    phone_number="+994501234567",
    description="Consultation",
    expire_date=datetime.now() + timedelta(days=7),
    send_sms=True,
)

link = invoice.payment_url   # share with the customer
details = payriff.invoices.get(invoice.invoice_uuid)
```

## Callbacks

When an order changes state, Payriff POSTs JSON to the `callback_url` you set on the order.

```python
from flask import Flask, request

from payriff import PaymentStatus, parse_order_callback

app = Flask(__name__)


@app.post("/payriff/callback")
def payriff_callback():
    notified = parse_order_callback(request.get_data())   # also accepts str or dict

    # Callbacks are not signed: confirm the state with Payriff before fulfilling.
    confirmed = payriff.orders.get(notified.order_id)
    if confirmed.payment_status is PaymentStatus.APPROVED:
        pass  # fulfil the order (make this idempotent: the same callback can arrive more than once)
    return "", 200
```

## Errors

Every SDK error extends `PayriffError`, which carries `http_status`, `code` (Payriff result code)
and `response_id` (quote it when contacting support).

| Exception | When |
|---|---|
| `AuthenticationError` | App key rejected (`14010`, `14013`, `14014`, `14015`) |
| `ValidationError` | Invalid request (`15400` or HTTP 400) |
| `RequestRejectedError` | Business refusal (`01000`), e.g. application under review |
| `InsufficientBalanceError` | Not enough wallet balance for a payout (`01200`) |
| `PayoutLimitError` | Payout limit reached (`01300`, `01400`, `01500`) |
| `ApiError` | Any other failure reported by Payriff |
| `PayriffConnectionError` | No response: network error or timeout |

Payriff can report a failure with HTTP 200. The SDK checks the result code in the body, so you
only need to catch exceptions. Invalid arguments raise `ValueError` before any request is sent.

```python
import logging

from payriff import PayriffConnectionError, PayriffError, ValidationError

log = logging.getLogger(__name__)

try:
    payriff.orders.refund(order_id)
except ValidationError as e:
    log.warning("Refund rejected: %s (%s)", e, e.code)
except PayriffConnectionError:
    pass  # Outcome unknown: check payriff.orders.get(order_id) before retrying
except PayriffError as e:
    log.error("Payriff error %s response_id=%s", e.code, e.response_id)
```

### Retries

The SDK never retries on its own, because payment calls are not safe to repeat blindly. After a
`PayriffConnectionError`, look the operation up first (`orders.get_by_request_rrn(...)`,
`payouts.get_by_request_rrn(...)`) and retry only if it does not exist. Set `request_rrn` /
`idempotency_key` on every request so that this lookup is possible.

## Development

```bash
python -m venv .venv
.venv/bin/pip install -e ".[test]"
.venv/bin/pytest
```

## License

MIT