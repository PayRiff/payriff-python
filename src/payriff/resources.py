from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Union

from ._transport import ApiRequest, Transport
from ._util import compact, filter_date, format_datetime, page_query, required, segment
from .card import CardData, CardEncryptor
from .models import (
    AutoPayResponse,
    AutoPaymentType,
    CardSaveDetails,
    CardSaveResponse,
    CreateOrderResponse,
    Currency,
    DirectPayResponse,
    Installment,
    InstallmentProductType,
    Invoice,
    InvoiceDetails,
    Language,
    Operation,
    OrderInfo,
    Page,
    PaymentStatus,
    PayoutResult,
    PayoutStatus,
    PayoutSummary,
    SavedCard,
    Transaction,
    TransferState,
    from_dict,
    page_from_dict,
)

Amount = Union[Decimal, int, float, str]


def _amount(value: Amount | None) -> Decimal | None:
    return None if value is None else Decimal(str(value))


class OrdersApi:
    def __init__(self, transport: Transport):
        self._transport = transport

    def create(
        self,
        *,
        amount: Amount,
        currency: Currency | str = Currency.AZN,
        language: Language | str | None = None,
        operation: Operation | str = Operation.PURCHASE,
        description: str | None = None,
        callback_url: str | None = None,
        redirect_url: str | None = None,
        card_save: bool | None = None,
        three_ds: bool | None = None,
        auto_payment_type: AutoPaymentType | str | None = None,
        installment: Installment | None = None,
        full_name: str | None = None,
        phone_number: str | None = None,
        metadata: dict[str, str] | None = None,
        fields: dict[str, str] | None = None,
        request_rrn: str | None = None,
    ) -> CreateOrderResponse:
        body = compact({
            "amount": _amount(required(amount, "amount")),
            "currency": required(currency, "currency"),
            "language": language,
            "operation": required(operation, "operation"),
            "description": description,
            "callbackUrl": callback_url,
            "redirectUrl": redirect_url,
            "cardSave": card_save,
            "threeDS": three_ds,
            "autoPaymentType": auto_payment_type,
            "installment": installment,
            "fullName": full_name,
            "phoneNumber": phone_number,
            "metadata": metadata,
            "fields": fields,
        })
        payload = self._transport.execute(
            ApiRequest("POST", "/api/v3/orders", headers={"X-REQUEST-RRN": request_rrn}, body=body)
        )
        return from_dict(CreateOrderResponse, payload)  # type: ignore[return-value]

    def get(self, order_id: str) -> OrderInfo:
        payload = self._transport.execute(ApiRequest("GET", f"/api/v3/orders/{segment(order_id, 'order_id')}"))
        return from_dict(OrderInfo, payload)  # type: ignore[return-value]

    def get_status(self, order_id: str) -> OrderInfo:
        payload = self._transport.execute(ApiRequest("GET", f"/api/v3/orders/{segment(order_id, 'order_id')}/status"))
        return from_dict(OrderInfo, payload)  # type: ignore[return-value]

    def get_by_request_rrn(self, request_rrn: str) -> OrderInfo:
        payload = self._transport.execute(ApiRequest("GET", f"/api/v3/orders/{segment(request_rrn, 'request_rrn')}/rrn"))
        return from_dict(OrderInfo, payload)  # type: ignore[return-value]

    def expire(self, order_id: str) -> None:
        segment(order_id, "order_id")
        self._transport.execute(ApiRequest("PATCH", "/api/v3/expire-status", query={"orderId": order_id}))

    def refund(
        self,
        order_id: str,
        *,
        amount: Amount | None = None,
        refund_reason: str | None = None,
        callback_url: str | None = None,
    ) -> None:
        body = compact({
            "orderId": required(order_id, "order_id"),
            "amount": _amount(amount),
            "refundReason": refund_reason,
            "callbackUrl": callback_url,
        })
        self._transport.execute(ApiRequest("POST", "/api/v3/refund", body=body))

    def complete(self, order_id: str, *, amount: Amount | None = None, callback_url: str | None = None) -> None:
        body = compact({"orderId": required(order_id, "order_id"), "amount": _amount(amount), "callbackUrl": callback_url})
        self._transport.execute(ApiRequest("POST", "/api/v3/complete", body=body))

    def download_receipt(self, order_id_or_rrn: str) -> bytes:
        path = f"/api/v3/acquiring/receipt/{segment(order_id_or_rrn, 'order_id_or_rrn')}"
        return self._transport.download(ApiRequest("GET", path))


