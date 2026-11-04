#!/usr/bin/env python3
"""C2d isolated host-launch lifecycle, fake Weather requests and fail-closed CI."""
from __future__ import annotations

from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SUPERVISOR = ROOT / "services/connections/experiments/C2dFakeHostSupervisor.py"
C2C = ROOT / "tests/connections/fixtures/C2cDescriptorBroker.py"
spec = importlib.util.spec_from_file_location("c2d_host", SUPERVISOR)
assert spec is not None and spec.loader is not None
host_code = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host_code)


@contextmanager
def disposable_test_home():
    with tempfile.TemporaryDirectory(prefix="postapollo-c2c-ci-", dir="/tmp") as root:
        folder = Path(root)
        home = folder / "home"
        home.mkdir(mode=0o700)
        marker = folder / ".ci-only-authority"
        marker.write_text("C2C_PRIVATE_SOCKETPAIR_ONLY\n", encoding="utf8")
        marker.chmod(0o600)
        old = os.environ.copy()
        os.environ.update({
            "HOME": str(home), "GITHUB_ACTIONS": "true",
            "POST_APOLLO_C2C_FAKE_ONLY": "1",
            "POST_APOLLO_FIRMS_MAP_KEY": "SHOULD_NOT_REACH_ANY_CHILD",
            "PYTHONPATH": "/tmp/NEVER_PASS_THIS_PYTHONPATH",
        })
        try:
            yield folder, home
        finally:
            os.environ.clear()
            os.environ.update(old)
            assert sorted(p.name for p in folder.iterdir()) == [
                ".ci-only-authority", "home",
            ], "UNEXPECTED_HOST_FILE_WRITE"
            assert list(home.iterdir()) == [], "HOST_RUNTIME_CREATED_USER_STATE"


def refused(actual: dict, why: str) -> None:
    assert actual == {"ok": False, "reason": why}, (actual, why)


def must_be_reaped(host) -> None:
    assert host.state == "CLOSED"
    for process in (host._broker, host._weather):
        if process is not None:
            assert process.poll() is not None, "ORPHAN_HOST_CHILD"
    assert host._control is None


def static_guards():
    script = SUPERVISOR.read_text(encoding="utf8")
    fixture = C2C.read_text(encoding="utf8")
    assert "if __name__ == \"__main__\":" in script
    assert "def _guard()" in script and "allowed_fixture()" in script
    assert "pass_fds=" in script and "close_fds=True" in script
    assert "socket.socketpair(" in script and "socket.SOCK_SEQPACKET" in script
    assert 'return "C2D_ALREADY_CLOSED"' in script
    assert "subprocess.DEVNULL" in script
    assert "process.wait(timeout=1)" in script
    assert "process.kill()" in script
    assert '"POST_APOLLO_FIRMS_MAP_KEY"' not in script.split("def _child_env()")[1].split("class FakeConnectionsHost")[0]
    for forbidden in (".bind(", ".listen(", "SO_PEERCRED", "secret-tool",
                      "https://", "http://", "curl ", "Keyring", "Quickshell"):
        assert forbidden not in script, forbidden
    assert "FAKE_KEY_PREFIX" in fixture
    assert "OPERATOR_DID_NOT_APPROVE" in fixture
    production = (ROOT / "services/connections/ConnectionsBroker.qml").read_text()
    policy = (ROOT / "services/connections/ConnectionsBrokerPolicy.js").read_text()
    assert "readonly property bool credentialActionsEnabled: false" in production
    assert 'reason:"TRUSTED_BROKER_NOT_ACTIVATED"' in policy


