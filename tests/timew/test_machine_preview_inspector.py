#!/usr/bin/env python3
"""MACHINE preview inspector must not introduce writes or automatic capture."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
window = (root / "widgets/TimeW.qml").read_text(encoding="utf-8")
assert 'property string machineInspectKind: "outputs"' in window
assert 'property int machineInspectIndex: 0' in window
assert 'function selectMachineInspectKind(kind)' in window
assert 'function stepMachineInspect(delta)' in window
for kind in ('"outputs"', '"workspaces"', '"windows"'):
    assert kind in window
assert 'timew.machineInspectItem.app_id' in window
assert 'timew.machineInspectItem.connector' in window
assert 'timew.machineInspectItem.output' in window
assert 'machineInspectIndex = 0;' in window
assert 'onLeftClicked: timew.requestMachineCapturePreview()' in window
assert 'onLeftClicked: timew.stepMachineInspect(-1)' in window
assert 'onLeftClicked: timew.stepMachineInspect(1)' in window
assert 'id: machineMarkerList' in window
assert '"NO SCREENSHOTS OR RESTORATION ACTIVE"' in window
assert 'function restoreDesktop(' not in window
assert 'FileView {' not in window
assert 'JsonAdapter {' not in window
print("TIMEW MACHINE INSPECTOR: SOURCE CONTRACT PASS")