class PaymentsApi:
    def __init__(self, transport: Transport, card_encryptor: CardEncryptor):
        self._transport = transport
        self._card_encryptor = card_encryptor

    def direct_pay(
        self,
        *,
        amount: Amount,
        description: str,
        card: CardData,
        operation: Operation | str = Operation.PURCHASE,
        currency: Currency | str = Currency.AZN,
        callback_url: str | None = None,
        three_ds: bool | None = None,
        custom_fields: dict[str, str] | None = None,
        card_save: bool = False,
        request_rrn: str | None = None,
    ) -> DirectPayResponse:
        body = compact({
            "amount": _amount(required(amount, "amount")),
            "operation": required(operation, "operation"),
            "currency": required(currency, "currency"),
            "description": required(description, "description"),
            "callbackUrl": callback_url,
            "threeDS": three_ds,
            "customFields": custom_fields,
        })
        if not isinstance(card, CardData):
            raise ValueError("card must be a CardData")
        encrypted = self._card_encryptor.encrypt(card)
        body["paymentData"] = {
            "paymentWay": "DIRECT",
            "encryptedMessage": encrypted.encrypted_message,
            "cardSave": bool(card_save),
        }
        payload = self._transport.execute(ApiRequest(
            "POST",
            "/api/v3/directPay",
            headers={"X-REQUEST-RRN": request_rrn, "x-secret-key": encrypted.secret_key},
            body=body,
        ))
        return from_dict(DirectPayResponse, payload)  # type: ignore[return-value]

    def auto_pay(
        self,
        *,
        card_uuid: str,
        amount: Amount,
        description: str,
        operation: Operation | str = Operation.PURCHASE,
        currency: Currency | str = Currency.AZN,
        callback_url: str | None = None,
        three_ds: bool | None = None,
        one_click_payment: bool | None = None,
        request_rrn: str | None = None,
    ) -> AutoPayResponse:
        body = compact({
            "cardUuid": required(card_uuid, "card_uuid"),
            "amount": _amount(required(amount, "amount")),
            "operation": required(operation, "operation"),
            "currency": required(currency, "currency"),
            "description": required(description, "description"),
            "callbackUrl": callback_url,
            "threeDS": three_ds,
            "isOneCLickPayment": one_click_payment,
        })
        payload = self._transport.execute(
            ApiRequest("POST", "/api/v3/autoPay", headers={"X-REQUEST-RRN": request_rrn}, body=body)
        )
        return from_dict(AutoPayResponse, payload)  # type: ignore[return-value]


