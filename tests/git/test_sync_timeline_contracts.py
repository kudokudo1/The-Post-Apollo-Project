#!/usr/bin/env python3
"""Exercise Fetch/Pull timeline arithmetic without launching Quickshell or Git."""
from pathlib import Path
import json
import subprocess

root = Path(__file__).resolve().parents[2]
service = (root / "services/git/GitService.qml").read_text()
body = "if (pipelineRefreshStartedMs > 0" + service.split(
    "if (pipelineRefreshStartedMs > 0", 1
)[1].split("if (trace) started = Date.now();", 1)[0]
assert "SYNC TIMELINE //" not in body
assert "syncTimingTotalMs = end - syncStartedMs;" in body
assert "syncTimingPrepareMs = prepareMs;" in body
assert "syncTimingGitMs = gitMs;" in body
assert "syncTimingFinalizeMs = finalizeMs;" in body
assert "syncTimingRefreshMs = refreshMs;" in body
assert "const refreshMs = end - pipelineRefreshStartedMs;" in body
assert "const gitMs = syncCommandFinishedMs - syncCommandStartedMs;" in body
assert "const finalizeMs = pipelineRefreshStartedMs - syncCommandFinishedMs;" in body
assert "syncCommandStartedMs = 0;" in body
assert "syncCommandFinishedMs = 0;" in body

# The timing is presentation-only, not a substitute for the BEFORE/AFTER gate.
before = service.split('if (gitService.snapshotPhase === "BEFORE")', 1)[1]
assert 'operationJournal.beginOperation(' in before
finalize = service.split("function finalizeControlAction(", 1)[1].split(
    "function finishActionProcess(", 1
)[0]
after = finalize.index('operationJournal.completeOperation(')
unlock = finalize.index('actionBusy = false;', after)
refresh = finalize.rindex('refresh();')
assert after < unlock < refresh
assert service.index('syncCommandStartedMs = Date.now();') < service.index(
    'actionProcess.exec(pendingActionCommand);'
)
assert service.index('syncCommandFinishedMs = Date.now();') < service.index(
    'pendingActionSuccess = actionExitCode === 0;'
)
assert 'if (!journalRecorded)' in service

# Evaluate the actual embedded JS branch under a fixed clock. Asserts that
# phase durations add up to elapsed wall time and invalid sequences are ignored.
script = """
const assert = require('node:assert/strict');
const vm = require('node:vm');
const source = SOURCE;
function run(overrides = {}) {
    const state = Object.assign({
        pipelineRefreshStartedMs: 7000,
        syncStartedMs: 5000,
        syncCommandStartedMs: 5400,
        syncCommandFinishedMs: 6800,
        actionOutput: 'BEFORE',
        syncTimingPrepareMs: -1, syncTimingGitMs: -1,
        syncTimingFinalizeMs: -1, syncTimingRefreshMs: -1,
        syncTimingTotalMs: -1
    }, overrides);
    state.Date = {now: () => 8000};
    vm.runInNewContext(source, state);
    return state;
}
const good = run();
assert.equal(good.actionOutput, 'BEFORE', 'do not duplicate values in log');
assert.equal(good.syncTimingPrepareMs, 400);
assert.equal(good.syncTimingGitMs, 1400);
assert.equal(good.syncTimingFinalizeMs, 200);
assert.equal(good.syncTimingRefreshMs, 1000);
assert.equal(good.syncTimingTotalMs, 3000);
assert.equal(good.syncCommandStartedMs, 0);
assert.equal(good.syncCommandFinishedMs, 0);

const invalid = run({syncCommandFinishedMs: 5300});
assert.equal(invalid.actionOutput, 'BEFORE');
assert.equal(invalid.syncTimingTotalMs, -1);
assert.equal(invalid.syncCommandStartedMs, 5400);
const unrelated = run({pipelineRefreshStartedMs: 0});
assert.equal(unrelated.actionOutput, 'BEFORE');
assert.equal(unrelated.syncTimingTotalMs, -1);
const previousAction = run({syncStartedMs: 5600});
assert.equal(previousAction.actionOutput, 'BEFORE');
assert.equal(previousAction.syncTimingTotalMs, -1);
console.log('Git Fetch/Pull pipeline phase arithmetic: PASS');
""".replace("SOURCE", json.dumps(body))
result = subprocess.run(
    ["node", "-e", script], cwd=root, text=True, capture_output=True,
    check=False, timeout=20
)
assert result.returncode == 0, result.stdout + "\n" + result.stderr
print(result.stdout.strip())
print("Git pipeline journal/refresh boundary contracts: PASS")
