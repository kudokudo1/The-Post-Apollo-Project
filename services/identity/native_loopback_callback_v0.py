"""Explicit, CI-only native OAuth loopback callback receiver prototype.

This module is NOT a deployed desktop service. Constructing it does NOT open
a port. Calling start() intentionally binds ONLY 127.0.0.1 on a random port.
The owning privileged process must configure DesktopSessionHost.redirect_uri
from receiver.redirect_uri *before* start_login(), launch the system browser,
then call close() on completion, cancellation, timeout and process shutdown.

NO listener is started by importing this module. No token, login code, nonce,
state, authorization URL, password, exception or request target is logged or
returned to the HTTP client. Do not expose a receiver object to Social QML.

This is a disposable transport test, not a hardened production local server:
resource limits, hostile same-user processes, lifecycle orchestration, OS
keyrings, IdP verification, remote logout and secure UI IPC require review.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import threading
from collections.abc import Callable


class _PrivateServer(ThreadingMixIn, HTTPServer):
    allow_reuse_address = False
    daemon_threads = True
    block_on_close = False
    request_queue_size = 4


class LoopbackCallbackReceiver:
    """Bound, one-use, explicitly owned 127.0.0.1 OAuth callback receiver.

    callback is a privileged host closure, normally host.complete_callback.
    It must NOT be an untrusted UI callback. Its result is used only as an
    internal success/fail indicator; sensitive results are not returned.
    """

    def __init__(self, *, callback: Callable[[str], dict[str, object]],
                 port: int = 0) -> None:
        if not callable(callback):
            raise ValueError("A host-owned callback is required")
        # Explicit nonzero port is ONLY for matching the existing disposable
        # Keycloak CI realm's fixed registration. Normal native hosts use 0
        # for an OS-selected ephemeral loopback port.
        if type(port) is not int or (port != 0 and not 1024 <= port <= 65535):
            raise ValueError("Invalid loopback callback port")
        self._port = port
        self._callback = callback
        self._lock = threading.Lock()
        self._used = False
        self._server: _PrivateServer | None = None
        self._worker: threading.Thread | None = None

    @property
    def redirect_uri(self) -> str:
        """Host-only pinned callback URI; not a QML property."""
        server = self._server
        if server is None:
            raise RuntimeError("The listener was not started")
        return "http://127.0.0.1:" + str(server.server_port) + "/callback"

    def start(self) -> None:
        if self._server is not None or self._used:
            raise RuntimeError("This receiver cannot be restarted")
        receiver = self

        class _Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, format, *args):
                # BaseHTTPRequestHandler logs the path (OAuth code + state)
                # by default. This must never be logged, including on error.
                return

            def _reply(self, code: int, text: bytes) -> None:
                self.send_response(code)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(text)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("Pragma", "no-cache")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
                self.send_header("Connection", "close")
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(text)
                self.close_connection = True

            def do_GET(self):
                expected_host = "127.0.0.1:" + str(self.server.server_port)
                supplied_host = self.headers.get_all("Host", [])
                if (len(supplied_host) != 1
                        or supplied_host[0] != expected_host
                        or self.headers.get("Transfer-Encoding") is not None
                        or self.headers.get("Content-Length") not in (None, "0")
                        or self.headers.get("Origin") is not None):
                    self._reply(400, b"Authentication response rejected.")
                    return
                if not self.path.startswith("/callback?") or len(self.path) > 4096:
                    self._reply(404, b"Not found.")
                    return
                with receiver._lock:
                    if receiver._used:
                        self._reply(410, b"Authentication response unavailable.")
                        return
                    # Consume even malformed callback attempts: never permit
                    # replay after the first well-formed HTTP route arrives.
                    receiver._used = True
                try:
                    uri = receiver.redirect_uri.split("/callback", 1)[0] + self.path
                    result = receiver._callback(uri)
                    success = (type(result) is dict
                               and result == {"status": "SIGNED_IN"})
                except Exception:
                    success = False
                if success:
                    self._reply(200, b"Authentication response received. Return to Post-Apollo.")
                else:
                    self._reply(400, b"Authentication response rejected.")

            def do_POST(self):
                self._reply(405, b"Method not allowed.")

            def do_HEAD(self):
                self._reply(405, b"Method not allowed.")

            def do_PUT(self):
                self._reply(405, b"Method not allowed.")

            def do_DELETE(self):
                self._reply(405, b"Method not allowed.")

        # Server is only ever bound to numeric loopback, never localhost,
        # ::, 0.0.0.0 or a selected external address.
        server = _PrivateServer(("127.0.0.1", self._port), _Handler)
        self._server = server
        worker = threading.Thread(
            target=server.serve_forever,
            kwargs={"poll_interval": 0.05},
            name="identity-ci-loopback-callback",
            daemon=True,
        )
        self._worker = worker
        try:
            worker.start()
        except Exception:
            server.server_close()
            self._server = None
            self._worker = None
            self._used = True
            raise

    def close(self) -> None:
        """Stop listening and prohibit reuse. Safe repeated close."""
        self._used = True
        server, worker = self._server, self._worker
        self._server = None
        self._worker = None
        if server is not None:
            server.shutdown()
            server.server_close()
        if worker is not None and worker is not threading.current_thread():
            worker.join(timeout=5)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
