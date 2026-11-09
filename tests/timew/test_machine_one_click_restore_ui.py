#!/usr/bin/env python3
"""MACHINE UX source contract: never expose backend preflight as a requirement."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
qml = (root / "widgets/TimeW.qml").read_text(encoding="utf-8")
backend = (root / "services/time/MachineRestoreCheckpoint.py").read_text(encoding="utf-8")

for fragment in (
    'label: "RESTORE DESKTOP"',
    "onLeftClicked: timew.machineRestoreSelectedCheckpoint()",
    "function machineRestoreSelectedCheckpoint()",
    'id: machineAutoRestoreProcess',
    'Quickshell.shellPath("services/time/MachineRestoreCheckpoint.py")',
    '"restore", machineAutoRestoreKey',
    'property bool machineAdvancedOpen: false',
    'visible: timew.machineAdvancedOpen',
    'label: timew.machineAdvancedOpen ? "HIDE DETAILS" : "DETAILS"',
    'machineAutoRestoreStatus',
):
    assert fragment in qml, fragment

assert qml.count('onLeftClicked: timew.machineRestoreSelectedCheckpoint()') == 1
assert qml.count('id: machineAutoRestoreProcess') == 1
assert qml.count('Process {') == 14
assert 'onMenuOpenChanged: timew.machineRestoreSelectedCheckpoint()' not in qml
assert 'Component.onCompleted: timew.machineRestoreSelectedCheckpoint()' not in qml
assert 'Timer' not in qml[qml.index('function machineRestoreSelectedCheckpoint()'):
                          qml.index('function machineInvalidateMoveReview()', qml.index('function machineRestoreSelectedCheckpoint()'))]
assert 'shell=False' in backend
assert 'gtk-launch' in backend
assert 'MoveApprovalGate().review' in backend
assert 'apply_one' in backend
assert 'journal_factory(suggested_path()).pending()' in backend
assert 'MAX_APPS = 40' in backend
assert 'MAX_LAUNCHES = 12' in backend
assert 'no_automatic_retry' in backend
assert 'subprocess.Popen(' not in backend

print("MACHINE ONE CLICK // OPTIONAL DETAILS UI PASS")