class CardsApi:
    def __init__(self, transport: Transport):
        self._transport = transport

    def save(
        self,
        *,
        customer_ref: str,
        callback_url: str,
        description: str | None = None,
        language: Language | str | None = None,
        metadata: dict[str, str] | None = None,
        idempotency_key: str | None = None,
    ) -> CardSaveResponse:
        body = compact({
            "customerRef": required(customer_ref, "customer_ref"),
            "callbackUrl": required(callback_url, "callback_url"),
            "description": description,
            "language": language,
            "metadata": metadata,
        })
        payload = self._transport.execute(
            ApiRequest("POST", "/api/v3/cards/save", headers={"X-Idempotency-Key": idempotency_key}, body=body)
        )
        return from_dict(CardSaveResponse, payload)  # type: ignore[return-value]

    def get_save(self, card_save_id: str) -> CardSaveDetails:
        payload = self._transport.execute(ApiRequest("GET", f"/api/v3/cards/save/{segment(card_save_id, 'card_save_id')}"))
        return from_dict(CardSaveDetails, payload)  # type: ignore[return-value]

    def list(self, customer_ref: str) -> list[SavedCard]:
        segment(customer_ref, "customer_ref")
        payload = self._transport.execute(ApiRequest("GET", "/api/v3/cards/save", query={"customerRef": customer_ref}))
        return [from_dict(SavedCard, c) for c in payload or [] if isinstance(c, dict)]  # type: ignore[misc]

    def delete(self, card_uuid: str) -> None:
        self._transport.execute(ApiRequest("DELETE", f"/api/v3/cards/{segment(card_uuid, 'card_uuid')}"))


class TransactionsApi:
    def __init__(self, transport: Transport):
        self._transport = transport

    def list(
        self,
        *,
        order_id: str | None = None,
        rrn: str | None = None,
        status: PaymentStatus | str | None = None,
        amount: str | None = None,
        description: str | None = None,
        name: str | None = None,
        full_name: str | None = None,
        card_number: str | None = None,
        booking_id: str | None = None,
        invoice_code: str | None = None,
        from_date: date | str | None = None,
        to_date: date | str | None = None,
        page: int = 0,
        size: int = 10,
    ) -> Page[Transaction]:
        query = {
            "orderId": order_id,
            "rrn": rrn,
            "status": status,
            "amount": amount,
            "description": description,
            "name": name,
            "fullName": full_name,
            "cardNumber": card_number,
            "bookingId": booking_id,
            "invoiceCode": invoice_code,
            "from": filter_date(from_date, "from_date"),
            "to": filter_date(to_date, "to_date"),
            **page_query(page, size),
        }
        payload = self._transport.execute(ApiRequest("GET", "/api/v3/transactions", query=query))
        return page_from_dict(Transaction, payload)  # type: ignore[return-value]


_PAN_SEPARATORS = re.compile(r"[\s-]")


class PayoutsApi:
    def __init__(self, transport: Transport):
        self._transport = transport

    def create(
        self,
        *,
        transfer_amount: Amount,
        description: str,
        full_name: str,
        fin_code: str,
        card_pan: str | None = None,
        bank_name: str | None = None,
        card_type: str | None = None,
        request_rrn: str | None = None,
        customer_code: str | None = None,
        voen: str | None = None,
        birth_date: str | None = None,
        callback_url: str | None = None,
        idempotency_key: str | None = None,
    ) -> PayoutResult:
        amount = _amount(required(transfer_amount, "transfer_amount"))
        if amount < 1:  # type: ignore[operator]
            raise ValueError("transfer_amount must be at least 1")
        body = compact({
            "transferAmount": amount,
            "description": required(description, "description"),
            "fullName": required(full_name, "full_name"),
            "finCode": required(fin_code, "fin_code"),
            "cardPan": card_pan,
            "bankName": bank_name,
            "cardType": card_type,
            "requestRrn": request_rrn,
            "customerCode": customer_code,
            "voen": voen,
            "birthDate": birth_date,
            "callbackUrl": callback_url,
        })
        payload = self._transport.execute(ApiRequest(
            "POST",
            "/api/v3/payout",
            headers={"X-IDEMPOTENCY-KEY": idempotency_key},
            body=body,
            merchant_envelope=True,
        ))
        return from_dict(PayoutResult, payload)  # type: ignore[return-value]

    def get_by_request_rrn(self, request_rrn: str) -> PayoutStatus:
        payload = self._transport.execute(ApiRequest("GET", f"/api/v3/payout/info/{segment(request_rrn, 'request_rrn')}"))
        return from_dict(PayoutStatus, payload)  # type: ignore[return-value]

    def check_cardholder(self, card_pan: str) -> str:
        pan = _PAN_SEPARATORS.sub("", str(required(card_pan, "card_pan")))
        if len(pan) != 16 or not pan.isdigit() or not pan.isascii():
            raise ValueError("card_pan must be a 16-digit number")
        result = self._transport.execute(ApiRequest("POST", "/api/v3/payout/check-cardholder", body={"cardPan": pan}))
        return "" if result is None else str(result)

    def list(
        self,
        *,
        rrn: str | None = None,
        status: TransferState | str | None = None,
        amount: str | None = None,
        description: str | None = None,
        full_name: str | None = None,
        fin_code: str | None = None,
        bank_source: str | None = None,
        from_date: date | str | None = None,
        to_date: date | str | None = None,
        page: int = 0,
        size: int = 10,
    ) -> Page[PayoutSummary]:
        query = {
            "rrn": rrn,
            "status": status,
            "amount": amount,
            "description": description,
            "fullName": full_name,
            "finCode": fin_code,
            "bankSource": bank_source,
            "from": filter_date(from_date, "from_date"),
            "to": filter_date(to_date, "to_date"),
            **page_query(page, size),
        }
        payload = self._transport.execute(ApiRequest("GET", "/api/v3/payouts", query=query))
        return page_from_dict(PayoutSummary, payload)  # type: ignore[return-value]

    def download_receipt(self, request_rrn: str) -> bytes:
        return self._transport.download(ApiRequest("GET", f"/api/v3/payout/receipt/{segment(request_rrn, 'request_rrn')}"))


