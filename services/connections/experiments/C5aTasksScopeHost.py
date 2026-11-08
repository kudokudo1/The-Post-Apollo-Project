#!/usr/bin/env python3
"""Connections C5a: real process-separated TASKS scope enforcement, CI ONLY.

Host has two DIFFERENT inherited SOCK_SEQPACKET descriptors. The untrusted
client receives only its request descriptor. The synthetic operator has only
the reviewer descriptor, never reachable through the client protocol.

Nothing here is an actual operator approval, application attestation, true
source receipt, Secret Service credential, production permission, or trusted
deployment artifact. Do not import into the desktop or run on a user session.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import selectors
import socket
import stat
import sys
import time
from secrets import token_hex

SCOPES = frozenset({
    "tasks.draft.capture.encrypted",
    "tasks.draft.preview.unlocked",
    "tasks.draft.clear.encrypted",
})
CAPTURE = "tasks.draft.capture.encrypted"
MAX_WIRE = 1024
MAX_REQUESTS = 16
MAX_TTL_MS = 30000
MARKER = "C5A_DISPOSABLE_DESCRIPTOR_TEST_ONLY"
FLAGS = {
    "hostAuthenticated": False,
    "operatorConsentAuthenticated": False,
    "callerAuthenticated": False,
    "realSourceVerified": False,
    "credentialActionsEnabled": False,
    "keyReleaseAuthorized": False,
    "realDraftCaptureAuthorized": False,
    "realPreviewAuthorized": False,
    "realClearAuthorized": False,
    "sourceWriteAuthorized": False,
    "checkpointChanged": False,
}


def reply(status: str, ok: bool = False, request_id: str | None = None) -> dict:
    value = {"status": status, "ok": bool(ok), **FLAGS}
    if request_id is not None:
        value["requestId"] = request_id
    return value


def exact(value: object, names: set[str]) -> bool:
    return type(value) is dict and set(value) == names


def natural(value: object, *, zero: bool = False) -> bool:
    return type(value) is int and (0 <= value <= 2**31 - 1
                                   if zero else 1 <= value <= 2**31 - 1)


def valid_scope_target(scope: object, target: object,
                       epoch: object, source: object) -> bool:
    if type(scope) is not str or scope not in SCOPES:
        return False
    if type(target) is not str or not natural(source):
        return False
    if scope == CAPTURE:
        return target in ("entry", "details") and natural(epoch)
    return target == "checkpoint" and epoch == 0 and type(epoch) is int


class Broker:
    """Short-lived state lives only in the independently started broker."""
    def __init__(self, clock=None):
        self.clock = clock or time.monotonic
        self.requests: dict[str, dict] = {}
        self.generation = 0
        self.open = True

    def client(self, value: object) -> dict:
        if type(value) is not dict or type(value.get("op")) is not str:
            return reply("INVALID_CLIENT_FRAME")
        operation = value["op"]
        if operation == "submit":
            if not exact(value, {"op", "scope", "target",
                                 "editorEpoch", "sourceGeneration"}):
                return reply("INVALID_REQUEST_FIELDS")
            if not valid_scope_target(value["scope"], value["target"],
                                      value["editorEpoch"], value["sourceGeneration"]):
                return reply("INVALID_SCOPE_OR_TARGET")
            if len(self.requests) >= MAX_REQUESTS:
                return reply("REQUEST_LIMIT_REACHED")
            rid = token_hex(16)
            self.requests[rid] = {
                "scope": value["scope"], "target": value["target"],
                "editorEpoch": value["editorEpoch"],
                "sourceGeneration": value["sourceGeneration"],
                "generation": self.generation, "deadline": 0.0,
                "state": "PENDING",
            }
            return reply("SYNTHETIC_REVIEW_PENDING", True, rid)
        if operation == "execute":
            if not exact(value, {"op", "requestId", "scope", "target",
                                 "editorEpoch", "sourceGeneration"}):
                return reply("INVALID_EXECUTE_FIELDS")
            rid = value["requestId"]
            if type(rid) is not str or re.fullmatch(r"[0-9a-f]{32}", rid) is None:
                return reply("INVALID_REQUEST_ID")
            request = self.requests.get(rid)
            if not request:
                return reply("UNKNOWN_REQUEST")
            if any(value[field] != request[field]
                   or type(value[field]) is not type(request[field])
                   for field in ("scope", "target", "editorEpoch",
                                 "sourceGeneration")):
                return reply("REQUEST_BINDING_CHANGED")
            if request["state"] != "APPROVED":
                return reply("NOT_APPROVED_OR_ALREADY_USED")
            # Consume BEFORE clock, source or any future sensitive operation.
            request["state"] = "CONSUMED"
            if (request["generation"] != self.generation
                    or self.clock() >= request["deadline"]):
                return reply("REVOKED_OR_EXPIRED")
            # The fixed marker proves only synthetic broker state, not
            # permission to handle an editor or access any real resource.
            return reply("SYNTHETIC_SCOPED_STEP_ACCEPTED_NO_REAL_GRANT", True)
        # In particular, "approve", "revoke", "unlock" and "clear" are
        # invalid through the client descriptor.
        return reply("CLIENT_CANNOT_AUTHORIZE")

    def operator(self, value: object) -> dict:
        if type(value) is not dict or type(value.get("op")) is not str:
            return reply("INVALID_REVIEW_FRAME")
        if value["op"] == "approve":
            if not exact(value, {"op", "requestId", "scope", "target",
                                 "ttlMs", "confirmed"}):
                return reply("INVALID_REVIEW_FIELDS")
            rid = value["requestId"]
            request = self.requests.get(rid) if type(rid) is str else None
            if not request or request["state"] != "PENDING":
                return reply("UNKNOWN_OR_ALREADY_REVIEWED")
            if (value["confirmed"] is not True
                    or type(value["scope"]) is not str
                    or type(value["target"]) is not str
                    or value["scope"] != request["scope"]
                    or value["target"] != request["target"]
                    or type(value["ttlMs"]) is not int
                    or not 1 <= value["ttlMs"] <= MAX_TTL_MS):
                return reply("REVIEW_SCOPE_OR_CONSENT_REFUSED")
            request["deadline"] = self.clock() + value["ttlMs"] / 1000
            request["state"] = "APPROVED"
            return reply("SYNTHETIC_OPERATOR_STEP_APPROVED_NO_REAL_GRANT", True)
        if value["op"] == "revoke":
            if not exact(value, {"op"}):
                return reply("INVALID_REVOKE_FIELDS")
            self.generation += 1
            for item in self.requests.values():
                item["state"] = "REVOKED"
            return reply("SYNTHETIC_OPERATOR_REVOKED", True)
        if value["op"] == "shutdown":
            if not exact(value, {"op"}):
                return reply("INVALID_SHUTDOWN_FIELDS")
            self.open = False
            return reply("SYNTHETIC_OPERATOR_SHUTDOWN", True)
        return reply("OPERATOR_OPERATION_REFUSED")


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("DUPLICATE_KEY")
        result[key] = value
    return result


def decode(raw: bytes) -> object:
    if not 0 < len(raw) <= MAX_WIRE:
        return None
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(
                              ValueError("NONFINITE_JSON")))
    except (UnicodeError, ValueError, TypeError):
        return None


def exchange(sock: socket.socket, data: object) -> None:
    raw = json.dumps(data, ensure_ascii=True, separators=(",", ":"),
                     allow_nan=False).encode()
    if len(raw) > MAX_WIRE:
        raise ValueError("FRAME_TOO_LARGE")
    if sock.send(raw) != len(raw):
        raise OSError("SHORT_PACKET")


def receive(sock: socket.socket) -> object:
    # SOCK_SEQPACKET preserves one complete bounded message.
    return decode(sock.recv(MAX_WIRE + 1))


def private_ci() -> bool:
    if (sys.platform != "linux" or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("POST_APOLLO_C5A_DISPOSABLE") != "1"
            or os.geteuid() == 0):
        return False
    value = os.environ.get("POST_APOLLO_C5A_FIXTURE_ROOT", "")
    if not re.fullmatch(r"/tmp/postapollo-c5a-scope-[A-Za-z0-9_-]{8,48}", value):
        return False
    folder = Path(value)
    try:
        info = folder.lstat()
        marker = (folder / ".c5a-test-only").lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) != 0o700
                or not stat.S_ISREG(marker.st_mode)
                or marker.st_uid != os.geteuid()
                or stat.S_IMODE(marker.st_mode) != 0o600):
            return False
        return (folder / ".c5a-test-only").read_text() == MARKER + "\n"
    except OSError:
        return False


def serve(operator_fd: int, client_fd: int) -> int:
    with (socket.socket(fileno=operator_fd) as operator,
          socket.socket(fileno=client_fd) as client,
          selectors.DefaultSelector() as events):
        for s in (operator, client):
            if s.family != socket.AF_UNIX or s.getsockopt(
                    socket.SOL_SOCKET, socket.SO_TYPE) != socket.SOCK_SEQPACKET:
                return 2
            s.settimeout(4.0)
        events.register(operator, selectors.EVENT_READ, "operator")
        events.register(client, selectors.EVENT_READ, "client")
        broker = Broker()
        while broker.open:
            available = events.select(timeout=4.0)
            if not available:
                break
            for item, _mask in available:
                sock = item.fileobj
                try:
                    raw = sock.recv(MAX_WIRE + 1)
                    if not raw:
                        broker.open = False
                        break
                    value = decode(raw)
                    out = (broker.operator(value) if item.data == "operator"
                           else broker.client(value))
                    exchange(sock, out)
                except (OSError, TimeoutError, ValueError):
                    broker.open = False
                    break
        broker.requests.clear()
        return 0


def fake_client(fd: int) -> int:
    with socket.socket(fileno=fd) as sock:
        if sock.family != socket.AF_UNIX or sock.getsockopt(
                socket.SOL_SOCKET, socket.SO_TYPE) != socket.SOCK_SEQPACKET:
            return 2
        sock.settimeout(4.0)
        for line in sys.stdin:
            try:
                if len(line) > MAX_WIRE:
                    response = reply("INVALID_CLIENT_FRAME")
                else:
                    value = decode(line.encode())
                    exchange(sock, value)
                    response = receive(sock)
                    if type(response) is not dict:
                        response = reply("BROKER_UNAVAILABLE")
            except (OSError, TimeoutError, ValueError):
                response = reply("BROKER_UNAVAILABLE")
            sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
            sys.stdout.flush()
        return 0


def main() -> int:
    if not private_ci():
        print("C5A_REFUSED_OUTSIDE_DISPOSABLE_HOST")
        return 2
    if len(sys.argv) != 4 or sys.argv[1] not in ("--host", "--client"):
        print("C5A_REFUSED_INVALID_MODE")
        return 2
    try:
        fd1 = int(sys.argv[2])
        fd2 = int(sys.argv[3])
        if (fd1 < 3
                or (sys.argv[1] == "--host"
                    and (fd2 < 3 or fd1 == fd2))
                or (sys.argv[1] == "--client" and fd2 != 0)):
            raise ValueError("BAD_FD")
        if sys.argv[1] == "--host":
            return serve(fd1, fd2)
        return fake_client(fd1)
    except (ValueError, OSError):
        print("C5A_REFUSED_INVALID_DESCRIPTOR")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
