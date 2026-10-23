#!/usr/bin/env python3
"""MACHINE M1c: capture only on click, in memory, no mutation or persistence."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
qml = (root / "widgets/TimeW.qml").read_text()
adapter = (root / "services/time/MachineSwayRead.py").read_text()

assert 'function requestMachineCapturePreview()' in qml
assert 'if (!menuOpen || selectedMode !== "machine" || machineCaptureBusy)' in qml
assert 'onLeftClicked: timew.requestMachineCapturePreview()' in qml
assert 'id: machineCaptureProcess' in qml
assert 'running: false' in qml.split('id: machineCaptureProcess', 1)[1].split('}', 1)[0]
assert 'Quickshell.shellPath("services/time/MachineSwayRead.py")' in qml
assert '"python3", "-B", "-I"' in qml
assert 'data.preview_only === true' in qml
assert 'data.kind === "sway-layout-metadata-preview"' in qml
assert 'machineCapturePreview = null' in qml
assert 'CAPTURE UNAVAILABLE' in qml
assert 'machineCaptureBusy = false' in qml
assert 'machineCapturePreview.outputs' in qml
assert 'machineCapturePreview.workspaces' in qml
assert 'machineCapturePreview.windows' in qml
assert 'function restoreDesktop(' not in qml
assert 'function captureDesktopCheckpoint(' not in qml
assert 'JsonAdapter {' not in qml and 'FileView {' not in qml
assert 'swaymsg' not in qml and 'execDetached(' not in qml
for command in ("get_outputs", "get_workspaces", "get_tree"):
    assert command in adapter
print("TIMEW MACHINE M1C: SOURCE CONTRACT PASS / CLICK-ONLY READ")
