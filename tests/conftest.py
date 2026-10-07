from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

from payriff import Payriff


@dataclass
class RecordedRequest:
    method: str
    url: str
    headers: dict[str, str]
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body)


class MockServer:
    def __init__(self) -> None:
        self.requests: list[RecordedRequest] = []
        self.stubs: dict[str, tuple[int, dict[str, str], bytes]] = {}
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: Any) -> None:
                pass

            def _handle(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                headers = {k.lower(): v for k, v in self.headers.items()}
                server.requests.append(RecordedRequest(self.command, self.path, headers, body))
                stub = server.stubs.get(f"{self.command} {self.path}") or server.stubs.get(
                    f"{self.command} {self.path.split('?')[0]}"
                )
                if stub is None:
                    self.send_response(404)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                status, extra, payload = stub
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                for k, v in extra.items():
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            do_GET = do_POST = do_PATCH = do_DELETE = _handle

        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self._httpd.server_address[1]}"

    def stub(self, method: str, url: str, *, status: int = 200, headers: dict[str, str] | None = None, body: Any = None) -> None:
        if isinstance(body, (bytes, str)):
            raw = body.encode() if isinstance(body, str) else body
        else:
            raw = b"" if body is None else json.dumps(body).encode()
        self.stubs[f"{method} {url}"] = (status, headers or {}, raw)

    def ok(self, method: str, url: str, payload: Any) -> None:
        self.stub(method, url, body={"code": "00000", "message": "Operation performed successfully", "payload": payload})

    @property
    def last(self) -> RecordedRequest:
        return self.requests[-1]

    def client(self, **options: Any) -> Payriff:
        params: dict[str, Any] = {"merchant_id": "ES1000000", "base_url": self.url, **options}
        return Payriff(params.pop("app_key", "app-key"), **params)

    def close(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()


@pytest.fixture(scope="session")
def _server():
    server = MockServer()
    yield server
    server.close()


@pytest.fixture
def server(_server: MockServer) -> MockServer:
    _server.requests.clear()
    _server.stubs.clear()
    return _server