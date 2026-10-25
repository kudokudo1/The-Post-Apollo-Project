#!/usr/bin/env python3
"""M2d fixture-only correlation: never connect to live hosts or app processes."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
pilot = (root / "services/time/MachineAdapterFixtureCorrelation.py").read_text()
qml = (root / "widgets/TimeW.qml").read_text()
store = (root / "services/time/MachineCheckpointStore.py").read_text()
plan = (root / "docs/timew-machine-m2d-fixture-session-correlation.md").read_text()

for required in (
    "def inspect_fixture_correlations(saved_sidecar, host_frame, app_frame,",
    "validate_sidecar(saved_sidecar",
    "find_declared_adapter(registry, adapter, app_id)",
    'kind="synthetic-host-window-observations"',
    'kind="synthetic-app-session-observations"',
    '"input_provenance": "synthetic_untrusted"',
    '"live_identity_verified": False',
    '"exact_session_match": False',
    '"capture_enabled": False',
    '"launch_enabled": False',
    '"restore_enabled": False',
    '"safe_actions": []',
    "DUPLICATE HOST OBSERVATION",
    "DUPLICATE SESSION REFERENCE",
    "CROSS-APPLICATION CORRELATION",
    "MISMATCHED OBSERVATION SCOPE",
):
    assert required in pilot, required
for forbidden in (
    "subprocess", "swaymsg", "os.system(", "os.spawn",
    "Popen(", "importlib", "socket", "webbrowser",
    "os.unlink", "sqlite3", "open(", "write(",
    "exec(", "eval(", "requests",
    "MachineMoveApproval", "MachineWindowMovePilot",
):
    assert forbidden not in pilot, forbidden
assert "MachineAdapterFixtureCorrelation.py" not in qml
assert "SCHEMA_VERSION = 1" in store
assert 'load_parser = choices.add_parser("load")' in store
for required in ("REVIVE", "RESTORE", "23", "Kitty",
                 "Firefox", "VS Code", "synthetic", "M2d",
                 "nothing on the operator", "scope", "privacy"):
    assert required.lower() in plan.lower(), required
print("MACHINE M2D: FIXTURE-ONLY CORRELATION CONTRACT / NO LIVE APP CONTROL PASS")
