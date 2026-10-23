#!/usr/bin/env python3
"""Exercise Fetch/Pull timeline arithmetic without launching Quickshell or Git."""
from pathlib import Path
import json
import subprocess

root = Path(__file__).resolve().parents[2]
service = (root / "services/git/GitService.qml").read_text()
body = service.split(
    "// End-to-end timing is emitted only after refreshing the UI", 1
)[1].split("if (trace) started = Date.now();", 1)[0]
assert body.count("SYNC TIMELINE // prepare") == 1
assert "const refreshMs = end - pipelineRefreshStartedMs;" in body
assert "const gitMs = syncCommandFinishedMs - syncCommandStartedMs;" in body
assert "const finalizeMs = pipelineRefreshStartedMs - syncCommandFinishedMs;" in body
assert "syncCommandStartedMs = 0;" in body
assert "syncCommandFinishedMs = 0;" in body

# The timing is presentation-only, not a substitute for the BEFORE/AFTER gate.
before = service.index('operationJournal.beginOperation(')
after = service.index('operationJournal.completeOperation(')
unlock = service.index('actionBusy = false;', after)
refresh = service.index('refresh();', unlock)
assert before < after < unlock < refresh
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
        actionOutput: 'BEFORE'
    }, overrides);
    state.Date = {now: () => 8000};
    vm.runInNewContext(source, state);
    return state;
}
const good = run();
assert.equal(good.actionOutput,
    'BEFORE\\nSYNC TIMELINE // prepare 400 ms // git 1400 ms'
    + ' // finalize 200 ms // refresh 1000 ms // total 3000 ms');
assert.equal(good.syncCommandStartedMs, 0);
assert.equal(good.syncCommandFinishedMs, 0);

const invalid = run({syncCommandFinishedMs: 5300});
assert.equal(invalid.actionOutput, 'BEFORE');
assert.equal(invalid.syncCommandStartedMs, 5400);
const unrelated = run({pipelineRefreshStartedMs: 0});
assert.equal(unrelated.actionOutput, 'BEFORE');
const previousAction = run({syncStartedMs: 5600});
assert.equal(previousAction.actionOutput, 'BEFORE');
console.log('Git Fetch/Pull pipeline phase arithmetic: PASS');
""".replace("SOURCE", json.dumps(body))
result = subprocess.run(
    ["node", "-e", script], cwd=root, text=True, capture_output=True,
    check=False, timeout=20
)
assert result.returncode == 0, result.stdout + "\n" + result.stderr
print(result.stdout.strip())
print("Git pipeline journal/refresh boundary contracts: PASS")
