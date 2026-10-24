#!/usr/bin/env python3
"""Execute the actual GitW NORMAL formatter and prove no unique values vanish.

Presentation only; canonical GitService actionOutput and durable journal are
untouched. All unknown Git stdout/stderr or malformed diagnostics pass through.
"""
from pathlib import Path
import json
import subprocess

root = Path(__file__).resolve().parents[2]
view = (root / "widgets/GitW.qml").read_text()
service = (root / "services/git/GitService.qml").read_text()

a = view.index("                            function compactGitTimingLine(line) {")
b = view.index("                            SharedComponents.ActionButton {", a)
formatter = view[a:b].strip()
assert "function normalGitOutput(output, isSync, repoViewMs)" in formatter
assert "return compactGitTimingLine(line);" in formatter
assert 'gitOutputPanel.showDetails\n                                        ? gitService.actionOutput' in view
assert "JOURNAL PROFILE // " in service
assert "REFRESHED // repository view " in service
assert "FINISHED // after snapshot " in service
assert "PREPARED // snapshot " in service
assert "JOURNAL NOT RECORDED" in service
assert "height: 112" in view

node = r"""
const assert = require('node:assert/strict');
const vm = require('node:vm');
SOURCE

const before = 'PREPARED // snapshot 123 ms // journal 98 ms (encode 27 ms / disk 8 ms)';
const begin = 'JOURNAL PROFILE // BEGIN clone 0 ms // record 2 ms // entries 1 ms // persist 90 ms // notify 3 ms // mutation 96 ms';
const after = 'FINISHED // after snapshot 54 ms // journal 110 ms (encode 31 ms / disk 9 ms)';
const complete = 'JOURNAL PROFILE // COMPLETE clone 1 ms // record 5 ms // entries 2 ms // persist 105 ms // notify 3 ms // mutation 115 ms';
const failed = 'JOURNAL PROFILE // FAIL clone 7 ms // record 8 ms // entries 9 ms // persist 10 ms // notify 11 ms // mutation 12 ms';
const refreshed = 'REFRESHED // repository view 1345 ms';
const raw = [
 'PREPARING // capturing repository references and journal evidence',
 before, begin,
 'RUNNING // Git subprocess started',
 'From https://github.com/example/project',
 '   53fe34..6fa2dc main -> origin/main',
 'Already up to date.',
 'FINALIZING // collecting repository evidence',
 after, complete, failed, refreshed,
 'SNAPSHOT WARNING // after snapshot could not be captured',
 'JOURNAL NOT RECORDED // AFTER save unconfirmed',
 'fatal: unable to access remote',
 'warning: repository identity not confirmed'
].join('\n');

const expected = [
 'PREPARING // capturing repository references and journal evidence',
 'PREPARED [ms] │ snapshot 123 · journal 98 (encode 27 · disk 8)',
 'JOURNAL PROFILE BEGIN [ms] │ clone 0 · record 2 · entries 1 · persist 90 · notify 3 · mutation 96',
 'From https://github.com/example/project',
 '   53fe34..6fa2dc main -> origin/main',
 'Already up to date.',
 'FINISHED [ms] │ after snapshot 54 · journal 110 (encode 31 · disk 9)',
 'JOURNAL PROFILE COMPLETE [ms] │ clone 1 · record 5 · entries 2 · persist 105 · notify 3 · mutation 115',
 'JOURNAL PROFILE FAIL [ms] │ clone 7 · record 8 · entries 9 · persist 10 · notify 11 · mutation 12',
 'REFRESHED │ repository view 1345ms',
 'SNAPSHOT WARNING // after snapshot could not be captured',
 'JOURNAL NOT RECORDED // AFTER save unconfirmed',
 'fatal: unable to access remote',
 'warning: repository identity not confirmed'
].join('\n');

assert.equal(normalGitOutput(raw, true), expected,
 'all stage identities, units, labels, values, Git results and safety messages must survive');
assert.equal(normalGitOutput(raw, false), raw, 'non-sync output is untouched');
assert.equal(normalGitOutput(raw, false, 1345), raw, 'DETAILS is raw');
assert.equal(normalGitOutput(raw, true, 1345), expected.replace(
 'REFRESHED │ repository view 1345ms\\n', ''),
 'NORMAL moves the exact repository-view value to the pinned header');
assert.equal(normalGitOutput(raw, true, 1344), expected,
 'wrong header value must not suppress a distinct measurement');
assert.ok(expected.length < raw.length, 'less wrapped text without omitting fields');
assert.equal(compactGitTimingLine(complete),
 'JOURNAL PROFILE COMPLETE [ms] │ clone 1 · record 5 · entries 2 · persist 105 · notify 3 · mutation 115');
assert.equal(normalGitOutput('JOURNAL PROFILE // UNEXPECTED DATA', true),
 'JOURNAL PROFILE // UNEXPECTED DATA');
assert.equal(normalGitOutput('REFRESHED // repository view unavailable', true),
 'REFRESHED // repository view unavailable');
assert.equal(normalGitOutput('FINISHED // after snapshot -1 ms // journal 0 ms', true),
 'FINISHED // after snapshot -1 ms // journal 0 ms');
assert.equal(normalGitOutput('  unknown content  \n\nerror: ACCESS DENIED', true),
 '  unknown content  \n\nerror: ACCESS DENIED', 'whitespace and errors must survive');
assert.equal(normalGitOutput('', true), '');
assert.equal(normalGitOutput(null, true), '');
console.log('Git compact journal evidence: exact values and safety lines PASS');
""".replace("SOURCE", formatter)
result = subprocess.run(
    ["node", "-e", node], cwd=root, text=True,
    capture_output=True, timeout=20, check=False
)
assert result.returncode == 0, result.stdout + "\n" + result.stderr
print(result.stdout.strip())
print("Git NORMAL compact formatting/DETAILS raw output contracts: PASS")
