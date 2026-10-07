from __future__ import annotations

import json
import re
import types
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Generic, TypeVar, Union, get_args, get_origin, get_type_hints

T = TypeVar("T")


class _Enum(str, Enum):
    def __str__(self) -> str:
        return str(self.value)


class _OpenEnum(_Enum):
    @classmethod
    def _missing_(cls, value: object) -> Any:
        return cls.UNKNOWN  # type: ignore[attr-defined]


class Currency(_Enum):
    AZN = "AZN"
    USD = "USD"
    EUR = "EUR"
    PKR = "PKR"
    AED = "AED"
    SAR = "SAR"


class Language(_Enum):
    AZ = "AZ"
    EN = "EN"
    RU = "RU"
    AR = "AR"


class Operation(_Enum):
    PURCHASE = "PURCHASE"
    PRE_AUTH = "PRE_AUTH"
    COMPLETE = "COMPLETE"
    REFUND = "REFUND"
    REVERSE = "REVERSE"


class AutoPaymentType(_Enum):
    NONE = "NONE"
    DEFAULT = "DEFAULT"
    RECURRING = "RECURRING"


class InstallmentProductType(_Enum):
    BIRKART = "BIRKART"
    ALLBALI = "ALLBALI"
    BOLKART = "BOLKART"
    TAMKART = "TAMKART"


InstallmentPeriod = _Enum(  # type: ignore[call-overload]
    "InstallmentPeriod",
    [("PERIOD", "PERIOD")] + [(f"PERIOD_{i}", f"PERIOD_{i}") for i in range(1, 25)],
)


class PaymentStatus(_OpenEnum):
    CREATED = "CREATED"
    APPROVED = "APPROVED"
    CANCELED = "CANCELED"
    DECLINED = "DECLINED"
    REFUNDED = "REFUNDED"
    PREAUTH_APPROVED = "PREAUTH_APPROVED"
    EXPIRED = "EXPIRED"
    REVERSE = "REVERSE"
    PARTIAL_REFUND = "PARTIAL_REFUND"
    PARTIAL = "PARTIAL"
    ACCEPTED = "ACCEPTED"
    REFUND_IN_PROGRESS = "REFUND_IN_PROGRESS"
    CASH = "CASH"
    PENDING = "PENDING"
    PREAUTH_EXPIRED = "PREAUTH_EXPIRED"
    IN_REVIEW = "IN_REVIEW"
    UNKNOWN = "UNKNOWN"


class CardSaveStatus(_OpenEnum):
    CREATED = "CREATED"
    VERIFIED = "VERIFIED"
    REVERSED = "REVERSED"
    REVERSE_FAILED = "REVERSE_FAILED"
    DECLINED = "DECLINED"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"


class TransferState(_OpenEnum):
    CREATED = "CREATED"
    IN_PROGRESS = "IN_PROGRESS"
    NOT_FOUND = "NOT_FOUND"
    FAIL = "FAIL"
    SUCCESS = "SUCCESS"
    DAILY_PAYOUT_LIMIT_EXCEEDED = "DAILY_PAYOUT_LIMIT_EXCEEDED"
    UNKNOWN = "UNKNOWN"


class InvoiceStatus(_OpenEnum):
    PENDING = "PENDING"
    ERROR = "ERROR"
    EXPIRED = "EXPIRED"
    PARTIAL = "PARTIAL"
    COMPLETE = "COMPLETE"
    CASH = "CASH"
    DECLINED = "DECLINED"
    CANCELED = "CANCELED"
    UNKNOWN = "UNKNOWN"


def _json(name: str) -> Any:
    return field(default=None, metadata={"json": name})


@dataclass(frozen=True)
class Installment:
    type: InstallmentProductType
    period: InstallmentPeriod  # type: ignore[valid-type]

    def to_json(self) -> dict[str, str]:
        return {"type": str(self.type), "period": str(self.period)}


@dataclass(frozen=True)
class CardDetails:
    masked_pan: str | None = None
    brand: str | None = None
    uuid: str | None = None
    card_holder_name: str | None = None
    phone_number: str | None = None


@dataclass(frozen=True)
class OrderTransaction:
    uuid: str | None = None
    created_date: datetime | None = None
    status: str | None = None
    channel: str | None = None
    channel_type: str | None = None
    request_rrn: str | None = None
    response_rrn: str | None = None
    external_rrn: str | None = None
    pan: str | None = None
    payment_way: str | None = None
    card_details: CardDetails | None = None
    card_uuid: str | None = None
    recurrence_id: int | None = None
    response_description: str | None = None
    merchant_category: str | None = None
    installment: Installment | None = None


@dataclass(frozen=True)
class OrderInfo:
    order_id: str = ""
    external_transaction_id: str | None = None
    invoice_uuid: str | None = None
    amount: Decimal | None = None
    currency: Currency | None = _json("currencyType")
    merchant_name: str | None = None
    commission: Decimal | None = None
    commission_rate: Decimal | None = None
    paid_amount: Decimal | None = None
    extra_payment: Decimal | None = None
    operation_type: Operation | None = None
    payment_status: PaymentStatus | None = None
    auto: bool | None = None
    created_date: datetime | None = None
    description: str | None = None
    metadata: str | None = None
    idempotency_key: str | None = None
    transactions: list[OrderTransaction] = field(default_factory=list)


