from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from .models import OrderInfo, from_dict

_NOT_A_CALLBACK = "Not a Payriff order callback"


def parse_order_callback(body: str | bytes | dict[str, Any]) -> OrderInfo:
    root: Any = body
    if isinstance(body, (str, bytes, bytearray)):
        try:
            root = json.loads(body, parse_float=Decimal)
        except ValueError as e:
            raise ValueError(_NOT_A_CALLBACK) from e
    payload = root.get("payload") if isinstance(root, dict) else None
    if not isinstance(payload, dict) or payload.get("orderId") is None:
        raise ValueError(_NOT_A_CALLBACK)
    return from_dict(OrderInfo, payload)  # type: ignore[return-value]