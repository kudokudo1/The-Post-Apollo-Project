#!/usr/bin/env python3
"""C2f simulated CPU++ request lifecycle over the C2d fake host.

Only an isolated GitHub Actions fixture. NOT a production permission server:
the simulated operator is a test method, not an authenticated human, and a
request ID is a correlation identifier, never an authorization credential.
No QML import, public endpoint, OS keyring or real provider is accessible.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import secrets
import sys
import time
from typing import Callable

HOST_SOURCE = Path(__file__).resolve().parent / "C2dFakeHostSupervisor.py"
spec = importlib.util.spec_from_file_location("c2f_existing_fake_host", HOST_SOURCE)
if spec is None or spec.loader is None:
    raise ImportError("C2F_MISSING_FAKE_HOST")
_host = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_host)

PROVIDER = "nasa-firms"
OPERATION = "fires.hotspots.read"
CONSUMER = "weather-earth"
PROFILE = "ci-only-profile"
ACTIVE = ("PENDING", "APPROVED")
TERMINAL = ("DENIED", "CANCELLED", "EXPIRED", "COMPLETED", "FAILED")
NO_REQUEST = {"ok": False, "reason": "REQUEST_NOT_FOUND"}
NO_HOST = {"ok": False, "reason": "HOST_UNAVAILABLE"}


class FakeRequestLifecycle:
    """One pending request per isolated session. Host owns all state and FDs.

    There is deliberately no consumer-supplied identity parameter and no
    user-facing callable that grants a token. Only the fake host's method
    simulates operator confirmation; this is not adequate production auth.
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._host = _host.FakeConnectionsHost()
        self._now = clock
        self._request: dict | None = None
        self._closed = False

    def start(self) -> dict:
        if self._closed:
            return {"ok": False, "reason": "HOST_ALREADY_CLOSED"}
        result = self._host.start()
        return ({"ok": True, "status": "FAKE_HOST_READY"}
                if result == "C2D_FAKE_RUNTIME_READY" else NO_HOST.copy())

    def _reconcile(self) -> None:
        r = self._request
        if r is None or r["state"] not in ACTIVE:
            return
        if self._host.state != "READY" or not self._host._live():
            r["state"] = "FAILED"
            r["reason"] = "HOST_DISCONNECTED"
            self._host.stop()
            return
        if self._now() >= r["deadline"]:
            if r["state"] == "APPROVED":
                self._host.revoke()
            r["state"] = "EXPIRED"
            r["reason"] = "REQUEST_EXPIRED"

    def _lookup(self, request_id: object) -> dict | None:
        self._reconcile()
        r = self._request
        if not isinstance(request_id, str) or r is None:
            return None
        return r if secrets.compare_digest(request_id, r["id"]) else None

    def request_weather_hotspots(self, *, ttl_ms: int = 15000) -> dict:
        """The trusted fake launcher constructs the scope; not a client claim."""
        self._reconcile()
        if self._closed or self._host.state != "READY" or not self._host._live():
            self._host.stop()
            return NO_HOST.copy()
        if type(ttl_ms) is not int or not 10 <= ttl_ms <= 60000:
            return {"ok": False, "reason": "INVALID_REQUEST_TTL"}
        if self._request is not None and self._request["state"] in ACTIVE:
            return {"ok": False, "reason": "REQUEST_ALREADY_PENDING"}
        request_id = secrets.token_hex(16)
        self._request = {
            "id": request_id, "state": "PENDING", "reason": "AWAITING_SIMULATED_REVIEW",
            "deadline": self._now() + ttl_ms / 1000,
        }
        return {"ok": True, "requestId": request_id, "state": "PENDING",
                "simulated": True}

    def review(self, request_id: object) -> dict:
        """Display-safe status; never includes a secret, FD, token or grant."""
        r = self._lookup(request_id)
        if r is None:
            return NO_REQUEST.copy()
        remaining = max(0, int((r["deadline"] - self._now()) * 1000))
        return {
            "ok": True, "requestId": r["id"], "state": r["state"],
            "provider": PROVIDER, "consumer": CONSUMER,
            "operation": OPERATION, "profile": PROFILE,
            "reason": r["reason"], "expiresInMs": remaining
                if r["state"] in ACTIVE else 0,
            "credentialPresent": False, "realGrantActive": False,
            "canApproveInProduction": False, "simulated": True,
        }

    def operator_decide(self, request_id: object, decision: object,
                        *, confirmed: bool = False) -> dict:
        """Simulated operator's private host action, NOT a public IPC method."""
        r = self._lookup(request_id)
        if r is None:
            return NO_REQUEST.copy()
        if r["state"] != "PENDING":
            return {"ok": False, "reason": "REQUEST_NOT_PENDING"}
        if decision == "deny":
            r["state"] = "DENIED"
            r["reason"] = "OPERATOR_DENIED"
            return {"ok": True, "state": "DENIED", "simulated": True}
        if decision != "approve":
            return {"ok": False, "reason": "DECISION_NOT_ALLOWED"}
        if confirmed is not True:
            return {"ok": False, "reason": "EXPLICIT_CONFIRMATION_REQUIRED"}
        remaining = int((r["deadline"] - self._now()) * 1000)
        if remaining < 1:
            self._reconcile()
            return {"ok": False, "reason": "REQUEST_EXPIRED"}
        granted = self._host.approve(confirmed=True, ttl_ms=min(5000, remaining))
        if granted != {"ok": True, "result": "APPROVED_FAKE_ONLY_ONE_SHOT"}:
            r["state"] = "FAILED"
            r["reason"] = "FAKE_BROKER_APPROVAL_FAILED"
            return {"ok": False, "reason": r["reason"]}
        r["state"] = "APPROVED"
        r["reason"] = "SIMULATED_HOST_APPROVED"
        return {"ok": True, "state": "APPROVED", "simulated": True}

    def cancel(self, request_id: object) -> dict:
        """Host-side cancellation revokes any approved simulated broker grant."""
        r = self._lookup(request_id)
        if r is None:
            return NO_REQUEST.copy()
        if r["state"] not in ACTIVE:
            return {"ok": False, "reason": "REQUEST_ALREADY_FINAL"}
        if r["state"] == "APPROVED":
            self._host.revoke()
        r["state"] = "CANCELLED"
        r["reason"] = "HOST_CANCELLED"
        return {"ok": True, "state": "CANCELLED", "simulated": True}

    def execute_fake(self, request_id: object) -> dict:
        """No arbitrary URL/scope passed to the fake Weather subprocess."""
        r = self._lookup(request_id)
        if r is None:
            return NO_REQUEST.copy()
        if r["state"] != "APPROVED":
            return {"ok": False, "reason": "REQUEST_NOT_APPROVED"}
        # Mark consumed first; even a malformed response cannot replay.
        r["state"] = "FAILED"
        r["reason"] = "FAKE_OPERATION_FAILED"
        result = self._host.read_fake_hotspots()
        if (result.get("ok") is True and
                result.get("kind") == "SYNTHETIC_FIRE_HOTSPOTS" and
                isinstance(result.get("observations"), list) and
                len(result["observations"]) == 2 and
                all(x.get("synthetic") is True for x in result["observations"])):
            r["state"] = "COMPLETED"
            r["reason"] = "SYNTHETIC_OPERATION_COMPLETE"
            return {"ok": True, "state": "COMPLETED", "simulated": True,
                    "observations": result["observations"]}
        return {"ok": False, "reason": "FAKE_OPERATION_FAILED"}

    def close(self) -> dict:
        if self._closed:
            return {"ok": True, "state": "CLOSED"}
        if self._request and self._request["state"] in ACTIVE:
            if self._request["state"] == "APPROVED":
                self._host.revoke()
            self._request["state"] = "CANCELLED"
            self._request["reason"] = "HOST_SHUTDOWN"
        self._host.stop()
        self._closed = True
        return {"ok": True, "state": "CLOSED"}

    def __enter__(self):
        if self.start().get("ok") is not True:
            raise RuntimeError("C2F_FAKE_HOST_START_REFUSED")
        return self

    def __exit__(self, *_):
        self.close()


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] != "--fake-self-check":
        print("REFUSED_C2F_NO_PRODUCTION_ENTRY")
        return 2
    try:
        with FakeRequestLifecycle() as app:
            r = app.request_weather_hotspots()
            if not r["ok"] or app.operator_decide(
                r["requestId"], "approve", confirmed=True
            ).get("ok") is not True:
                raise RuntimeError("C2F_TEST_DENIED")
            outcome = app.execute_fake(r["requestId"])
            if not outcome.get("ok"):
                raise RuntimeError("C2F_FAKE_EXECUTION_DENIED")
        print("C2F_PASS // FAKE_REQUEST_REVIEW_APPROVE_EXECUTE_CLOSE")
        return 0
    except (OSError, RuntimeError, AssertionError, KeyError, ValueError):
        print("REFUSED_C2F_FAKE_TEST")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
