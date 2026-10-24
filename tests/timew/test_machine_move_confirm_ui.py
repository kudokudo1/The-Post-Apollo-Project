#!/usr/bin/env python3
"""M1p invariant: a typed review never becomes a live action or durable grant."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
qml = (root / "widgets/TimeW.qml").read_text()
adapter = (root / "services/time/MachineMoveConfirmRead.py").read_text()

for snippet in (
    "function machineConfirmPreviewOnly()",
    "function machineInvalidateConfirmation()",
    "machineConfirmationTyped",
    "machineConfirmationPhrase",
    "machineMoveReviewKey === machineMoveCandidateKey",
    "machineConfirmationTyped !== machineConfirmationPhrase",
    'Quickshell.shellPath("services/time/MachineMoveConfirmRead.py")',
    '"confirm-preview"',
    "id: machineConfirmPreviewProcess",
    'label: "VALIDATE ONLY"',
    'TYPE EXACT PHRASE // DRY RUN ONLY',
    'PHRASE VALIDATED // NO APPROVAL OR MOVE',
    'result.kind === "machine-m1p-confirmation-dry-run"',
    "result.approval_issued === false",
    "result.executable === false",
    "result.read_only === true",
    "result.confirmation_persisted === false",
    "result.requires_new_approval_to_execute === true",
    'NO SCREENSHOTS OR RESTORATION ACTIVE',
):
    assert snippet in qml, snippet
for snippet in (
    "def confirm_preview(payload, *, read_runner):",
    "def required_phrase(action):",
    'sys.argv[1:] != ["confirm-preview"]',
    "review_candidate(proposed, read_runner=read_runner)",
    "if entered != phrase:",
    '"approval_issued": False',
    '"confirmation_persisted": False',
    '"executable": False',
    '"requires_new_approval_to_execute": True',
    "MAX_CONFIRMATION_LENGTH = 256",
):
    assert snippet in adapter, snippet
for forbidden in (
    "gate.approve(", "gate.consume(", "execute_one(",
    "journal.begin(", "journal.finish(", "journal.mark_dispatching(",
    "swaymsg -t command", "subprocess.Popen(",
    "os.system(", "os.unlink(",
):
    assert forbidden not in adapter, forbidden
for forbidden in ("MachineWindowMovePilot.py", "MachineMoveApproval.py",
                  "machineExecuteMove(", "onLeftClicked: timew.apply"):
    assert forbidden not in qml, forbidden
assert qml.count("Process {") == 12
print("MACHINE M1P: NO-APPLY CONFIRMATION UI CONTRACT PASS")
