#!/usr/bin/env python3
"""M1k guard: isolated injected test pilot only, no production apply path."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
pilot = (root / "services/time/MachineWindowMovePilot.py").read_text(encoding="utf-8")
qml = (root / "widgets/TimeW.qml").read_text(encoding="utf-8")
for required in (
    "def preview_one(saved_document, request, *, read_runner):",
    "def execute_one(saved_document, request, *, read_runner, command_runner, journal):",
    "approval_required=True",
    "if approval_required and req[\"approved\"] is not True:",
    "def _preflight(saved_document, request, *, runner, approval_required):",
    "def _observe(runner, saved_document, request):",
    'return {"status": "ready_for_review", "executable": False,',
    '"requires_fresh_revalidation": True',
    '"no_automatic_undo": True',
    'if not isinstance(journal, MoveJournal):',
    'operation_id = journal.begin(report["before"])',
    'journal.mark_dispatching(operation_id)',
    'journal.finish(operation_id, status,',
    'status = "uncertain_requires_manual_review"',
    'status = "refused_no_confirmed_move"',
    'status = "verified_moved"',
    '["swaymsg", "-r", "-t", "command", report["command"]]',
    'NUMERIC_WORKSPACE = re.compile',
    'MAX_COMMAND_RESPONSE = 4096',
):
    assert required in pilot, required
assert 'if __name__ == "__main__"' not in pilot
assert "subprocess.run" not in pilot
assert "os.system" not in pilot
assert "shell=True" not in pilot
assert "Popen(" not in pilot
assert "exec " not in pilot
for forbidden in (
    "MachineWindowMovePilot.py",
    "machineApplyMove(", "onLeftClicked: timew.applyRecovery",
    "onLeftClicked: timew.executeMove"
):
    assert forbidden not in qml, forbidden
assert "NO SCREENSHOTS OR RESTORATION ACTIVE" in qml
assert 'label: "RESOLVE LIVE"' in qml
print("TIMEW MACHINE M1K: ISOLATED PILOT CONTRACT PASS / NO LIVE WIRING")
