from payriff import Region


def test_regions_map_to_base_url_and_currency():
    assert (Region.AZERBAIJAN.base_url, Region.AZERBAIJAN.currency) == ("https://api.payriff.com", "AZN")
    assert (Region.SAUDI.base_url, Region.SAUDI.currency) == ("https://api.gccpay.sa", "SAR")
    assert Region("saudi") is Region.SAUDI


def test_saudi_defaults_to_sar(server):
    payriff = server.client(region=Region.SAUDI)

    server.ok("POST", "/api/v3/orders", {"orderId": "ORD-1"})
    payriff.orders.create(amount=1)
    assert server.last.json()["currency"] == "SAR"

    server.ok("POST", "/api/v3/autoPay", {"orderId": "ORD-2"})
    payriff.payments.auto_pay(card_uuid="card-1", amount=1, description="x")
    assert server.last.json()["currency"] == "SAR"

    server.ok("POST", "/api/v2/invoices", {"invoiceUuid": "inv-1"})
    payriff.invoices.create(amount=1)
    assert server.last.json()["body"]["currencyType"] == "SAR"


def test_explicit_currency_wins_over_region(server):
    server.ok("POST", "/api/v3/orders", {"orderId": "ORD-1"})

    server.client(region=Region.SAUDI).orders.create(amount=1, currency="USD")

    assert server.last.json()["currency"] == "USD"