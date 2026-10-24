#!/usr/bin/env python3
"""M1o: UI cannot grant an approval or dispatch/undo a move."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
qml = (root / "widgets/TimeW.qml").read_text()
bridge = (root / "services/time/MachineMoveReviewRead.py").read_text()
for term in (
    'label: "REVIEW MOVE"',
    'label: "CHECK INTERRUPTS"',
    'onLeftClicked: timew.machineReviewActionCandidate()',
    'onLeftClicked: timew.machineCheckInterruptedMoves()',
    "function machineReviewActionCandidate()",
    "function machineCheckInterruptedMoves()",
    "function machineInvalidateMoveReview()",
    "machineMoveCandidateKey",
    "machineMoveReviewKey === timew.machineMoveCandidateKey",
    "timew.machineResolverItem.status === \"candidate\"",
    'id: machineMoveReviewProcess',
    'Quickshell.shellPath("services/time/MachineMoveReviewRead.py")',
    '"preview"',
    '"pending"',
    'data.kind === "machine-m1o-action-review"' if False else 'result.kind === "machine-m1o-action-review"',
    'result.approval_issued === false',
    'result.executable === false',
    'result.read_only === true',
    'MOVE REVIEWED // NO APPROVAL',
    'NO UNRESOLVED MOVE OPERATIONS',
    'PENDING // NO AUTOMATIC RETRY OR UNDO',
    'machineStepPendingMove(-1)',
    'machineStepPendingMove(1)',
    'NO SCREENSHOTS OR RESTORATION ACTIVE',
):
    assert term in qml, term
for term in (
    'def review_candidate(payload, *, read_runner):',
    'def review_interruptions(*, journal, read_runner):',
    'args[0] not in ("preview", "pending")',
    '"approval_issued": False',
    '"executable": False',
    '"read_only": True',
    "MoveApprovalGate()",
    "gate.review(",
    "inspect_pending(",
    "MAX_REQUEST_BYTES = 262144",
):
    assert term in bridge, term
for forbidden in (
    "gate.approve(", "gate.consume(", "execute_one(", "journal.begin(",
    "journal.finish(", "journal.mark_dispatching(", "swaymsg -t command",
    "subprocess.Popen(", "subprocess.run([", "os.system(", "os.unlink(",
):
    assert forbidden not in bridge, forbidden
for forbidden in (
    "MachineWindowMovePilot.py",
    "MachineMoveApproval.py",
    "machineApplyMove(",
    "machineExecuteMove(",
    "approval_token:",
):
    assert forbidden not in qml, forbidden
assert qml.count("Process {") == 11
print("TIMEW MACHINE M1O: READ-ONLY UI / NO-APPLY CONTRACT PASS")
