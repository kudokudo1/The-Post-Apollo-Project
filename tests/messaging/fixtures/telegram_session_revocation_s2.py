#!/usr/bin/env python3
"""Telegram S2 // disposable separated-process fake sign-out host.

Runs only under an explicit nonroot GitHub Actions marker. Reuses C5b's
SO_PASSCRED per-packet kernel identity helper and S1's fake log_out semantics,
WITHOUT importing or broadening C5b's TASKS scopes or production Connections.

The test harness is the "reviewer", NOT an authenticated human. The host is
an ordinary Python process, NOT a signed/SELinux protected production service.
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
import os
from pathlib import Path
import selectors
import socket
import struct
import sys
import time

ROOT = Path(__file__).resolve().parents[3]


def fixed_import(file: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, file)
    if spec is None or spec.loader is None:
        raise RuntimeError("TELEGRAM_S2_SOURCE_MISSING")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


S1 = fixed_import(Path(__file__).with_name("telegram_session_revocation_m1.py"),
                  "tg_s1_pinned")
C5B = fixed_import(ROOT / "services/connections/experiments"
                   / "C5bTasksDurableConsentHost.py", "tg_s2_c5b_packet")
C5A = C5B.C5a
MARKER = "POST_APOLLO_TELEGRAM_S2_CI_ONLY"
MAX_PACKETS = 32
CRED_SIZE = struct.calcsize("3i")


def disposable() -> bool:
    return (sys.platform == "linux" and os.geteuid() != 0
            and os.environ.get("GITHUB_ACTIONS") == "true"
            and os.environ.get("POST_APOLLO_TELEGRAM_S2_DISPOSABLE") == MARKER)


class FakeNativeOwner:
    """In-memory fake per-scope provider, never reads a real session path."""

    def __init__(self):
        self.items = {
            ("shared", ""): self._new("shared", "", "fake-session-shared-s2"),
            ("private", "identity-1"): self._new(
                "private", "identity-1", "fake-session-private-s2"),
        }
        self.logout_calls = 0
        self.fail = False

    @staticmethod
    def _new(target: str, identity: str, nonce: str) -> dict:
        return dict(target=target, identity=identity, epoch=7, nonce=nonce,
                    authorized=True, operationBusy=False)

    def inspect(self, target, identity):
        record = self.items.get((target, identity))
        return dict(record) if record else None

    async def log_out(self, target, identity):
        self.logout_calls += 1
        if self.fail:
            raise RuntimeError("FAKE_LOGOUT_RESULT_UNKNOWN")
        record = self.items[(target, identity)]
        record["authorized"] = False
        record["epoch"] += 1
        return True

    def change_for_test(self, target, identity):
        entry = self.items.get((target, identity))
        if entry is None:
            return False
        entry["epoch"] += 1
        return True


class S2Host:
    def __init__(self):
        self.provider = FakeNativeOwner()
        self.s1 = S1.DisposableTelegramRevocation(
            marker=S1.TEST_MARKER, provider=self.provider, clock=time.monotonic)
        self.client_identity = None
        self.count = 0

    def bind(self, packet):
        if (not S1.exact(packet, {"op", "pid", "uid", "gid"})
                or packet["op"] != "bind"
                or any(type(packet[k]) is not int for k in ("pid", "uid", "gid"))
                or packet["pid"] < 2 or packet["uid"] <= 0
                or packet["gid"] < 0):
            return S1.report("INVALID_CLIENT_BINDING")
        ticks = C5B.process_start_ticks(packet["pid"])
        if ticks is None:
            return S1.report("CLIENT_PID_NOT_FOUND")
        proposed = (packet["pid"], packet["uid"], packet["gid"], ticks)
        if self.client_identity is not None and self.client_identity != proposed:
            return S1.report("CLIENT_ALREADY_BOUND")
        self.client_identity = proposed
        return S1.report("SYNTHETIC_KERNEL_SENDER_BOUND_NO_REAL_GRANT")

    def from_client(self, payload, sender):
        bound = self.client_identity
        if bound is None:
            return S1.report("CALLER_NOT_BOUND")
        if sender is None:
            return S1.report("KERNEL_SENDER_MISSING")
        if sender != bound[:3]:
            return S1.report("KERNEL_SENDER_MISMATCH")
        if C5B.process_start_ticks(bound[0]) != bound[3]:
            return S1.report("CALLER_START_TICKS_CHANGED")
        if type(payload) is not dict or type(payload.get("op")) is not str:
            return S1.report("INVALID_CLIENT_FRAME")
        if payload["op"] == "prepare":
            if not S1.exact(payload, {"op", "scope", "operation", "target", "identity"}):
                return S1.report("INVALID_CLIENT_FIELDS")
            return self.s1.client_prepare({k: v for k, v in payload.items() if k != "op"})
        if payload["op"] == "execute":
            if not S1.exact(payload, {"op", "requestId", "scope", "operation",
                                     "target", "identity"}):
                return S1.report("INVALID_CLIENT_FIELDS")
            return asyncio.run(self.s1.client_execute(
                {k: v for k, v in payload.items() if k != "op"}))
        return S1.report("CLIENT_CANNOT_REVIEW_OR_ADMINISTER")

    def from_reviewer(self, payload):
        if type(payload) is not dict or type(payload.get("op")) is not str:
            return S1.report("INVALID_REVIEW_FRAME")
        if payload["op"] == "bind":
            return self.bind(payload)
        if payload["op"] == "approve":
            required = {"op", "requestId", "scope", "operation", "target", "identity",
                        "confirmRemoteRevocation", "confirmLocalSessionLoss"}
            if not S1.exact(payload, required):
                return S1.report("INVALID_REVIEW_FIELDS")
            return self.s1.synthetic_reviewer_approve(
                {k: v for k, v in payload.items() if k != "op"})
        if payload["op"] == "revoke" and S1.exact(payload, {"op"}):
            return self.s1.synthetic_revoke()
        if payload["op"] == "invalidate" and S1.exact(
                payload, {"op", "target", "identity"}):
            return S1.report("SYNTHETIC_SOURCE_CHANGED"
                             if self.provider.change_for_test(
                                 payload["target"], payload["identity"])
                             else "UNKNOWN_SYNTHETIC_SOURCE")
        if payload["op"] == "failProvider" and S1.exact(payload, {"op"}):
            self.provider.fail = True
            return S1.report("SYNTHETIC_FAILURE_INJECTED")
        if payload["op"] == "shutdown" and S1.exact(payload, {"op"}):
            return S1.report("SYNTHETIC_HOST_SHUTDOWN")
        return S1.report("UNSUPPORTED_REVIEW_OPERATION")


def serve(review_fd: int, client_fd: int, reviewer_pid: int,
          reviewer_uid: int, reviewer_gid: int, reviewer_ticks: int) -> int:
    # Test harness pins the reviewer separately from the client. Descriptor
    # SO_PEERCRED reflects socket creation/transfer provenance, not a signed
    # human identity or necessarily its current packet sender.
    if (reviewer_pid < 2 or reviewer_uid <= 0 or reviewer_gid < 0
            or C5B.process_start_ticks(reviewer_pid) != reviewer_ticks):
        return 2
    reviewer_identity = (reviewer_pid, reviewer_uid, reviewer_gid)
    host = S2Host()
    with (socket.socket(fileno=review_fd) as reviewer,
          socket.socket(fileno=client_fd) as client,
          selectors.DefaultSelector() as events):
        for sock in (reviewer, client):
            if (sock.family != socket.AF_UNIX
                    or sock.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE)
                    != socket.SOCK_SEQPACKET):
                return 2
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
        events.register(reviewer, selectors.EVENT_READ, "reviewer")
        events.register(client, selectors.EVENT_READ, "client")
        while host.count < MAX_PACKETS:
            ready = events.select(timeout=3.0)
            if not ready:
                return 0
            for event, _ in ready:
                sock = event.fileobj
                try:
                    payload, sender = C5B.packet(sock)
                except (OSError, EOFError):
                    return 0
                if event.data == "reviewer":
                    if sender is None:
                        reply = S1.report("REVIEWER_KERNEL_CREDENTIALS_MISSING")
                    elif sender[0] != reviewer_pid:
                        reply = S1.report("REVIEWER_KERNEL_PID_MISMATCH")
                    elif sender[1] != reviewer_uid:
                        reply = S1.report("REVIEWER_KERNEL_UID_MISMATCH")
                    elif sender[2] != reviewer_gid:
                        reply = S1.report("REVIEWER_KERNEL_GID_MISMATCH")
                    elif C5B.process_start_ticks(reviewer_pid) != reviewer_ticks:
                        reply = S1.report("REVIEWER_KERNEL_START_MISMATCH")
                    else:
                        reply = host.from_reviewer(payload)
                else:
                    reply = host.from_client(payload, sender)
                C5A.exchange(sock, reply)
                host.count += 1
                if (event.data == "reviewer" and sender == reviewer_identity
                        and C5B.process_start_ticks(reviewer_pid)
                            == reviewer_ticks
                        and type(payload) is dict
                        and payload.get("op") == "shutdown"
                        and reply["status"] == "SYNTHETIC_HOST_SHUTDOWN"):
                    return 0
    return 0


def client_loop(fd: int) -> int:
    with socket.socket(fileno=fd) as connection:
        # The fixture parent sets a receive timeout on its copy of this
        # descriptor, which marks the shared open file description O_NONBLOCK.
        # Reestablish blocking semantics for the child's send/receive pair.
        connection.setblocking(True)
        if (connection.family != socket.AF_UNIX
                or connection.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE)
                != socket.SOCK_SEQPACKET):
            return 2
        for raw in sys.stdin:
            try:
                payload = json.loads(raw)
                C5A.exchange(connection, payload)
                response = C5A.receive(connection)
                print(json.dumps(response, separators=(",", ":")), flush=True)
            except (OSError, ValueError, TypeError) as exc:
                # Safe test-only diagnostic: exception class/errno, NEVER
                # wire packet contents or session state.
                print("TELEGRAM_S2_CLIENT_IO_REFUSED "
                      + type(exc).__name__ + " "
                      + str(getattr(exc, "errno", "")), file=sys.stderr,
                      flush=True)
                return 2
    return 0


def main() -> int:
    if not disposable():
        print("TELEGRAM_S2_REFUSED_OUTSIDE_NONROOT_DISPOSABLE_CI")
        return 2
    if len(sys.argv) == 8 and sys.argv[1] == "--host":
        return serve(*(int(s) for s in sys.argv[2:]))
    if len(sys.argv) == 3 and sys.argv[1] == "--client":
        return client_loop(int(sys.argv[2]))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
