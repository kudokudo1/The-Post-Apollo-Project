#!/usr/bin/env python3
"""C2j real C2f fake-host state -> real server -> real C2i socket reader."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def load(name: str, file: Path):
    spec = importlib.util.spec_from_file_location(name, file)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


server_code = load(
    "c2j_status_server", ROOT / "services/connections/ConnectionsHostStatusServer.py")
client_code = load(
    "c2j_status_reader", ROOT / "services/connections/ConnectionsHostStatusInspect.py")
fake = load(
    "c2j_fake_lifecycle", ROOT / "services/connections/experiments/C2fFakeRequestLifecycle.py")


def assert_observed(root: Path, expected: str) -> None:
    value = client_code.probe(env={"XDG_RUNTIME_DIR": str(root)})
    assert value == {
        "status": "OBSERVED_UNVERIFIED", "provider": "nasa-firms",
        "state": expected, "hostAuthenticated": False,
        "credentialPresent": False, "grantActive": False,
        "canApprove": False,
    }, value


def main():
    previous = os.environ.copy()
    try:
        with tempfile.TemporaryDirectory(prefix="postapollo-c2c-ci-", dir="/tmp") as temp:
            root = Path(temp)
            home = root / "home"
            home.mkdir(mode=0o700)
            marker = root / ".ci-only-authority"
            marker.write_text("C2C_PRIVATE_SOCKETPAIR_ONLY\n")
            marker.chmod(0o600)
            os.environ.update({
                "HOME": str(home), "GITHUB_ACTIONS": "true",
                "POST_APOLLO_C2C_FAKE_ONLY": "1",
            })
            os.environ.pop("POST_APOLLO_FIRMS_MAP_KEY", None)
            with fake.FakeRequestLifecycle() as lifecycle:
                current = {"id": None}

                def host_state():
                    if current["id"] is None:
                        return "IDLE"
                    snapshot = lifecycle.review(current["id"])
                    if snapshot.get("ok") is not True:
                        return "FAILED"
                    return snapshot["state"]

                with server_code.ConnectionsHostStatusServer(
                    runtime_directory=root, status_provider=host_state
                ):
                    assert_observed(root, "IDLE")
                    request = lifecycle.request_weather_hotspots()
                    current["id"] = request["requestId"]
                    assert_observed(root, "PENDING")
                    approval = lifecycle.operator_decide(
                        current["id"], "approve", confirmed=True
                    )
                    assert approval == {
                        "ok": True, "state": "APPROVED", "simulated": True
                    }
                    assert_observed(root, "APPROVED")
                    outcome = lifecycle.execute_fake(current["id"])
                    assert outcome["ok"] is True
                    assert_observed(root, "COMPLETED")
                    current["id"] = lifecycle.request_weather_hotspots()["requestId"]
                    assert_observed(root, "PENDING")
                    assert lifecycle.operator_decide(current["id"], "deny")["ok"] is True
                    assert_observed(root, "DENIED")
                    current["id"] = lifecycle.request_weather_hotspots()["requestId"]
                    assert lifecycle.cancel(current["id"])["state"] == "CANCELLED"
                    assert_observed(root, "CANCELLED")

                value = client_code.probe(env={"XDG_RUNTIME_DIR": str(root)})
                assert value["status"] == "HOST_NOT_FOUND"
            assert sorted(x.name for x in root.iterdir()) == [
                ".ci-only-authority", "home"
            ], "UNEXPECTED_RUNTIME_ARTIFACT"
            assert list(home.iterdir()) == [], "HOST_WROTE_USER_HOME"
    finally:
        os.environ.clear()
        os.environ.update(previous)
    print("C2J_PASS // REAL_FAKE_HOST_STATUS_TO_C2I_SOCKET_WITHOUT_TRUST_GRANTS")


if __name__ == "__main__":
    main()