class InvoicesApi:
    def __init__(self, transport: Transport):
        self._transport = transport

    def create(
        self,
        *,
        amount: Amount | None = None,
        amount_dynamic: bool | None = None,
        currency: Currency | str = Currency.AZN,
        language: Language | str | None = None,
        full_name: str | None = None,
        email: str | None = None,
        phone_number: str | None = None,
        description: str | None = None,
        custom_message: str | None = None,
        expire_date: datetime | str | None = None,
        approve_url: str | None = None,
        cancel_url: str | None = None,
        decline_url: str | None = None,
        redirect_url: str | None = None,
        installment_product_type: InstallmentProductType | str | None = None,
        installment_period: int | None = None,
        direct_pay: bool | None = None,
        send_sms: bool | None = None,
        send_whatsapp: bool | None = None,
        send_email: bool | None = None,
        metadata: dict[str, str] | None = None,
        external_transaction_id: str | None = None,
    ) -> Invoice:
        if amount_dynamic is not True and amount is None:
            raise ValueError("amount is required")
        body = compact({
            "amount": _amount(amount),
            "amountDynamic": amount_dynamic,
            "currencyType": currency,
            "languageType": language,
            "fullName": full_name,
            "email": email,
            "phoneNumber": phone_number,
            "description": description,
            "customMessage": custom_message,
            "expireDate": format_datetime(expire_date),
            "approveURL": approve_url,
            "cancelURL": cancel_url,
            "declineURL": decline_url,
            "redirectURL": redirect_url,
            "installmentProductType": installment_product_type,
            "installmentPeriod": installment_period,
            "directPay": direct_pay,
            "sendSms": send_sms,
            "sendWhatsapp": send_whatsapp,
            "sendEmail": send_email,
            "metadata": metadata,
            "externalTransactionId": external_transaction_id,
        })
        payload = self._transport.execute(ApiRequest("POST", "/api/v2/invoices", body=body, merchant_envelope=True))
        return from_dict(Invoice, payload)  # type: ignore[return-value]

    def get(self, invoice_uuid: str) -> InvoiceDetails:
        segment(invoice_uuid, "invoice_uuid")
        payload = self._transport.execute(
            ApiRequest("POST", "/api/v2/get-invoice", body={"uuid": invoice_uuid}, merchant_envelope=True)
        )
        return from_dict(InvoiceDetails, payload)  # type: ignore[return-value]