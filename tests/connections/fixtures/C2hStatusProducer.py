#!/usr/bin/env python3
"""C2h CI-only status producer: C2f real fake-host states over stdout JSON lines.

No production handler. Never starts under a normal user's HOME, never opens
Secret Service, network sockets, real NASA, or an authenticated desktop channel.
Its stdout is untrusted display data. A requestId is NOT a grant/capability.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
HOST = ROOT / "services/connections/experiments/C2fFakeRequestLifecycle.py"
C2C = ROOT / "tests/connections/fixtures/C2cDescriptorBroker.py"


def load(name: str, location: Path):
    spec = importlib.util.spec_from_file_location(name, location)
    if spec is None or spec.loader is None:
        raise RuntimeError("C2H_FIXTURE_MISSING")
    instance = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(instance)
    return instance


def private_only() -> bool:
    return load("c2h_fixture_guard", C2C).allowed_fixture()


class FakeClock:
    def __init__(self) -> None:
        self.ticks = 9000.0

    def __call__(self) -> float:
        return self.ticks

    def advance(self, ms: int) -> None:
        self.ticks += ms / 1000


def emit(snapshot: dict) -> None:
    # Exact C2f review shape only, not arbitrary host output or credentials.
    keys = {
        "ok", "requestId", "state", "provider", "consumer", "operation",
        "profile", "reason", "expiresInMs", "credentialPresent",
        "realGrantActive", "canApproveInProduction", "simulated",
    }
    if not isinstance(snapshot, dict) or set(snapshot) != keys:
        raise RuntimeError("C2H_UNSAFE_SNAPSHOT")
    if (snapshot["ok"] is not True
        or snapshot["simulated"] is not True
        or snapshot["credentialPresent"] is not False
        or snapshot["realGrantActive"] is not False
        or snapshot["canApproveInProduction"] is not False
        or snapshot["provider"] != "nasa-firms"
        or snapshot["consumer"] != "weather-earth"
        or snapshot["operation"] != "fires.hotspots.read"
        or snapshot["profile"] != "ci-only-profile"):
        raise RuntimeError("C2H_SCOPE_INVALID")
    payload = json.dumps(snapshot, separators=(",", ":"), ensure_ascii=True)
    if len(payload) > 1024 or "\n" in payload:
        raise RuntimeError("C2H_FRAME_OVERSIZE")
    sys.stdout.write(payload + "\n")
    sys.stdout.flush()


def run_fake() -> None:
    module = load("c2h_fake_request_lifecycle", HOST)
    clock = FakeClock()
    with module.FakeRequestLifecycle(clock=clock) as app:
        def create(ttl_ms: int = 15000) -> str:
            new = app.request_weather_hotspots(ttl_ms=ttl_ms)
            if new.get("state") != "PENDING":
                raise RuntimeError("C2H_CREATE_REFUSED")
            rid = new["requestId"]
            emit(app.review(rid))
            return rid

        rid = create()
        if not app.operator_decide(rid, "approve", confirmed=True).get("ok"):
            raise RuntimeError("C2H_APPROVAL_REFUSED")
        emit(app.review(rid))
        if not app.execute_fake(rid).get("ok"):
            raise RuntimeError("C2H_FAKE_EXECUTION_REFUSED")
        emit(app.review(rid))

        rid = create()
        if app.operator_decide(rid, "deny").get("state") != "DENIED":
            raise RuntimeError("C2H_DENIAL_REFUSED")
        emit(app.review(rid))

        rid = create()
        if app.cancel(rid).get("state") != "CANCELLED":
            raise RuntimeError("C2H_CANCELLATION_REFUSED")
        emit(app.review(rid))

        rid = create(20)
        clock.advance(25)
        emit(app.review(rid))  # EXPIRED, never approved.

        rid = create()
        if app.operator_decide(rid, "approve", confirmed=True).get("state") != "APPROVED":
            raise RuntimeError("C2H_SECOND_APPROVAL_REFUSED")
        emit(app.review(rid))
        # Fault injection proves a dead broker produces FAILED, not a
        # stale "APPROVED" display. C2f reaps the Weather process.
        proc = app._host._broker
        proc.kill()
        proc.wait(timeout=3)
        emit(app.review(rid))  # FAILED / HOST_DISCONNECTED.


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] != "--c2h-fake-stream":
        print("C2H_REFUSED_MODE", file=sys.stderr)
        return 2
    if not private_only():
        print("C2H_REFUSED_NOT_PRIVATE", file=sys.stderr)
        return 2
    try:
        run_fake()
        return 0
    except (OSError, ValueError, RuntimeError, KeyError, TimeoutError):
        print("C2H_REFUSED_HOST_STATUS", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
