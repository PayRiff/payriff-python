from __future__ import annotations

import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from ._version import VERSION
from .errors import SUCCESS_CODE, ApiError, PayriffConnectionError, to_api_error

_USER_AGENT = f"payriff-python/{VERSION}"
_MAX_ERROR_BODY = 500


@dataclass
class ApiRequest:
    method: str
    path: str
    query: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, str | None] = field(default_factory=dict)
    body: Any = None
    merchant_envelope: bool = False


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


def _default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "to_json"):
        return value.to_json()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def dumps(value: Any) -> str:
    return json.dumps(value, default=_default, separators=(",", ":"), ensure_ascii=False)


class Transport:
    def __init__(self, base_url: str, app_key: str, merchant_id: str | None, timeout: float):
        self._base_url = base_url.rstrip("/")
        self._app_key = app_key
        self._merchant_id = merchant_id
        self._timeout = timeout
        self._opener = urllib.request.build_opener(_NoRedirect)

    def execute(self, request: ApiRequest) -> Any:
        status, body = self._send(request, "application/json")
        return self._unwrap(status, body.decode("utf-8", errors="replace"))

    def download(self, request: ApiRequest) -> bytes:
        status, body = self._send(request, "application/pdf, application/json")
        if 200 <= status < 300:
            return body
        self._unwrap(status, body.decode("utf-8", errors="replace"))
        raise ApiError("Unexpected response", status)

    def _send(self, request: ApiRequest, accept: str) -> tuple[int, bytes]:
        headers = {"Accept": accept, "User-Agent": _USER_AGENT, "Authorization": self._app_key}
        headers.update({k: v for k, v in request.headers.items() if v is not None})
        data = self._request_body(request)
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(self._url(request), data=data, headers=headers, method=request.method)
        try:
            with self._opener.open(req, timeout=self._timeout) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as e:
            try:
                return e.code, e.read()
            finally:
                e.close()
        except (urllib.error.URLError, socket.timeout, OSError) as e:
            reason = getattr(e, "reason", e)
            raise PayriffConnectionError(f"Payriff request failed: {reason}") from e

    def _url(self, request: ApiRequest) -> str:
        params = {k: str(v) for k, v in request.query.items() if v is not None}
        query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        return self._base_url + request.path + (f"?{query}" if query else "")

    def _request_body(self, request: ApiRequest) -> bytes | None:
        if request.merchant_envelope:
            if not self._merchant_id:
                raise ValueError("merchant_id must be configured on Payriff for this operation")
            return dumps({"merchant": self._merchant_id, "body": request.body or {}}).encode("utf-8")
        if request.body is None:
            return None
        return dumps(request.body).encode("utf-8")

    def _unwrap(self, status: int, text: str) -> Any:
        try:
            root = json.loads(text, parse_float=Decimal) if text else None
        except ValueError:
            root = None
        ok = 200 <= status < 300
        if not isinstance(root, dict) or "code" not in root:
            raise ApiError("Unexpected response from Payriff" if ok else _truncate(text, status), status)
        code = _as_str(root.get("code"))
        response_id = _as_str(root.get("responseId"))
        if not ok or code != SUCCESS_CODE:
            raise to_api_error(_as_str(root.get("message")), status, code, response_id)
        return root.get("payload")


def _as_str(value: Any) -> str | None:
    return None if value is None else str(value)


def _truncate(text: str, status: int) -> str:
    if not text:
        return f"Payriff request failed (HTTP {status})"
    return text[:_MAX_ERROR_BODY] + "..." if len(text) > _MAX_ERROR_BODY else text