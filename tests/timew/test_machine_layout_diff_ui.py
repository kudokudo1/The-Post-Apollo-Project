#!/usr/bin/env python3
"""MACHINE read-only comparison is explicit and cannot mutate the desktop."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
qml = (root / "widgets/TimeW.qml").read_text(encoding="utf-8")
policy = (root / "services/time/MachineLayoutDiffPolicy.js").read_text(encoding="utf-8")
for term in (
    'import "../services/time/MachineLayoutDiffPolicy.js" as MachineLayoutDiffPolicy',
    "property var machineLayoutComparison: null",
    "function machineCompareSavedToCapture()",
    "function machineStepLayoutDifference(delta)",
    "MachineLayoutDiffPolicy.compare(",
    "machineOpenedCheckpoint.document, machineCapturePreview",
    "machineOpenedCheckpoint.checkpoint.id !== machineSavedItem.id",
    'machineLayoutComparison = null;',
    'onLeftClicked: timew.machineCompareSavedToCapture()',
    'label: "COMPARE TO CAPTURE"',
    'CAPTURE CURRENT FIRST',
    'OPEN SAVED FIRST',
    'MATCHES CURRENT CAPTURE // NO CHANGES',
    'COMPARE UNAVAILABLE // INVALID METADATA',
    'SHOWING FIRST 40 DIFFERENCES',
    'onLeftClicked: timew.machineStepLayoutDifference(-1)',
    'onLeftClicked: timew.machineStepLayoutDifference(1)',
    "OPEN SAVED METADATA",
    "SAVE CHECKPOINT",
    "NO SCREENSHOTS OR RESTORATION ACTIVE"
):
    assert term in qml, term
for term in (
    "function compare(saved, current)",
    'sway-layout-selection-preview',
    'sway-layout-metadata-preview',
    "function windowCounts(windows)",
    "function maps(doc)",
    "var MAX_DELTAS = 40;",
):
    assert term in policy, term
assert "Process {" not in policy
assert "FileView {" not in policy
assert "swaymsg" not in policy
assert "execDetached(" not in policy
assert "function restoreDesktop(" not in qml
assert "function applySavedCheckpoint(" not in qml
print("TIMEW MACHINE M1H: READ-ONLY DIFF SOURCE CONTRACT PASS")
