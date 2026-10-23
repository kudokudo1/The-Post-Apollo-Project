#!/usr/bin/env python3
"""Run extracted *service* logic using disposable FileView doubles.

This exercises journal begin/complete/load/replay without touching the user's
files. It does NOT certify the Qt FileView runtime or disk-level fsync.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
test = ROOT / "tests/git/fixtures/journal_delta_service_runtime.cjs"
result = subprocess.run(
    ["node", str(test)],
    cwd=ROOT, text=True, capture_output=True, timeout=45, check=False,
)
assert result.returncode == 0, result.stdout + "\n" + result.stderr
print(result.stdout.strip())

# The basic FETCH/PULL buttons already unlock after the durable AFTER record.
# Guard that useful behavior without dropping the BEFORE/AFTER evidence gate.
service = (ROOT / "services/git/GitService.qml").read_text()
widget = (ROOT / "widgets/GitW.qml").read_text()
finalize = service.split("function finalizeControlAction(", 1)[1].split(
    "function finishActionProcess(", 1
)[0]
journal_at = finalize.index("operationJournal.completeOperation(")
unlock_at = finalize.index('actionBusy = false;')
refresh_at = finalize.rindex('refresh();')
assert journal_at < unlock_at < refresh_at, (
    "completion must be journaled before unlocking, with refresh afterward"
)
assert 'journalRecorded = operationJournal.completeOperation(' in finalize
assert 'journalRecorded = operationJournal.failOperation(' in finalize
assert 'if (!journalRecorded)' in finalize
assert '"JOURNAL NOT RECORDED // Git subprocess "' in finalize
assert 'actionExitCode = 1;' in finalize.split('if (!journalRecorded)', 1)[1], (
    "the UI must warn even if Git itself succeeded"
)
# The timing line is diagnostic only. It must not turn into an apparent
# Git completion message or move the durable-before-unlock boundary.
assert 'function journalProfileLine(stage, snapshotCloneMs)' in service
assert 'JOURNAL PROFILE // ' in service  # Prefix includes an escaped newline.
assert 'value.indexOf("JOURNAL PROFILE //") === 0' in service
before = service.split('if (gitService.snapshotPhase === "BEFORE")', 1)[1].split(
    'if (gitService.snapshotPhase === "AFTER")', 1
)[0]
assert 'const snapshotCloneMs = Date.now() - journalStartedMs;' in before
assert 'gitService.journalProfileLine(' in before
assert 'journalProfileLine(' in finalize
assert 'const snapshotCloneMs = Date.now() - finalizationStarted;' in finalize

local_actions = widget.split('label: "FETCH"', 1)[1].split('label: "STATUS"', 1)[0]
fetch = local_actions.split('label: "FETCH"', 1)[-1].split('onTriggered: gitService.runSyncAction("fetch")', 1)[0]
pull = local_actions.split('gitService.runSyncAction("pull");', 1)[0]
assert '!gitService.actionBusy' in fetch
assert '!gitService.actionBusy' in pull
assert '!gitService.refreshing' not in fetch
assert '!gitService.refreshing' not in pull
print("Git Menu durable-unlock/refresh ordering: PASS")
