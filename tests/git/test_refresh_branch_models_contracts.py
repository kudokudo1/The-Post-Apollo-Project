#!/usr/bin/env python3
"""Run actual QML-JS branch list publication against deterministic ListModel fakes.

No user repo, system Qt instance, Git subprocess, journal, or network touched.
"""
from pathlib import Path
import json
import subprocess

root = Path(__file__).resolve().parents[2]
source = (root / "services/git/GitService.qml").read_text()
start = source.index("    function branchModelMatches(")
end = source.index("    function allocateLane(", start)
actual = source[start:end]
assert actual.count("function branchModelMatches") == 1
assert actual.count("function publishPendingModels") == 1
assert "const topologyDelta = reconcileTopologyRows();" in actual

js = r"""
const assert = require('node:assert/strict');
const vm = require('node:vm');
const functions = SOURCE;
function model(rows) {
  return {
    rows: rows.map(row => ({...row})),
    clears: 0, appends: 0,
    get count() { return this.rows.length; },
    get(i) { return this.rows[i]; },
    clear() { this.clears++; this.rows.length = 0; },
    append(row) { this.appends++; this.rows.push({...row}); }
  };
}
const l1 = {name:'main', head:'aaa', upstream:'origin/main',unpulledCount:0,lastChangedEpoch:0};
const l2 = {name:'feature',head:'bbb',upstream:'origin/feature',unpulledCount:1,lastChangedEpoch:100};
const r1 = {name:'origin/main',unpulledCount:0,remoteOnly:false,lastChangedEpoch:0};
const r2 = {name:'origin/feature',unpulledCount:1,remoteOnly:true,lastChangedEpoch:100};
let topologies = 0;
const state = {
  syntagmaStartupTraceEnabled:false,
  pendingRepoRoot:'/tmp/example', pendingRepository:'example',
  pendingBranch:'main', pendingHead:'aaa', pendingHeadFull:'aaa-full',
  pendingWorktree:'CLEAN', pendingOrigin:'origin', pendingUpstream:'origin/main',
  pendingAhead:0, pendingBehind:0,
  pendingLocalBranches:[{...l1},{...l2}],
  pendingRemoteBranches:[{...r1},{...r2}, {name:'not-remote'}],
  localBranchRows:model([l1,l2]),
  remoteBranchRows:model([r1,r2]),
  isRemoteBranchTarget:(name) => name.startsWith('origin/'),
  reconcileTopologyRows:() => {topologies++; return {unchanged:10};}
};
vm.createContext(state);
vm.runInContext(functions, state);
const publish = () => vm.runInContext('publishPendingModels()', state);
publish();
assert.equal(state.localBranchRows.clears,0,'unchanged local rows must not clear');
assert.equal(state.remoteBranchRows.clears,0,'unchanged remote rows must not clear');
assert.equal(state.localBranchRows.appends,0);
assert.equal(state.remoteBranchRows.appends,0);
assert.equal(topologies,1,'topology reconciliation remains active');

state.pendingRemoteBranches[1].unpulledCount=0;
publish();
assert.equal(state.localBranchRows.clears,0,'local side unaffected by remote delta');
assert.equal(state.remoteBranchRows.clears,1);
assert.equal(state.remoteBranchRows.rows[1].unpulledCount,0);
assert.equal(state.remoteBranchRows.appends,2);

state.pendingLocalBranches[0].head='changed';
publish();
assert.equal(state.localBranchRows.clears,1);
assert.equal(state.localBranchRows.rows[0].head,'changed');
assert.equal(state.remoteBranchRows.clears,1);

state.pendingLocalBranches.reverse();
state.pendingRemoteBranches=[{...r1}];
publish();
assert.equal(state.localBranchRows.rows[0].name,'feature');
assert.equal(state.remoteBranchRows.rows.length,1);
assert.equal(state.remoteBranchRows.rows[0].name,'origin/main');
state.pendingLocalBranches = [];
state.pendingRemoteBranches = [];
publish();
assert.equal(state.localBranchRows.rows.length,0);
assert.equal(state.remoteBranchRows.rows.length,0);
assert.equal(topologies,5);
state.syntagmaStartupTraceEnabled=true;
const receipt = publish();
assert.ok(receipt.topologyDelta && receipt.topologyDelta.unchanged===10);
assert.equal(topologies,6);
console.log('Git refresh unchanged/changed branch ListModel runtime: PASS');
""".replace("SOURCE", json.dumps(actual))
test = subprocess.run(
    ["node", "-e", js], cwd=root, text=True, capture_output=True,
    timeout=20, check=False
)
assert test.returncode == 0, test.stdout + "\n" + test.stderr
print(test.stdout.strip())

# Existing durable BEFORE/AFTER snapshot and journal barriers are unchanged.
assert 'pendingJournalId =\n                    gitService.operationJournal' in source
assert 'journalRecorded = operationJournal.completeOperation(' in source
assert 'if (!journalRecorded)' in source
assert 'clearPendingControlAction();' in source
print("Git branch refresh did not alter journal safety entrypoints: PASS")
