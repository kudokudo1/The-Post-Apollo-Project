#!/usr/bin/env python3
"""C2c CI-only FD-bound authority proof. Not a production Post-Apollo daemon.

A trusted harness owns both socketpair endpoints at creation, then passes only
one endpoint to the fake Weather client and both broker-facing endpoints to a
fake host broker. The client cannot send operator approval through its FD.
No named socket, credential, keyring, network operation, QML bridge, or disk
state exists in this prototype.
"""
from __future__ import annotations
import json
import os
import re
import selectors
import socket
import stat
import sys
import time
from pathlib import Path

MAX_MESSAGE = 4096
PROVIDER = "nasa-firms"
OPERATION = "fires.hotspots.read"
PROFILE = "ci-only-profile"
CONSUMER = "weather-earth"
FAKE_KEY_PREFIX = "C2C_SYNTHETIC_NEVER_A_REAL_CREDENTIAL_"


def allowed_fixture() -> bool:
    home = os.environ.get("HOME", "")
    if (os.name != "posix" or not sys.platform.startswith("linux")
        or os.environ.get("GITHUB_ACTIONS") != "true"
        or os.environ.get("POST_APOLLO_C2C_FAKE_ONLY") != "1"):
        return False
    if not re.fullmatch(r"/tmp/postapollo-c2c-ci-[A-Za-z0-9_-]+/home", home):
        return False
    root = Path(home).parent
    for directory in (root, Path(home)):
        try:
            info = directory.lstat()
        except OSError:
            return False
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            return False
    try:
        marker = (root / ".ci-only-authority").lstat()
        return (stat.S_ISREG(marker.st_mode) and marker.st_uid == os.getuid()
                and not marker.st_mode & 0o077
                and (root / ".ci-only-authority").read_text().strip()
                == "C2C_PRIVATE_SOCKETPAIR_ONLY")
    except OSError:
        return False


def send(sock: socket.socket, obj: dict) -> None:
    data = json.dumps(obj, separators=(",", ":"), ensure_ascii=True).encode()
    if len(data) > MAX_MESSAGE:
        raise ValueError("oversize response")
    sock.sendall(data)


def receive(sock: socket.socket) -> dict | None:
    buf = sock.recv(MAX_MESSAGE + 1)
    if not buf:
        return None
    if len(buf) > MAX_MESSAGE:
        return {"op": "_invalid", "reason": "TOO_LARGE"}
    try:
        data = json.loads(buf)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"op": "_invalid", "reason": "INVALID_JSON"}
    if not isinstance(data, dict):
        return {"op": "_invalid", "reason": "NON_OBJECT"}
    return data


class Broker:
    def __init__(self):
        self.grant_deadline: float | None = None
        self.provider = PROVIDER
        self.op = OPERATION
        self.profile = PROFILE
        self.alive = True
        self.fake_key = FAKE_KEY_PREFIX + os.urandom(16).hex()
        self.used = 0

    def operator(self, msg: dict) -> dict:
        """Only data arriving on the separately inherited operator FD may grant."""
        cmd = msg.get("op")
        if cmd == "approve":
            # In C2c this is a *simulated operator* channel, not a trusted UI.
            if set(msg) != {"op", "approved", "provider", "operation", "profile", "ttlMs"}:
                return {"ok": False, "reason": "INVALID_APPROVAL_FIELDS"}
            if msg["approved"] is not True:
                return {"ok": False, "reason": "OPERATOR_DID_NOT_APPROVE"}
            if (msg["provider"] != PROVIDER or msg["operation"] != OPERATION
                or msg["profile"] != PROFILE or type(msg["ttlMs"]) is not int
                or not 1 <= msg["ttlMs"] <= 60000):
                return {"ok": False, "reason": "INVALID_APPROVAL_SCOPE"}
            self.grant_deadline = time.monotonic() + msg["ttlMs"] / 1000
            return {"ok": True, "result": "APPROVED_FAKE_ONLY_ONE_SHOT"}
        if cmd == "revoke":
            if set(msg) != {"op"}:
                return {"ok": False, "reason": "INVALID_REVOKE"}
            self.grant_deadline = None
            return {"ok": True, "result": "REVOKED"}
        if cmd == "shutdown":
            if set(msg) != {"op"}:
                return {"ok": False, "reason": "INVALID_SHUTDOWN"}
            self.grant_deadline = None
            self.alive = False
            return {"ok": True, "result": "SHUTDOWN"}
        return {"ok": False, "reason": "HOST_ACTION_UNKNOWN"}

    def client(self, msg: dict) -> dict:
        """The client FD can request one bounded fake operation, never approve."""
        if msg.get("op") != "read":
            return {"ok": False, "reason": "CLIENT_CANNOT_APPROVE_OR_REVOKE"}
        if set(msg) != {"op", "provider", "operation", "profile", "consumer"}:
            return {"ok": False, "reason": "CLIENT_FIELDS_REJECTED"}
        # The consumer field is *checked*, not used to establish identity.
        # Its authority comes solely from the host-distributed descriptor.
        if msg["consumer"] != CONSUMER:
            return {"ok": False, "reason": "CONSUMER_CLAIM_MISMATCH"}
        if msg["provider"] != PROVIDER or msg["operation"] != OPERATION:
            return {"ok": False, "reason": "CROSS_PROVIDER_OR_OPERATION"}
        if msg["profile"] != PROFILE:
            return {"ok": False, "reason": "PROFILE_MISMATCH"}
        if self.grant_deadline is None:
            return {"ok": False, "reason": "NO_OPERATOR_GRANT"}
        if time.monotonic() >= self.grant_deadline:
            self.grant_deadline = None
            return {"ok": False, "reason": "GRANT_EXPIRED"}
        self.grant_deadline = None   # Consume BEFORE fake action.
        self.used += 1
        assert self.fake_key.startswith(FAKE_KEY_PREFIX)  # Internal only.
        return {"ok": True, "kind": "SYNTHETIC_FIRE_HOTSPOTS",
                "provider": PROVIDER, "operation": OPERATION,
                "observations": [
                    {"latitude": 37.91, "longitude": -79.02, "synthetic": True},
                    {"latitude": 37.94, "longitude": -78.97, "synthetic": True}
                ]}


