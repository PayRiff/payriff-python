# Changelog

## 0.2.0 (unreleased)

- Added: Saudi Arabia support via `Payriff(..., region=Region.SAUDI)`. It uses
  `https://api.gccpay.sa` and defaults the currency to `SAR`. Azerbaijan (`AZN`) stays the default.
- Removed: direct (host-to-host) card payments: `payments.direct_pay()`, `CardData` and the
  `card_encryption_key` option. Use the hosted payment page (`orders.create()`) instead.
- Removed the `cryptography` dependency; the SDK has no runtime dependencies now.
- Removed `payriff.client.PRODUCTION_URL`; use `Region.AZERBAIJAN.base_url`.

## 0.1.2 (2026-10-07)

- First release on PyPI.

## 0.1.1 (2026-10-07)

- Published as `payriff-python` (the `payriff` name on PyPI is not ours); the import name stays `payriff`.

## 0.1.0 (2026-10-07)

- Initial release: orders, direct and saved-card payments, saved cards, transactions, payouts,
  v2 invoices, order callback parsing.