@dataclass(frozen=True)
class CreateOrderResponse:
    order_id: str = ""
    session_id: str | None = None
    payment_url: str | None = None
    preview_url: str | None = None
    transaction_id: int | None = None
    commission_rate: Decimal | None = _json("comissionRate")
    amount: Decimal | None = None
    fee: Decimal | None = None
    total_amount: Decimal | None = None


@dataclass(frozen=True)
class DirectPayResponse:
    order_id: str = ""
    three_ds: bool | None = _json("threeDS")
    redirect: bool | None = None
    redirect_url: str | None = None
    payment_url: str | None = None
    transaction: OrderTransaction | None = _json("transactionResponse")


@dataclass(frozen=True)
class TransactionResponse:
    redirect: bool | None = None
    redirect_url: str | None = None
    three_ds: bool | None = _json("threeDS")
    access_url: str | None = None
    channel: str | None = None
    transaction_result: DirectPayResponse | None = None


@dataclass(frozen=True)
class AutoPayResponse:
    order_id: str = ""
    payment_url: str | None = None
    description: str | None = None
    amount: Decimal | None = None
    commission: Decimal | None = None
    commission_rate: Decimal | None = None
    currency: Currency | None = _json("currencyType")
    operation_type: Operation | None = None
    payment_status: PaymentStatus | None = None
    auto: bool | None = None
    created_date: datetime | None = None
    transactions: list[OrderTransaction] = field(default_factory=list)
    transaction_response: TransactionResponse | None = _json("transactionResponseDto")


@dataclass(frozen=True)
class CardSaveResponse:
    card_save_id: str = ""
    order_id: str | None = None
    session_id: str | None = None
    payment_url: str | None = None
    amount: Decimal | None = None
    currency: Currency | None = None
    status: CardSaveStatus | None = None


@dataclass(frozen=True)
class CardSaveDetails:
    card_save_id: str = ""
    order_id: str | None = None
    status: CardSaveStatus | None = None
    card_uuid: str | None = None
    masked_pan: str | None = None
    card_brand: str | None = None
    amount: Decimal | None = None
    currency: Currency | None = None
    customer_ref: str | None = None
    created_date: datetime | None = None
    verified_date: datetime | None = None


@dataclass(frozen=True)
class SavedCard:
    card_uuid: str = ""
    masked_pan: str | None = None
    card_brand: str | None = None
    created_date: datetime | None = None


@dataclass(frozen=True)
class Transaction:
    id: int | None = None
    application_id: int | None = None
    order_id: str | None = None
    session_id: str | None = None
    uuid: str | None = None
    rrn: str | None = None
    external_rrn: str | None = None
    amount: Decimal | None = None
    paid_amount: Decimal | None = None
    refund_amount: Decimal | None = None
    rest_of_amount: Decimal | None = None
    amount_without_fee: Decimal | None = None
    payriff_amount: Decimal | None = None
    commission_rate: Decimal | None = None
    extra_payment: Decimal | None = _json("extra_payment")
    currency: Currency | None = _json("currencyType")
    payment_status: PaymentStatus | None = None
    payment_source: str | None = None
    description: str | None = None
    response_description: str | None = None
    order_language: Language | None = None
    tariff_type: str | None = None
    source: str | None = None
    full_name: str | None = None
    phone_number: str | None = None
    booking_id: str | None = None
    invoice_code: str | None = None
    pan: str | None = None
    card_brand: str | None = _json("card_brand")
    payment_route: str | None = _json("payment_route")
    payment_way: str | None = _json("payment_way")
    transit_id: str | None = None
    created_date: str | None = None
    last_modified_date: str | None = None


@dataclass(frozen=True)
class Page(Generic[T]):
    content: list[T]
    total_elements: int = 0
    total_pages: int = 0
    number: int = 0
    size: int = 0
    first: bool = False
    last: bool = False


@dataclass(frozen=True)
class PayoutResult:
    final_state: str | None = _json("_final")
    state: str | None = None
    state_description: str | None = None
    current_deposit_balance: Decimal | None = None
    wallet_history_id: int | None = None
    bank_name: str | None = None


@dataclass(frozen=True)
class PayoutStatus:
    bank_name: str | None = None
    state: TransferState | None = None
    card_pan: str | None = None
    transfer_amount: Decimal | None = None
    created_date: str | None = None
    formatted_date: str | None = None
    transfer_type: str | None = None
    merchant: str | None = None
    description: str | None = None
    full_name: str | None = None
    fin_code: str | None = None


