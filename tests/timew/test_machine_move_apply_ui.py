#!/usr/bin/env python3
"""M1r: one explicit restore action, without converting M1o/M1p into executors."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
qml = (root / "widgets/TimeW.qml").read_text(encoding="utf-8")
bridge = (root / "services/time/MachineMoveApply.py").read_text(encoding="utf-8")
review = (root / "services/time/MachineMoveReviewRead.py").read_text(encoding="utf-8")
confirm = (root / "services/time/MachineMoveConfirmRead.py").read_text(encoding="utf-8")

required_ui = (
    'id: machineStoredViewport',
    'id: machineStoredScroll',
    'contentHeight: machineStoredPane.height',
    'id: machineStoredRail',
    'flickable: machineStoredScroll',
    'geometryMode: "viewport"',
    'label: "RESTORE ONE WINDOW"',
    "onLeftClicked: timew.machineRestoreOneWindow()",
    "function machineRestoreOneWindow()",
    'selectedMode !== "machine"',
    "!machineStoredViewOpen",
    "machineApplyBusy || machineConfirmationBusy",
    "machineConfirmationTyped !== machineConfirmationPhrase",
    'machineResolverItem.status !== "candidate"',
    "machineOpenedCheckpoint.checkpoint.id !== machineSavedItem.id",
    "machineApplyKey = machineMoveCandidateKey",
    "machineApplySubmittedText = machineConfirmationTyped",
    "machineApplyPayload = JSON.stringify({",
    "checkpoint_id: machineSavedItem.id",
    "document: machineOpenedCheckpoint.document",
    "candidate: machineResolverItem",
    "confirmation_text: machineConfirmationTyped",
    'Quickshell.shellPath("services/time/MachineMoveApply.py")',
    '"apply-one"',
    "id: machineApplyOneProcess",
    "stdinEnabled: true",
    "result.kind === \"machine-m1q-single-window-result\"",
    'result.status === "verified_moved"',
    'result.status === "uncertain_requires_manual_review"',
    "result.no_automatic_retry === true",
    "result.no_automatic_undo === true",
    "timew.machineInvalidateResolver();",
    "ONE WINDOW MOVED // RE-RESOLVE TO CONTINUE",
    "MOVE UNCERTAIN // CHECK INTERRUPTS",
    'label: "VALIDATE ONLY"',
    "onLeftClicked: timew.machineConfirmPreviewOnly()",
    'label: "RESTORE PREVIEW"',
    "onLeftClicked: timew.machinePreviewRestorePlan()",
)
for key in required_ui:
    assert key in qml, key

assert qml.count("Process {") == 14
assert qml.count('Quickshell.shellPath("services/time/MachineMoveApply.py")') == 1
assert qml.count("onLeftClicked: timew.machineRestoreOneWindow()") == 1
assert 'onMenuOpenChanged: timew.machineRestoreOneWindow' not in qml
assert "machineRestoreOneWindow()" not in qml[:qml.index('function machineRestoreOneWindow()')]
assert "NO SCREENSHOTS OR AUTOMATIC RESTORATION" in qml

start = qml.index("function machineRestoreOneWindow()")
end = qml.index("function machineInvalidateMoveReview()", start)
action = qml[start:end]
assert "machineApplyOneProcess.exec(" in action
assert "swaymsg" not in action
assert "MachineWindowMovePilot" not in action
assert "MachineMoveApproval" not in action
assert "machineStorePayload" not in action
assert "machineApplyResult = null;" in action
assert 'selectedMode !== "machine"' in action

for key in (
    "checkpoint_loader(checkpoint_id)",
    'validate(payload["document"]) != stored.get("document")',
    "gate.review(document, request, checkpoint_id=checkpoint_id",
    'confirmation != review["confirmation_text"]',
    "grant = gate.approve(",
    "result = execute_one(",
    "journal_factory(suggested_path())",
    'args != ["apply-one"]',
):
    assert key in bridge, key

# Existing read-only reviewer/rehearsal must not acquire a command path.
for pure in (review, confirm):
    for forbidden in ("execute_one(", "gate.approve(", "gate.consume(",
                      "journal.begin(", "journal.mark_dispatching(",
                      "swaymsg -t command"):
        assert forbidden not in pure, forbidden

assert qml.count("machineApplyOneProcess.exec(") == 1
print("MACHINE M1r: EXPLICIT ONE-WINDOW UI / READ-ONLY BOUNDARY PASS")
