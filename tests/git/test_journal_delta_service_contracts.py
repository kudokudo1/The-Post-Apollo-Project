#!/usr/bin/env python3
"""Source-safety rules for the opt-in two-file Git journal writer."""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
journal=(ROOT / "services/git/GitOperationJournalService.qml").read_text()
control=(ROOT / "services/git/GitService.qml").read_text()

def section(begin,end):
    assert begin in journal and end in journal
    return journal.split(begin,1)[1].split(end,1)[0]

assert 'POST_APOLLO_GIT_JOURNAL_DELTA' in journal
assert 'property bool storageReady: false' in journal
assert 'if (!repo || !operationKind || !storageReady)' in journal
assert 'deltaActive = deltaRequested || overlay.present;' in journal
assert 'property var encodedDeltaRecords: []' in journal
assert 'encodedDeltaRecords = [];' in journal
assert 'storageReady = false;' in journal and 'storageReady = true;' in journal
assert 'JOURNAL STORAGE BLOCKED' in journal
assert 'const record = Object.assign({}, row, {' in journal
assert 'undoState: String(row.undoState || "NOT_IMPLEMENTED")' in journal

assert 'path: Qt.resolvedUrl("../../git-operation-journal.json")' in journal
assert 'path: Qt.resolvedUrl("../../git-operation-journal-delta.json")' in journal
assert journal.count('blockLoading: true') == 2
assert journal.count('blockWrites: true') == 2
assert journal.count('atomicWrites: true') == 2
assert 'Component.onCompleted:' in journal
assert 'onLoaded: root.load()' not in journal

save=section('function persist(record) {','\n    FileView {')
assert 'record.kind === "CONTROL/FETCH"' in save
assert 'record.kind === "CONTROL/PULL"' in save
assert 'DeltaCodec.upsert(deltaRecords, record)' in save
assert 'DeltaCodec.encodeSidecarCached(' in save
assert 'checkpointGeneration, revised, encodedDeltaRecords' in save
assert 'lastPersistReusedCount = encoded.reusedCount;' in save
assert save.index('deltaFile.setText(serialized)') < save.index('encodedDeltaRecords = encoded.cache;')
assert save.index('if (!requireWriteAck("DELTA"))') < save.index('encodedDeltaRecords = encoded.cache;')
assert save.index('checkpointGeneration = nextGeneration;') < save.index('encodedDeltaRecords = [];')
assert 'if (revised.length < maxDeltaRecords)' in save
assert 'deltaFile.setText(serialized)' in save
assert 'journalFile.setText(data)' in save
assert save.index('journalFile.setText(data)') < save.index(
    'deltaFile.setText(\n                DeltaCodec.encodeSidecar(nextGeneration, [])'
), 'checkpoint must land before sidecar clear'
assert 'checkpointGeneration = nextGeneration' in save
assert 'return true;' in save

for fragment in (
    'const saved = persist(record);',
    'if (!saved) {',
    'markMutationProfile("BEGIN_FAILED"',
    'markMutationProfile("COMPLETE_FAILED"',
    'markMutationProfile("FAIL_FAILED"',
    'operationStarted(operationId, cloneValue(record));',
    'operationFinished(operationId, true, cloneValue(record));',
    'operationFinished(operationId, false, cloneValue(record));',
    'if (repairedInterrupted)\n            persist();',
    'next[index] = record;\n        entries = next;\n        return persist();',
):
    assert fragment in journal, fragment

# Blocking FileView writes report void; journal success needs a synchronous
# saved() acknowledgement and must fail closed on saveFailed().
for fragment in (
    'property int journalWriteStatus: 0',
    'property int deltaWriteStatus: 0',
    'function requireWriteAck(channel)',
    'if (!requireWriteAck("DELTA"))',
    'if (!requireWriteAck("CHECKPOINT"))',
    'onSaved: root.journalWriteStatus = 1',
    'onSaved: root.deltaWriteStatus = 1',
    'onSaveFailed: function(error)',
    'function blockStorage(reason)',
):
    assert fragment in journal, fragment
assert journal.count('onSaveFailed: function(error)') == 2
assert 'return blockStorage("PERSIST EXCEPTION //' in journal

# Phase instrumentation must not copy operation contents or touch disk.
for token in (
    'property var lastMutationProfile: ({})',
    'function markMutationProfile(stage, started, built, published, saved, notified)',
    'recordMs: Math.max(0, built - started)',
    'entriesMs: Math.max(0, published - built)',
    'persistMs: Math.max(0, saved - published)',
    'notifyMs: Math.max(0, notified - saved)',
    'totalMs: Math.max(0, notified - started)',
):
    assert token in journal, token

# Keep every Undo / recovery consumer's public contract unchanged.
for fragment in (
    'function beginOperation(',
    'function completeOperation(',
    'function failOperation(',
    'function markUndoResult(',
    'property var entries: []',
    'readonly property var repositoryEntries:',
):
    assert fragment in journal
assert 'operationJournal.beginOperation(' in control
assert 'operationJournal.completeOperation(' in control
assert 'operationJournal.failOperation(' in control

print("Git journal opt-in partition storage source contracts: PASS")
