#!/usr/bin/env python3
"""Run the QML-safe serializer with Node against synthetic journal state."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
code = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = 'services/git/GitJournalSerialization.js';
const context = vm.createContext({});
vm.runInContext(fs.readFileSync(path, 'utf8'), context);
const serialize = context.serializeJournal;

const records = Array.from({length: 500}, (_, i) => ({
  id: 'record-' + i,
  repository: '/synthetic/repository',
  kind: i % 2 ? 'CONTROL/PULL' : 'CONTROL/FETCH',
  status: 'COMPLETE',
  before: { refs: [{ name: 'refs/heads/main', sha: String(i) }], worktrees: [] },
  after: { refs: [{ name: 'refs/heads/main', sha: String(i + 1) }], worktrees: [] },
  metadata: { target: 'origin/main', notes: '💜' }
}));
const legacy = JSON.stringify({schemaVersion: 1, entries: records});
const first = serialize(1, records, []);
assert.equal(first.text, legacy);
assert.equal(first.reusedCount, 0);
assert.equal(JSON.parse(first.text).entries.length, 500);

const moved = { ...records[0], status: 'UNDONE', undoState: 'UNDONE' };
const updated = [moved, ...records.slice(1)];
const second = serialize(1, updated, first.cache);
assert.equal(second.reusedCount, 499);
assert.equal(second.text, JSON.stringify({schemaVersion: 1, entries: updated}));
assert.equal(JSON.parse(second.text).entries[0].status, 'UNDONE');

const inserted = [{id:'new', status:'RUNNING', before:{head:'HEAD'}}, ...updated].slice(0, 500);
const third = serialize(1, inserted, second.cache);
assert.equal(third.reusedCount, 499);
assert.equal(third.text, JSON.stringify({schemaVersion: 1, entries: inserted}));
const finished = [{...inserted[0], status:'COMPLETE', after:{head:'AFTER'}}, ...inserted.slice(1)];
const fourth = serialize(1, finished, third.cache);
assert.equal(fourth.reusedCount, 499);
assert.equal(fourth.text, JSON.stringify({schemaVersion: 1, entries: finished}));

const reloaded = JSON.parse(fourth.text);
const uncached = serialize(1, reloaded.entries, []);
assert.equal(uncached.text, fourth.text);
assert.equal(uncached.reusedCount, 0);
assert.equal(serialize(2, reloaded.entries, fourth.cache).text,
             JSON.stringify({schemaVersion: 2, entries: reloaded.entries}));
console.log('Git journal incremental serialization synthetic runtime: PASS');
"""
completed = subprocess.run(
    ["node", "-e", code], cwd=ROOT, check=False,
    capture_output=True, text=True, timeout=30,
)
assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
print(completed.stdout.strip())
