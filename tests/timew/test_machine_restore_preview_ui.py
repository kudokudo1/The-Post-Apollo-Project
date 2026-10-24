#!/usr/bin/env python3
"""M1i restore-planning contract. No Sway mutation, persistence or launches."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
qml = (root / "widgets/TimeW.qml").read_text(encoding="utf-8")
policy = (root / "services/time/MachineRestorePreviewPolicy.js").read_text(encoding="utf-8")
checks = (
    'import "../services/time/MachineRestorePreviewPolicy.js" as MachineRestorePreviewPolicy',
    "function machinePreviewRestorePlan()",
    "function machineStepRestorePlanItem(delta)",
    "MachineRestorePreviewPolicy.plan(",
    "machineOpenedCheckpoint.document, machineCapturePreview",
    "machineOpenedCheckpoint.checkpoint.id !== machineSavedItem.id",
    "machineRestorePlan = null;",
    'label: "RESTORE PREVIEW"',
    'onLeftClicked: timew.machinePreviewRestorePlan()',
    'onLeftClicked: timew.machineStepRestorePlanItem(-1)',
    'onLeftClicked: timew.machineStepRestorePlanItem(1)',
    'RESTORE PLAN UNAVAILABLE // INVALID DATA',
    'SHOWING FIRST 40 RESTORE REVIEW ITEMS',
    'PLAN ONLY // NO ACTIONS OR RESTARTS',
    'NO SCREENSHOTS OR RESTORATION ACTIVE',
    'label: "COMPARE TO CAPTURE"',
    'onLeftClicked: timew.machineCompareSavedToCapture()',
    'label: "OPEN SAVED METADATA"',
)
for term in checks:
    assert term in qml, term
for term in (
    '.import "MachineLayoutDiffPolicy.js" as Diff',
    "function plan(saved, current)",
    "preview_only: true",
    "executable: false",
    "possible_window_reuse",
    "window_not_observed",
    "duplicate_window_candidates",
    "workspace_output_missing",
    "geometry_review",
    "var MAX_PLAN_ITEMS = 40;",
):
    assert term in policy, term
for forbidden in (
    "swaymsg", "execDetached", "Process {", "FileView {",
    "subprocess", "os.system", "hospital.db", "machine.db",
):
    assert forbidden not in policy, forbidden
for forbidden in (
    'function restoreDesktop(', 'function applySavedCheckpoint(',
    'onLeftClicked: timew.applyRestorePlan(',
):
    assert forbidden not in qml
print("TIMEW MACHINE M1I: READ-ONLY RESTORE PREVIEW UI CONTRACT PASS")
