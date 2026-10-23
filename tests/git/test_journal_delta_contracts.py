#!/usr/bin/env python3
"""Synthetic delta overlay, legacy migration, and checkpoint crash-window tests."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
js = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const scope = vm.createContext({});
vm.runInContext(fs.readFileSync('services/git/GitJournalDelta.js','utf8'),scope);
const d = scope;

const make = (i, status='COMPLETE') => ({
    schemaVersion:1, id:'op-'+i, kind:i%2?'CONTROL/PULL':'CONTROL/FETCH',
    repository:'/synthetic', status, before:{refs:[{sha:'a'+i}]},
    after:{refs:[{sha:'b'+i}]},metadata:{label:'🟣'}, recoveryClass:'EVIDENCE_ONLY'
});
const base = Array.from({length:500},(_,i)=>make(500-i));
let rows = [];
const before = make(501,'RUNNING');
rows = d.upsert(rows,before);
rows = d.upsert(rows,{...before,status:'COMPLETE',after:{refs:[{sha:'b501'}]}});
assert.equal(rows.length,1);
assert.equal(rows[0].status,'COMPLETE');
const complete = d.overlay(base,rows,500);
assert.equal(complete.length,500);
assert.equal(complete[0].id,'op-501');
assert.equal(complete[1].id,base[0].id);
assert.equal(complete[499].id,base[498].id);
assert.equal(JSON.stringify(d.overlay(base,rows,500)),JSON.stringify(complete));

const edited = {...base[2],undoState:'UNDONE'};
rows = d.upsert(rows,edited);
const updated = d.overlay(base,rows,500);
assert.equal(updated[3].id,base[2].id);
assert.equal(updated[3].undoState,'UNDONE');
assert.equal(updated[0].id,'op-501');

// Large unchanged records retain their exact JSON without being encoded again.
// A replacement object with the same ID must never replay stale evidence.
const heavy = {...make(600), before:{payload:'x'.repeat(512 * 1024)}};
const firstCache = d.encodeSidecarCached(0,[heavy],[]);
assert.equal(firstCache.reusedCount,0);
assert.equal(firstCache.text,d.encodeSidecar(0,[heavy]));
const nextRow = {...make(601), after:{payload:'y'.repeat(256 * 1024)}};
const appended = d.encodeSidecarCached(0,[heavy,nextRow],firstCache.cache);
assert.equal(appended.reusedCount,1);
assert.equal(appended.text,d.encodeSidecar(0,[heavy,nextRow]));
const changed = {...nextRow,status:'FAILED',detail:'new evidence'};
const updatedCache = d.encodeSidecarCached(0,[heavy,changed],appended.cache);
assert.equal(updatedCache.reusedCount,1);
assert.equal(JSON.parse(updatedCache.text).records[1].detail,'new evidence');
assert.equal(updatedCache.text,d.encodeSidecar(0,[heavy,changed]));
const coldCache = d.encodeSidecarCached(
    0,[JSON.parse(JSON.stringify(heavy)),changed],updatedCache.cache
);
assert.equal(coldCache.reusedCount,1,'changed row remains reusable by identity');
assert.equal(coldCache.text,updatedCache.text);
assert.throws(()=>d.encodeSidecarCached(-1,[heavy],firstCache.cache));
assert.throws(()=>d.encodeSidecarCached(0,[{id:''}],firstCache.cache));

// Crash A: sidecar written but checkpoint not committed yet.
const sidecar = d.encodeSidecar(0,rows);
const oldView=d.overlay(base,d.readSidecar(sidecar,0).rows,500);
assert.deepEqual(JSON.parse(JSON.stringify(oldView)),JSON.parse(JSON.stringify(updated)));

// Crash B: newer checkpoint committed but sidecar clear not committed.
const newBase=JSON.parse(JSON.stringify({checkpointGeneration:1,entries:updated}));
const stale=d.readSidecar(sidecar,newBase.checkpointGeneration);
assert.equal(stale.stale,true);
const afterCrash=d.overlay(newBase.entries,stale.rows,500);
assert.equal(JSON.stringify(afterCrash),JSON.stringify(updated));
assert.equal(afterCrash.some(x=>x.id==='op-1'),false);

// Crash C: cleared sidecar matches new checkpoint.
const clean=d.readSidecar(d.encodeSidecar(1,[]),1);
assert.equal(clean.rows.length,0);
assert.equal(clean.stale,false);

// Fail-closed invalid formats, generations and duplicates.
for (const [raw,gen] of [
    ['{bad',0],['{"deltaVersion":9,"records":[]}',0],
    [d.encodeSidecar(4,[]),1],
    ['{"deltaVersion":1,"baseGeneration":0,"records":[{"id":"same"},{"id":"same"}]}',0]
]) {
    assert.throws(()=>d.readSidecar(raw,gen));
}
assert.throws(()=>d.overlay(base,[{id:''}],500));
assert.equal(d.readSidecar('',0).present,false);
console.log('Git delta overlay migration and crash-window synthetic: PASS');
"""
run = subprocess.run(['node','-e',js],cwd=ROOT,capture_output=True,text=True,timeout=30)
assert run.returncode == 0, run.stdout + "\n" + run.stderr
print(run.stdout.strip())
