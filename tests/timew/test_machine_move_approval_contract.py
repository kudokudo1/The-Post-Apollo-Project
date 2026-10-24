#!/usr/bin/env python3
"""M1n isolation guard: review and reconciliation cannot move windows."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
approval = (root / "services/time/MachineMoveApproval.py").read_text()
reconcile = (root / "services/time/MachineMoveReconciliation.py").read_text()
pilot = (root / "services/time/MachineWindowMovePilot.py").read_text()
qml = (root / "widgets/TimeW.qml").read_text()
for term in (
    "class MoveApprovalGate:",
    "def review(self, saved_document, request, *, checkpoint_id, read_runner):",
    "def approve(self, *, review_id, checkpoint_id, saved_document,",
    "def consume(self, *, approval_token, checkpoint_id, saved_document, request):",
    "APPROVAL_TTL_SECONDS = 90",
    "self._ticket = None",
    "hmac.compare_digest(",
):
    assert term in approval, term
for term in (
    "def inspect_pending(journal, *, read_runner):",
    "pending = journal.pending()",
    '"automatic_retry_allowed": False',
    '"automatic_undo_allowed": False',
    '"requires_manual_review": True',
    '"evidence_is_not_process_identity": True',
):
    assert term in reconcile, term
for term in (
    "journal, approval_gate, approval_token, checkpoint_id):",
    'if not isinstance(approval_gate, MoveApprovalGate):',
    'approval_gate.consume(',
    'operation_id = journal.begin(report["before"])',
    'journal.mark_dispatching(operation_id)',
):
    assert term in pilot, term
assert pilot.index('approval_gate.consume(') < pilot.index('operation_id = journal.begin(')
for forbidden in (
    "if __name__", "subprocess.run(", "subprocess.Popen(",
    "swaymsg -", "Quickshell", "os.system(", "sqlite3",
):
    assert forbidden not in approval, forbidden
    assert forbidden not in reconcile, forbidden
for forbidden in ("MachineMoveApproval.py", "MachineMoveReconciliation.py",
                  "MachineWindowMovePilot.py", "machineApplyMove("):
    assert forbidden not in qml, forbidden
print("TIMEW MACHINE M1N: ISOLATED APPROVAL AND RECONCILIATION CONTRACT PASS")
