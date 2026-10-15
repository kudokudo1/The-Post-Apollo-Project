#!/usr/bin/env python3
"""Source-only contract: opt-in Syntagma UI lag probe must be harmless by default.

A source check is NOT a Qt/Sway runtime test or a profiling measurement.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
shell = (root / "shell.qml").read_text(encoding="utf-8")
git = (root / "widgets/GitW.qml").read_text(encoding="utf-8")
hospital = (root / "widgets/HospitalW.qml").read_text(encoding="utf-8")

# No probe work is scheduled unless the operator opts in at process launch.
assert 'Quickshell.env("POST_APOLLO_UI_LAG_PROBE")' in shell
assert 'trim() === "1"' in shell
assert "running: shellRoot.syntagmaLagProbeEnabled" in shell
assert "interval: 100" in shell
assert "if (elapsed >= 350)" in shell
assert "SYNTAGMA_LAG_PROBE // event-loop interval" in shell

# Hospital mode correlation is enabled only by the same existing env opt-in.
# It observes the already-emitted signal on the shell instance, not Hospital
# services. Mode names are static UI categories, never Room or Patient data.
assert 'property double syntagmaHospitalLastModeChangeMs: 0' in shell
assert 'if (shellRoot.syntagmaLagProbeEnabled) {' in shell
assert 'onOperationsSurfaceChanged: {' in shell
assert '"SYNTAGMA_LAG_PROBE // hospital mode-change"' in shell
assert 'hospitalModeAgeMs=' in shell
assert 'hospitalMode=' in shell
assert 'tsMs=' in shell
assert 'shellRoot.syntagmaHospitalLastModeChangeMs = now;' in shell
assert shell.count("hospitalWindow.toggle();") == 2
assert shell.count("gitWindow.toggle();") == 2

# The synchronous duration wraps each *existing* dock toggle. Nothing changes
# about which QML handler is invoked or what data the widgets refresh.
# Both original toggle sites remain: IPC and dock. Only dock is timed.
assert shell.count("hospitalWindow.toggle();") == 2
assert shell.count("gitWindow.toggle();") == 2
assert 'reportSyntagmaToggleTime(\n                        "hospital"' in shell
assert 'reportSyntagmaToggleTime(\n                        "git"' in shell

# Known crash avoidance (PR #243) and focus ownership remain untouched.
for src in (git, hospital):
    assert "visible: true" in src
    assert "visibilityLifecyclePilot" not in src
    assert "keyboardOwnershipRequested()" in src

print("SYNTAGMA UI LAG PROBE // SOURCE GUARDS PASS; RUNTIME UNTESTED")