@dataclass(frozen=True)
class PayoutSummary:
    id: int | None = None
    request_rrn: str | None = None
    transfer_amount: Decimal | None = None
    amount_with_fee: Decimal | None = None
    fee: Decimal | None = None
    created_date: datetime | None = None
    state: TransferState | None = None
    state_description: str | None = None
    card_pan: str | None = None
    fin_code: str | None = None
    full_name: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class Invoice:
    id: int | None = None
    merchant_id: str | None = None
    uuid: str | None = None
    invoice_uuid: str = ""
    invoice_code: str | None = None
    status: InvoiceStatus | None = _json("invoiceStatus")
    payment_url: str | None = None
    amount: Decimal | None = None
    total_amount: Decimal | None = None
    payriff_amount: Decimal | None = None
    payriff_fee: Decimal | None = None
    payriff_fixed_fee_amount: Decimal | None = None
    currency: Currency | None = _json("currencyType")
    language: Language | None = _json("languageType")
    payment_type: str | None = None
    full_name: str | None = None
    email: str | None = None
    phone_number: str | None = None
    description: str | None = None
    custom_message: str | None = None
    expire_date: datetime | None = None
    created_date: datetime | None = None
    approve_url: str | None = _json("approveURL")
    cancel_url: str | None = _json("cancelURL")
    decline_url: str | None = _json("declineURL")
    active: bool | None = None
    send_sms: bool | None = None


@dataclass(frozen=True)
class InvoiceDetails:
    id: int | None = None
    merchant_id: str | None = None
    uuid: str | None = None
    invoice_uuid: str = ""
    invoice_code: str | None = None
    status: InvoiceStatus | None = _json("invoiceStatus")
    base_url: str | None = None
    amount: Decimal | None = None
    total_amount: Decimal | None = None
    payriff_amount: Decimal | None = None
    payriff_fee: Decimal | None = None
    payriff_fixed_fee_amount: Decimal | None = None
    currency: Currency | None = _json("currencyType")
    language: Language | None = _json("languageType")
    payment_type: str | None = None
    full_name: str | None = None
    email: str | None = None
    phone_number: str | None = None
    description: str | None = None
    expire_date: datetime | None = None
    payment_day: date | None = None
    expire_day: date | None = None
    created_date: datetime | None = None
    approve_url: str | None = _json("approveURL")
    cancel_url: str | None = _json("cancelURL")
    decline_url: str | None = _json("declineURL")
    active: bool | None = None
    installment_period: int | None = None
    source: str | None = None
    direct_pay: bool | None = None
    metadata: str | None = None


def _camel(name: str) -> str:
    head, *rest = name.split("_")
    return head + "".join(p[:1].upper() + p[1:] for p in rest)


_FRACTION = re.compile(r"(\.\d+)")


def _parse_datetime(value: str) -> datetime | None:
    text = value.replace(" ", "T", 1).replace("Z", "+00:00")
    text = _FRACTION.sub(lambda m: m.group(1)[:7].ljust(7, "0"), text, count=1)
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _convert(tp: Any, value: Any) -> Any:
    if value is None:
        return None
    origin = get_origin(tp)
    if origin is Union or origin is types.UnionType:
        inner = [a for a in get_args(tp) if a is not type(None)]
        return _convert(inner[0], value)
    if origin is list:
        if not isinstance(value, list):
            return []
        (item,) = get_args(tp)
        return [_convert(item, v) for v in value]
    if isinstance(tp, type):
        if is_dataclass(tp):
            if not isinstance(value, dict):
                return None
            try:
                return from_dict(tp, value)
            except TypeError:
                return None
        if issubclass(tp, Enum):
            try:
                return tp(value)
            except ValueError:
                return None
        if tp is Decimal:
            return value if isinstance(value, Decimal) else Decimal(str(value))
        if tp is datetime:
            return _parse_datetime(value) if isinstance(value, str) else None
        if tp is date:
            try:
                return date.fromisoformat(value[:10])
            except (TypeError, ValueError):
                return None
        if tp is str:
            return json.dumps(value) if isinstance(value, (dict, list)) else str(value)
        if tp is bool:
            return value if isinstance(value, bool) else str(value).lower() == "true"
        if tp is int:
            try:
                return int(value)
            except (TypeError, ValueError):
                return None
    return value


def from_dict(cls: type[T], data: dict[str, Any] | None) -> T | None:
    if data is None:
        return None
    hints = get_type_hints(cls)
    kwargs: dict[str, Any] = {}
    for f in fields(cls):  # type: ignore[arg-type]
        key = f.metadata.get("json", _camel(f.name))
        if key in data:
            converted = _convert(hints[f.name], data[key])
            if converted is not None:
                kwargs[f.name] = converted
    return cls(**kwargs)


def page_from_dict(item: type[T], data: dict[str, Any] | None) -> Page[T] | None:
    if data is None:
        return None
    content = data.get("content") or []
    return Page(
        content=[from_dict(item, c) for c in content if isinstance(c, dict)],  # type: ignore[misc]
        total_elements=int(data.get("totalElements") or 0),
        total_pages=int(data.get("totalPages") or 0),
        number=int(data.get("number") or 0),
        size=int(data.get("size") or 0),
        first=bool(data.get("first")),
        last=bool(data.get("last")),
    )