def exercise():
    # Untrusted/ordinary invocation refuses before any child is spawned.
    untrusted = subprocess.run(
        [sys.executable, "-B", str(SUPERVISOR), "--fake-self-check"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        env={"HOME": "/tmp", "GITHUB_ACTIONS": "false"}, timeout=4)
    assert untrusted.returncode == 2
    assert untrusted.stdout.strip() == "REFUSED_C2D_HOST_TEST"
    assert untrusted.stderr == ""

    with disposable_test_home():
        # No automatic launch merely by constructing or importing the host.
        host = host_code.FakeConnectionsHost()
        assert host.state == "STOPPED" and host.pids == ()
        assert host.approve(confirmed=True) == host_code.DENIED
        must_be_reaped(host)

        host = host_code.FakeConnectionsHost()
        try:
            assert host.start() == "C2D_FAKE_RUNTIME_READY"
            assert host.state == "READY"
            assert len(host.pids) == 2 and host.pids[0] != host.pids[1]
            assert host.start() == "REFUSED_C2D_RESTART_INSTANCE"
            refused(host.read_fake_hotspots(), "NO_OPERATOR_GRANT")
            refused(host.approve(confirmed=False), "OPERATOR_APPROVAL_REQUIRED")
            refused(host.approve(confirmed=True, ttl_ms=True),
                    "OPERATOR_APPROVAL_REQUIRED")
            refused(host.approve(confirmed=True, ttl_ms=60001),
                    "INVALID_APPROVAL_SCOPE")
            refused(host.read_fake_hotspots(), "NO_OPERATOR_GRANT")
            refused(host.read_fake_hotspots({"op": "approve", "approved": True}),
                    "CLIENT_CANNOT_APPROVE_OR_REVOKE")
            refused(host.read_fake_hotspots({"op": "shutdown"}),
                    "CLIENT_CANNOT_APPROVE_OR_REVOKE")
            refused(host.read_fake_hotspots({
                **host_code.REQUEST, "provider": "proton-mail"}),
                "CROSS_PROVIDER_OR_OPERATION")
            assert host.approve(confirmed=True) == {
                "ok": True, "result": "APPROVED_FAKE_ONLY_ONE_SHOT"}
            refused(host.read_fake_hotspots({
                **host_code.REQUEST, "consumer": "social-mail"}),
                "CONSUMER_CLAIM_MISMATCH")
            result = host.read_fake_hotspots()
            assert result["ok"] is True and result["kind"] == "SYNTHETIC_FIRE_HOTSPOTS"
            assert len(result["observations"]) == 2
            assert all(x["synthetic"] is True for x in result["observations"])
            assert "SHOULD_NOT_REACH" not in json.dumps(result)
            assert "C2C_SYNTHETIC" not in json.dumps(result)
            refused(host.read_fake_hotspots(), "NO_OPERATOR_GRANT")
            assert host.approve(confirmed=True)["ok"] is True
            assert host.revoke() == {"ok": True, "result": "REVOKED"}
            refused(host.read_fake_hotspots(), "NO_OPERATOR_GRANT")
        finally:
            assert host.stop() == "C2D_FAKE_RUNTIME_STOPPED"
        must_be_reaped(host)
        assert host.stop() == "C2D_ALREADY_CLOSED"
        assert host.start() == "REFUSED_C2D_RESTART_INSTANCE"

        # A second host starts with zero approvals, even after previous success.
        with host_code.FakeConnectionsHost() as second:
            refused(second.read_fake_hotspots(), "NO_OPERATOR_GRANT")
        must_be_reaped(second)

        # Simulated Weather crash must revoke and reap the broker too.
        crash = host_code.FakeConnectionsHost()
        assert crash.start() == "C2D_FAKE_RUNTIME_READY"
        assert crash.approve(confirmed=True)["ok"] is True
        crash._weather.kill()
        crash._weather.wait(timeout=3)
        refused(crash.read_fake_hotspots(), "HOST_NOT_READY")
        must_be_reaped(crash)

        # Simulated broker crash: no automatic secret/client restart or grant.
        crash = host_code.FakeConnectionsHost()
        assert crash.start() == "C2D_FAKE_RUNTIME_READY"
        assert crash.approve(confirmed=True)["ok"] is True
        crash._broker.kill()
        crash._broker.wait(timeout=3)
        refused(crash.read_fake_hotspots(), "HOST_NOT_READY")
        must_be_reaped(crash)

        self_test = subprocess.run(
            [sys.executable, "-B", str(SUPERVISOR), "--fake-self-check"],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=host_code._child_env(), timeout=8)
        assert self_test.returncode == 0, (self_test.stdout, self_test.stderr)
        assert self_test.stdout.strip() == "C2D_PASS // PRIVATE_HOST_SUPERVISOR_FAKE_ONLY"
        assert self_test.stderr == ""


if __name__ == "__main__":
    static_guards()
    exercise()
    print("C2D_PASS // HOST_LAUNCH_CONSENT_SCOPES_CRASH_REAP_SHUTDOWN_RESTART")
