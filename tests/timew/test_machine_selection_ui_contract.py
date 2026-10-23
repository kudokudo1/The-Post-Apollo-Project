#!/usr/bin/env python3
"""MACHINE selection remains in-memory and does not change Sway or disk."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
qml = (root / "widgets/TimeW.qml").read_text(encoding="utf-8")
for term in (
    'property var machineExcludedItems: ({})',
    'function machineSelectionKey(kind, index)',
    'function machineItemIncluded(kind, index)',
    'function toggleMachineItemSelection()',
    'function machineIncludedCount(kind)',
    'function machineSelectionPreview()',
    'machineExcludedItems = ({});',
    'kind: "sway-layout-selection-preview"',
    'label: "EXCLUDE ITEM" : "INCLUDE ITEM"',
    'onLeftClicked: timew.toggleMachineItemSelection()',
    'SELECTION PREVIEW ONLY // NOTHING SAVED',
    'onLeftClicked: timew.requestMachineCapturePreview()',
    'id: machineMarkerList'
):
    assert term in qml, term
assert 'FileView {' not in qml
assert 'JsonAdapter {' not in qml
assert 'function restoreDesktop(' not in qml
assert 'function captureDesktopCheckpoint(' not in qml
print("TIMEW MACHINE M1E: SELECTION SOURCE CONTRACT PASS")
