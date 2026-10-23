#!/usr/bin/env python3
"""Guard inactive Git Operations history binding and live re-entry semantics.

This is a QML source/binding expression contract, not a live Quickshell
performance benchmark or a claim that other journal consumers are inexpensive.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
view = (ROOT / "widgets/GitOperationsView.qml").read_text()
menu = (ROOT / "widgets/GitW.qml").read_text()
journal = (ROOT / "services/git/GitOperationJournalService.qml").read_text()

body = view.split("readonly property var entries:", 1)[1].split(
    "readonly property var selectedRecord:", 1
)[0]
expression = " ".join(line.strip() for line in body.splitlines() if line.strip())
assert expression == (
    "root.visible && operationJournal ? operationJournal.repositoryEntries : []"
), expression
assert "model: root.entries" in view
assert "root.selectedRecord" in view
assert "recoveryService.preview(selectedRecord)" in view
assert "onOperationStarted(operationId, record)" in view
assert "onOperationFinished(operationId, success, record)" in view

operations = menu.split("GitOperationsView {", 1)[1].split(
    "GitBranchesView {", 1
)[0]
assert 'root.activePage === "git"' in operations
assert 'root.gitView === "operations"' in operations
assert "operationJournal: operationJournalService" in operations

# The optimization is presentation-only: do not defer durable journal writes,
# signals, recovery or public record access to make the UI seem faster.
assert "property var entries: []" in journal
assert "readonly property var repositoryEntries:" in journal
assert "operationStarted(operationId, cloneValue(record));" in journal
assert "operationFinished(operationId, true, cloneValue(record));" in journal
assert "operationFinished(operationId, false, cloneValue(record));" in journal
assert "if (!requireWriteAck(\"DELTA\"))" in journal
assert "if (!requireWriteAck(\"CHECKPOINT\"))" in journal

script = r"""
const assert = require('node:assert/strict');
const vm = require('node:vm');
let reads = 0;
let rows = [{id:'old'}];
const journal = {};
Object.defineProperty(journal, 'repositoryEntries', {
    get() { reads++; return rows; }
});
function run(visible) {
    return vm.runInNewContext(EXPRESSION, {
        root: {visible}, operationJournal: journal
    });
}
assert.deepEqual(Array.from(run(false)), []);
assert.equal(reads, 0, 'hidden view must not read large journal model');
assert.equal(run(true)[0].id, 'old');
assert.equal(reads, 1);
rows = [{id:'new'}, {id:'old'}];
assert.equal(run(true)[0].id, 'new', 're-open must use newest rows');
assert.deepEqual(Array.from(run(false)), []);
assert.equal(reads, 2);
console.log('Git Operations visibility-gated journal binding: PASS');
""".replace("EXPRESSION", repr(expression))
# repr() is Python-quoted JS text, valid as the string argument to vm.
result = subprocess.run(
    ["node", "-e", script], cwd=ROOT,
    capture_output=True, text=True, timeout=20, check=False
)
assert result.returncode == 0, result.stdout + "\n" + result.stderr
print(result.stdout.strip())
print("Git Operations QML presentation-only safety contracts: PASS")
