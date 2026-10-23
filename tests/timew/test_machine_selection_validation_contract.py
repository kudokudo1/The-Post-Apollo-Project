#!/usr/bin/env python3
"""M1f source contract: selection validation is read-only and fail closed."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
qml = (root / "widgets/TimeW.qml").read_text(encoding="utf-8")
policy = (root / "services/time/MachineSelectionPolicy.js").read_text(encoding="utf-8")
for term in (
    'import "../services/time/MachineSelectionPolicy.js" as MachineSelectionPolicy',
    "MachineSelectionPolicy.validate(machineCapturePreview, machineExcludedItems)",
    'function machineLocateSelectionIssue()',
    'onLeftClicked: timew.machineLocateSelectionIssue()',
    'machineSelectionValidation.status !== "ready"',
    '"SELECTION CONSISTENT // NOT SAVED"',
    '"BLOCKED // INVALID PREVIEW"',
    'label: "LOCATE"',
    'SELECTION PREVIEW ONLY // NOTHING SAVED',
    'onLeftClicked: timew.toggleMachineItemSelection()',
    'onLeftClicked: timew.requestMachineCapturePreview()',
    'id: machineMarkerList',
):
    assert term in qml, term
assert 'function validate(preview, excluded)' in policy
assert 'workspace_excluded' in policy and 'output_excluded' in policy
assert 'duplicate_output' in policy and 'duplicate_workspace' in policy
for forbidden in ('swaymsg', 'subprocess', 'FileView {', 'JsonAdapter {'):
    assert forbidden not in policy, forbidden
assert 'FileView {' not in qml and 'JsonAdapter {' not in qml
assert 'function restoreDesktop(' not in qml
print("TIMEW MACHINE M1F: SOURCE VALIDATION CONTRACT PASS")
