#!/usr/bin/env python3
"""C2h producer tests: real C2f subprocess statuses, no production rights."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
PRODUCER = ROOT / "tests/connections/fixtures/C2hStatusProducer.py"
SCENE = ROOT / "tests/connections/fixtures/C2hNativeStatusScene.qml"
RUNNER = ROOT / "tests/connections/fixtures/C2hNativeStatusRunner.sh"
BRIDGE = ROOT / "services/connections/ConnectionsRequestStatus.qml"
BROKER = ROOT / "services/connections/ConnectionsBroker.qml"

EXPECTED = [
    ("PENDING", "AWAITING_SIMULATED_REVIEW"),
    ("APPROVED", "SIMULATED_HOST_APPROVED"),
    ("COMPLETED", "SYNTHETIC_OPERATION_COMPLETE"),
    ("PENDING", "AWAITING_SIMULATED_REVIEW"),
    ("DENIED", "OPERATOR_DENIED"),
    ("PENDING", "AWAITING_SIMULATED_REVIEW"),
    ("CANCELLED", "HOST_CANCELLED"),
    ("PENDING", "AWAITING_SIMULATED_REVIEW"),
    ("EXPIRED", "REQUEST_EXPIRED"),
    ("PENDING", "AWAITING_SIMULATED_REVIEW"),
    ("APPROVED", "SIMULATED_HOST_APPROVED"),
    ("FAILED", "HOST_DISCONNECTED"),
]
FIELDS = {
    "ok", "requestId", "state", "provider", "consumer", "operation",
    "profile", "reason", "expiresInMs", "credentialPresent",
    "realGrantActive", "canApproveInProduction", "simulated",
}


def invoke(env: dict[str, str], mode: str = "--c2h-fake-stream"):
    return subprocess.run(
        [sys.executable, "-B", str(PRODUCER), mode],
        env=env, capture_output=True, text=True, timeout=16,
    )


def main():
    no_guard = invoke({"HOME": "/tmp", "GITHUB_ACTIONS": "false"})
    assert no_guard.returncode == 2
    assert no_guard.stdout == ""
    assert no_guard.stderr.strip() == "C2H_REFUSED_NOT_PRIVATE"
    bad_mode = invoke({"HOME": "/tmp"}, "--real-provider")
    assert bad_mode.returncode == 2 and bad_mode.stdout == ""
    assert bad_mode.stderr.strip() == "C2H_REFUSED_MODE"

    with tempfile.TemporaryDirectory(prefix="postapollo-c2c-ci-", dir="/tmp") as temp:
        root = Path(temp)
        home = root / "home"
        home.mkdir(mode=0o700)
        marker = root / ".ci-only-authority"
        marker.write_text("C2C_PRIVATE_SOCKETPAIR_ONLY\n", encoding="utf8")
        marker.chmod(0o600)
        env = {
            "PATH": os.environ["PATH"],
            "HOME": str(home),
            "GITHUB_ACTIONS": "true",
            "POST_APOLLO_C2C_FAKE_ONLY": "1",
            "LANG": "C.UTF-8",
        }
        run = invoke(env)
        assert run.returncode == 0, (run.returncode, run.stderr)
        assert run.stderr == ""
        lines = run.stdout.splitlines()
        assert len(lines) == len(EXPECTED), "C2H_STATUS_SEQUENCE_LENGTH"
        records = [json.loads(line) for line in lines]
        ids: list[str] = []
        for record, (state, reason) in zip(records, EXPECTED):
            assert set(record) == FIELDS, "C2H_STATUS_KEYS"
            assert record["ok"] is True
            assert record["simulated"] is True
            assert record["credentialPresent"] is False
            assert record["realGrantActive"] is False
            assert record["canApproveInProduction"] is False
            assert record["provider"] == "nasa-firms"
            assert record["consumer"] == "weather-earth"
            assert record["operation"] == "fires.hotspots.read"
            assert record["profile"] == "ci-only-profile"
            assert record["state"] == state
            assert record["reason"] == reason
            assert re.fullmatch(r"[0-9a-f]{32}", record["requestId"])
            assert isinstance(record["expiresInMs"], int)
            assert 0 <= record["expiresInMs"] <= 60000
            if state not in ("PENDING", "APPROVED"):
                assert record["expiresInMs"] == 0
            ids.append(record["requestId"])
        # Each independent request gets a new ID; phases share their ID.
        assert ids[0] == ids[1] == ids[2]
        assert ids[3] == ids[4]
        assert ids[5] == ids[6]
        assert ids[7] == ids[8]
        assert ids[9] == ids[10] == ids[11]
        assert len({ids[0], ids[3], ids[5], ids[7], ids[9]}) == 5
        assert "C2C_SYNTHETIC_NEVER_A_REAL_CREDENTIAL_" not in run.stdout
        assert "FAKE_LEAK_CANARY" not in run.stdout
        assert sorted(f.name for f in root.iterdir()) == [".ci-only-authority", "home"]
        assert not any(home.iterdir()), "C2H_FAKE_HOST_WROTE_HOME"

    scene = SCENE.read_text()
    source = PRODUCER.read_text()
    runner = RUNNER.read_text()
    singleton = BRIDGE.read_text()
    broker = BROKER.read_text()
    assert 'readonly property bool hostConnected: false' in singleton
    assert 'readonly property bool hostAuthenticated: false' in singleton
    assert 'readonly property bool credentialActionsEnabled: false' in broker
    assert 'stdout: SplitParser {' in scene
    assert 'Quickshell.shellPath(' in scene
    assert 'C2hStatusProducer.py' in scene
    assert 'details.syntheticStatusPreview = record' in scene
    assert 'details.syntheticStatusPreview = null' in scene
    assert "HOST NOT CONNECTED" in scene
    assert "C2H_NATIVE_STREAM_PASS // REAL_QML_FAKE_HOST_NO_GRANT" in scene
    assert 'POST_APOLLO_C2C_FAKE_ONLY=1' in runner
    assert 'env -i PATH="$PATH"' in runner
    assert 'C2H_PASS // NATIVE_QML_REAL_FAKE_HOST_STREAM_OFFLINE_NO_CREDENTIALS' in runner
    assert 'FakeRequestLifecycle(clock=clock)' in source
    for forbidden in (
        "secret-tool", "org.freedesktop.secrets", "requests.get",
        "urllib.request", "https://", "http://", "socket.bind",
        "POST_APOLLO_FIRMS_MAP_KEY",
    ):
        assert forbidden not in source, forbidden
    print("C2H_PASS // REAL_FAKE_HOST_BOUNDED_JSON_FRAMES_AND_DISABLED_PRODUCTION")


if __name__ == "__main__":
    main()
