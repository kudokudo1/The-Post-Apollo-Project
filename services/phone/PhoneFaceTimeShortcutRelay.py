#!/usr/bin/env python3
"""Opt-in loopback FaceTime request relay for a manually run iPhone Shortcut.

This is a *request* relay, not a FaceTime API, incoming-call monitor, or a
remote video/audio source. It never starts by importing or reading PHONE.
A separate operator-approved HTTPS reverse proxy and manually installed iOS
Shortcut are needed for a real iPhone to reach the phone-side endpoints.

No default listener, non-loopback bind, private logs, persisted contacts or
requests, phone calls, shell commands, Bluetooth changes, or notification reads.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import stat
import threading
import time
from typing import Callable

SCHEMA = "post-apollo.phone.facetime-shortcuts-relay.v1"
MAX_REQUEST_BYTES = 512
REQUEST_TTL_SECONDS = 90
TARGET = re.compile(r"(?:\+[1-9][0-9]{2,14}|[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)")
REQUEST_ID = re.compile(r"[A-Za-z0-9_-]{22,48}")
STATES = frozenset({
    "EMPTY", "QUEUED", "DELIVERED_TO_SHORTCUT", "PHONE_REPORTED_OPEN_REQUEST",
    "PHONE_DECLINED", "CANCELLED", "EXPIRED",
})
TERMINAL = frozenset({
    "PHONE_REPORTED_OPEN_REQUEST", "PHONE_DECLINED", "CANCELLED", "EXPIRED",
})


@dataclass(slots=True)
class _Request:
    id: str
    mode: str
    target: str
    created: int
    expires: int
    state: str = "QUEUED"


class Relay:
    """One pending request, bounded lifetime, no persistence or call authority."""

    def __init__(
        self, admin_token: str, phone_token: str,
        *, clock: Callable[[], float] = time.time,
        new_id: Callable[[int], str] = secrets.token_urlsafe,
    ) -> None:
        if (type(admin_token) is not str or len(admin_token) < 43
                or type(phone_token) is not str or len(phone_token) < 43
                or hmac.compare_digest(admin_token, phone_token)):
            raise ValueError("invalid relay credentials")
        self._admin = admin_token
        self._phone = phone_token
        self._clock = clock
        self._new_id = new_id
        self._lock = threading.Lock()
        self._request: _Request | None = None

    def authorize(self, role: str, header: object) -> bool:
        if role not in ("admin", "phone") or type(header) is not str:
            return False
        expected = self._admin if role == "admin" else self._phone
        # No accidental token match through truncation or Unicode changes.
        if len(header) != len(expected) + 7 or not header.startswith("Bearer "):
            return False
        return hmac.compare_digest(header[7:], expected)

    def _expire(self) -> None:
        req = self._request
        if req is not None and req.state not in TERMINAL:
            if int(self._clock()) >= req.expires:
                req.state = "EXPIRED"

    @staticmethod
    def _public(req: _Request | None) -> dict[str, object]:
        # Neither status nor error responses can disclose a recipient or
        # request ID. Possession of the admin token alone is not FaceTime.
        return {
            "schema": SCHEMA,
            "state": req.state if req is not None else "EMPTY",
            "iphoneWorkflowReportedRequest": (
                req is not None and req.state == "PHONE_REPORTED_OPEN_REQUEST"),
            "faceTimeConnected": False,
            "incomingCallObserved": False,
            "canAnswer": False,
            "canHangup": False,
            "audioVerified": False,
            "videoStreamAvailable": False,
            "authenticatedAppleFaceTimeSession": False,
            "personalDataAccess": False,
        }

    def status(self) -> dict[str, object]:
        with self._lock:
            self._expire()
            return self._public(self._request)

    def prepare(self, body: object) -> bool:
        # Called by a separate operator action. Never automatically dial.
        if type(body) is not dict or set(body) != {"mode", "target"}:
            return False
        mode, target = body["mode"], body["target"]
        if mode not in ("audio", "video") or type(target) is not str:
            return False
        if len(target) > 254 or TARGET.fullmatch(target) is None:
            return False
        with self._lock:
            self._expire()
            if self._request is not None and self._request.state not in TERMINAL:
                return False
            now = int(self._clock())
            rid = self._new_id(18)
            if type(rid) is not str or REQUEST_ID.fullmatch(rid) is None:
                return False
            self._request = _Request(
                id=rid, mode=mode, target=target,
                created=now, expires=now + REQUEST_TTL_SECONDS)
            return True

    def claim(self) -> dict[str, object]:
        # Only authenticated phone-side request path may call this.
        with self._lock:
            self._expire()
            req = self._request
            if req is None or req.state in TERMINAL:
                return {"schema": SCHEMA, "state": "NONE"}
            req.state = "DELIVERED_TO_SHORTCUT"
            uri = ("facetime-audio:" if req.mode == "audio" else "facetime:") + req.target
            return {
                "schema": SCHEMA,
                "state": "DELIVERED_TO_SHORTCUT",
                "requestId": req.id,
                "mode": req.mode,
                # Destination is intentionally disclosed ONLY to the phone
                # credential holder at explicit polling time.
                "faceTimeUri": uri,
                "expiresAt": req.expires,
                "faceTimeConnected": False,
            }

    def acknowledge(self, body: object) -> bool:
        if type(body) is not dict or set(body) != {"requestId", "event"}:
            return False
        rid, event = body["requestId"], body["event"]
        if (type(rid) is not str or REQUEST_ID.fullmatch(rid) is None
                or event not in ("OPEN_URL_REQUESTED", "DECLINED")):
            return False
        with self._lock:
            self._expire()
            req = self._request
            if (req is None or req.state != "DELIVERED_TO_SHORTCUT"
                    or not hmac.compare_digest(req.id, rid)):
                return False
            req.state = ("PHONE_REPORTED_OPEN_REQUEST"
                         if event == "OPEN_URL_REQUESTED" else "PHONE_DECLINED")
            return True

    def cancel(self) -> bool:
        with self._lock:
            self._expire()
            req = self._request
            if req is None or req.state in TERMINAL:
                return False
            req.state = "CANCELLED"
            return True


class _LoopbackOnly(ThreadingHTTPServer):
    allow_reuse_address = False
    daemon_threads = True

    def __init__(self, address: tuple[str, int], relay: Relay):
        if address[0] != "127.0.0.1":
            raise ValueError("relay must bind only to loopback")
        self.relay = relay
        super().__init__(address, _Handler)


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "PostApollo"
    sys_version = ""

    def log_message(self, _format: str, *_args: object) -> None:
        # HTTP paths/addresses, request body, target, tokens are never logged.
        pass

    def log_error(self, _format: str, *_args: object) -> None:
        pass

    def _respond(self, code: int, payload: dict[str, object]) -> None:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Pragma", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'none'")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(raw)
        self.close_connection = True

    def _error(self, status: int) -> None:
        self._respond(status, {"schema": SCHEMA, "state": "REFUSED"})

    def _authorized(self, role: str) -> bool:
        relay = self.server.relay
        if not relay.authorize(role, self.headers.get("Authorization")):
            self._error(403)
            return False
        return True

    def _body(self) -> object | None:
        if (self.headers.get("Content-Type") != "application/json"
                or self.headers.get("Transfer-Encoding") is not None):
            return None
        raw_len = self.headers.get("Content-Length")
        if (raw_len is None or not raw_len.isascii() or not raw_len.isdecimal()
                or not 1 <= int(raw_len) <= MAX_REQUEST_BYTES):
            return None
        data = self.rfile.read(int(raw_len))
        if len(data) != int(raw_len):
            return None
        try:
            return json.loads(data.decode("utf-8"))
        except (ValueError, UnicodeError):
            return None

    def do_GET(self) -> None:
        if self.path == "/v1/operator/status":
            if not self._authorized("admin"):
                return
            self._respond(200, self.server.relay.status())
        elif self.path == "/v1/iphone/next":
            if not self._authorized("phone"):
                return
            self._respond(200, self.server.relay.claim())
        else:
            self._error(404)

    def do_POST(self) -> None:
        roles = {
            "/v1/operator/request": "admin",
            "/v1/operator/cancel": "admin",
            "/v1/iphone/ack": "phone",
        }
        role = roles.get(self.path)
        if role is None:
            self._error(404)
            return
        if not self._authorized(role):
            return
        if self.path == "/v1/operator/cancel":
            if self.headers.get("Content-Length") not in (None, "0"):
                self._error(400)
                return
            success = self.server.relay.cancel()
        else:
            body = self._body()
            if body is None:
                self._error(400)
                return
            success = (
                self.server.relay.prepare(body)
                if role == "admin"
                else self.server.relay.acknowledge(body))
        if not success:
            self._error(409)
        else:
            self._respond(200, self.server.relay.status())

    def do_OPTIONS(self) -> None:
        self._error(405)


def _load_token(filename: str) -> str:
    """Refuse shared/group-readable files, symlinks or unsafe token content."""
    file = Path(filename)
    info = file.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
        raise ValueError("unsafe credentials file")
    if info.st_uid != os.getuid() or info.st_size > 256:
        raise ValueError("unsafe credentials file")
    raw = file.read_text(encoding="ascii").strip()
    if len(raw) < 43 or re.fullmatch(r"[A-Za-z0-9_-]{43,128}", raw) is None:
        raise ValueError("invalid credentials")
    return raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Manually started loopback FaceTime request relay; NO iPhone calls")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--admin-token-file")
    parser.add_argument("--iphone-token-file")
    args = parser.parse_args(argv)
    if not args.serve or not (1024 <= args.port <= 65535):
        return 2
    if not args.admin_token_file or not args.iphone_token_file:
        return 2
    try:
        relay = Relay(_load_token(args.admin_token_file),
                      _load_token(args.iphone_token_file))
        server = _LoopbackOnly(("127.0.0.1", args.port), relay)
    except (OSError, ValueError, UnicodeError):
        return 2
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
