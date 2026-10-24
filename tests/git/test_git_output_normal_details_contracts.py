#!/usr/bin/env python3
"""Check GitW's actual Normal/Details presentation code without Quickshell.

Only status-only repetition may be suppressed. Journal BEGIN/COMPLETE/FAIL
profiles and the independent REFRESHED boundary are unique and must remain
visible in Normal, while Details retains raw evidence byte-for-byte.
"""
from pathlib import Path
import json
import subprocess

root = Path(__file__).resolve().parents[2]
view = (root / "widgets/GitW.qml").read_text()
service = (root / "services/git/GitService.qml").read_text()

start = view.index("                            function normalGitOutput(output, isSync) {")
end = view.index("                            SharedComponents.ActionButton {", start)
normal_js = view[start:end].strip()

assert 'property bool showDetails: false' in view
assert 'id: gitOutputModeToggle' in view
assert 'visible: syncTimingHeader.isSyncOutput' in view
assert 'label: gitOutputPanel.showDetails ? "DETAILS" : "NORMAL"' in view
assert 'selected: gitOutputPanel.showDetails' in view
assert 'onClicked: gitOutputPanel.showDetails =' in view
assert 'gitOutputPanel.normalGitOutput(' in view
assert 'gitService.actionOutput,' in view
assert 'syncTimingHeader.isSyncOutput)' in view
assert 'gitOutputPanel.showDetails\n                                        ? gitService.actionOutput' in view
assert 'height: 112' in view
assert 'syncTimingHeader.visible ? 33 : 24' in view
assert 'NeonScrollBar {' in view
assert 'text: gitOutputPanel.showDetails' in view

# No change to canonical recorded evidence: the UI is the only modified file.
assert 'JOURNAL PROFILE // ' in service
assert 'JOURNAL NOT RECORDED // Git subprocess' in service
assert 'SNAPSHOT WARNING // ' in service
assert 'FINISHED // after snapshot ' in service
assert 'PREPARED // snapshot ' in service

node = r"""
const assert = require('node:assert/strict');
const vm = require('node:vm');
vm.runInThisContext(SOURCE);
const raw = [
    'PREPARING // capturing repository references and journal evidence',
    'PREPARED // snapshot 35 ms // journal 90 ms',
    'JOURNAL PROFILE // BEGIN clone 0 ms // record 1 ms',
    'RUNNING // Git subprocess started',
    'From https://github.com/sample/repo',
    '   abc123..def456 main -> origin/main',
    'Already up to date.',
    'FINALIZING // collecting repository evidence',
    'FINISHED // after snapshot 28 ms // journal 100 ms',
    'JOURNAL PROFILE // COMPLETE clone 0 ms // entries 1 ms',
    'REFRESHED // repository view 1400 ms',
    'SNAPSHOT WARNING // after snapshot could not be captured',
    'JOURNAL NOT RECORDED // AFTER save unconfirmed',
    'FETCH FAILED // connection timed out',
    'STILL RUNNING // watchdog is observing Git',
    'error: permission denied'
].join('\n');

const compact = normalGitOutput(raw, true);
assert.equal(normalGitOutput(raw, false), raw,
    'non Fetch/Pull actions must remain byte-identical');
assert.equal(normalGitOutput('', true), '');
assert.equal(normalGitOutput(null, true), '');
assert.equal(compact, [
    'PREPARING // capturing repository references and journal evidence',
    'PREPARED // snapshot 35 ms // journal 90 ms',
    'JOURNAL PROFILE // BEGIN clone 0 ms // record 1 ms',
    'From https://github.com/sample/repo',
    '   abc123..def456 main -> origin/main',
    'Already up to date.',
    'FINISHED // after snapshot 28 ms // journal 100 ms',
    'JOURNAL PROFILE // COMPLETE clone 0 ms // entries 1 ms',
    'REFRESHED // repository view 1400 ms',
    'SNAPSHOT WARNING // after snapshot could not be captured',
    'JOURNAL NOT RECORDED // AFTER save unconfirmed',
    'FETCH FAILED // connection timed out',
    'STILL RUNNING // watchdog is observing Git',
    'error: permission denied'
].join('\n'));

assert.ok(compact.includes('JOURNAL PROFILE // BEGIN'));
assert.ok(compact.includes('JOURNAL PROFILE // COMPLETE'));
assert.ok(compact.includes('REFRESHED // repository view 1400 ms'));
assert.ok(!compact.includes('RUNNING // Git subprocess started'));
assert.ok(!compact.includes('FINALIZING // collecting repository evidence'));
const failed = normalGitOutput([
    'JOURNAL PROFILE // FAIL clone 0 ms',
    'JOURNAL NOT RECORDED // persistent failure',
    'JOURNAL PROFILE // UNEXPECTED DATA',
    'REFRESHED // repository view unavailable',
    'REFRESHED // repository view 3 ms'
].join('\n'), true);
assert.equal(failed,
    'JOURNAL PROFILE // FAIL clone 0 ms\n'
    + 'JOURNAL NOT RECORDED // persistent failure\n'
    + 'JOURNAL PROFILE // UNEXPECTED DATA\n'
    + 'REFRESHED // repository view unavailable\n'
    + 'REFRESHED // repository view 3 ms',
    'all unique timing and unexpected statuses must stay visible');
assert.equal(normalGitOutput('   unrelated text\n\n   summary', true),
    '   unrelated text\n\n   summary', 'retain whitespace and blank lines');
console.log('Git Normal/Details selective diagnostics: PASS');
""".replace("SOURCE", normal_js)
res = subprocess.run(
    ["node", "-e", node], cwd=root,
    capture_output=True, text=True, check=False, timeout=20
)
assert res.returncode == 0, res.stdout + "\n" + res.stderr
print(res.stdout.strip())
print("Git view-only filtering / durable journal source contracts: PASS")