def serve(control_fd: int, client_fd: int) -> None:
    # This deliberately has NO bind/listen path, environment token, or HTTP.
    host = socket.socket(fileno=control_fd)
    weather = socket.socket(fileno=client_fd)
    host.settimeout(8)
    weather.settimeout(8)
    with host, weather, selectors.DefaultSelector() as selector:
        selector.register(host, selectors.EVENT_READ, "operator")
        selector.register(weather, selectors.EVENT_READ, "weather")
        broker = Broker()
        while broker.alive:
            events = selector.select(timeout=8)
            if not events:
                # A disconnected or stalled operator cannot leave grants alive.
                break
            for event, _mask in events:
                sock = event.fileobj
                try:
                    req = receive(sock)
                except (OSError, TimeoutError):
                    broker.alive = False
                    break
                if req is None:
                    broker.alive = False
                    break
                response = (broker.operator(req) if event.data == "operator"
                            else broker.client(req))
                try:
                    send(sock, response)
                except (OSError, TimeoutError):
                    broker.alive = False
                    break
    broker.grant_deadline = None
    broker.fake_key = ""  # No persisted key or grant.


def fake_client(fd: int) -> None:
    with socket.socket(fileno=fd) as sock:
        sock.settimeout(4)
        for line in sys.stdin:
            if len(line) > MAX_MESSAGE:
                sys.stdout.write('{"ok":false,"reason":"INPUT_TOO_LARGE"}\n')
                sys.stdout.flush()
                continue
            try:
                req = json.loads(line)
                send(sock, req)
                response = receive(sock)
                if response is None:
                    raise ConnectionError("broker closed")
            except (ValueError, OSError, ConnectionError, TimeoutError):
                response = {"ok": False, "reason": "BROKER_UNAVAILABLE"}
            sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
            sys.stdout.flush()


def main() -> int:
    if not allowed_fixture():
        print("REFUSED_C2C_PRIVATE_FIXTURE_REQUIRED")
        return 2
    if len(sys.argv) != 4 or sys.argv[1] not in ("--broker", "--client"):
        print("REFUSED_C2C_INVALID_MODE")
        return 2
    try:
        fd1, fd2 = int(sys.argv[2]), int(sys.argv[3])
        if fd1 < 3 or fd2 < 0:
            raise ValueError("invalid fd")
        if sys.argv[1] == "--broker":
            if fd2 < 3 or fd2 == fd1:
                raise ValueError("invalid descriptor pair")
            serve(fd1, fd2)
        else:
            # Client's third argument is an unused placeholder, not authority.
            if fd2 != 0:
                raise ValueError("unexpected client arg")
            fake_client(fd1)
        return 0
    except (ValueError, OSError):
        print("REFUSED_C2C_INVALID_DESCRIPTOR")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
