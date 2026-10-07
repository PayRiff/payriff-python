from __future__ import annotations


class PayriffError(Exception):
    def __init__(self, message: str, http_status: int = 0, code: str | None = None, response_id: str | None = None):
        super().__init__(message)
        self.message = message
        self.http_status = http_status
        self.code = code
        self.response_id = response_id


class ApiError(PayriffError):
    pass


class AuthenticationError(ApiError):
    pass


class ValidationError(ApiError):
    pass


class RequestRejectedError(ApiError):
    pass


class InsufficientBalanceError(ApiError):
    pass


class PayoutLimitError(ApiError):
    pass


class PayriffConnectionError(PayriffError):
    pass


SUCCESS_CODE = "00000"

_AUTH_CODES = frozenset({"14010", "14013", "14014", "14015"})
_PAYOUT_LIMIT_CODES = frozenset({"01300", "01400", "01500"})
_BY_CODE = {
    "01200": InsufficientBalanceError,
    "01000": RequestRejectedError,
    "15400": ValidationError,
}


def to_api_error(message: str | None, http_status: int, code: str | None, response_id: str | None) -> ApiError:
    msg = message or f"Payriff request failed (HTTP {http_status})"
    if code is not None:
        if code in _AUTH_CODES:
            return AuthenticationError(msg, http_status, code, response_id)
        if code in _PAYOUT_LIMIT_CODES:
            return PayoutLimitError(msg, http_status, code, response_id)
        if code in _BY_CODE:
            return _BY_CODE[code](msg, http_status, code, response_id)
    if http_status in (401, 403):
        return AuthenticationError(msg, http_status, code, response_id)
    if http_status == 400:
        return ValidationError(msg, http_status, code, response_id)
    return ApiError(msg, http_status, code, response_id)