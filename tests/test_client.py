import pytest

from payriff import Payriff


@pytest.mark.parametrize("app_key", ["", "  ", None])
def test_app_key_is_required(app_key):
    with pytest.raises(ValueError, match="^app_key is required$"):
        Payriff(app_key)


def test_timeout_must_be_positive():
    with pytest.raises(ValueError):
        Payriff("k", timeout=0)


def test_exposes_all_api_groups():
    payriff = Payriff("k")

    for group in ("orders", "payments", "cards", "transactions", "payouts", "invoices"):
        assert getattr(payriff, group) is not None