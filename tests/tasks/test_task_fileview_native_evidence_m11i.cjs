#!/usr/bin/env node
"use strict";
// M11i pure in-memory event chronology. Does not instantiate Quickshell.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const path="services/projects/TaskFileViewNativeEvidenceM11i.js";
const source=fs.readFileSync(path,"utf8").replace(/^\.pragma library\s*$/m,"");
const state=vm.createContext({Array,JSON,Math,Number,Object,String});
vm.runInContext(source,state,{filename:path});
const tags=["ATTACH_REQUEST","HOST_HELLO","FILE_INITIAL_LOAD",
    "STAGE_REQUEST","HOST_ADMIT","FILE_SAVED","FILE_READBACK_OK",
    "HOST_SETTLED","FREEZE_REQUEST","HOST_FROZEN","HOST_EXIT",
    "RECOVERY_REVIEW"];
function trace(events) {
    let t=state.empty();
    for(const item of events)
        t=state.append(t,item,"JSON_ACTIVE");
    return t;
}
function review(seq) {return state.summarize(trace(seq));}
let correct=trace(tags);
assert.equal(correct.sequence,tags.length);
assert.equal(correct.events.length,tags.length);
assert.equal(correct.events[0].seq,1);
assert.equal(correct.events[0].tag,"ATTACH_REQUEST");
assert.equal(correct.events[0].phase,"JSON_ACTIVE");
const summary=state.summarize(correct);
assert.equal(summary.saveChains,1);
assert.equal(summary.chainObserved,true);
assert.equal(summary.frozen,true);
assert.equal(summary.recoveryObserved,true);
assert.equal(summary.label,"OBSERVATION_ONLY_NOT_NATIVE_ACCEPTED");
assert.equal(summary.lastEvent,"RECOVERY_REVIEW");
assert.equal(state.recent(correct,2),"11:HOST_EXIT  12:RECOVERY_REVIEW");
for(const events of [
    ["STAGE_REQUEST","HOST_ADMIT","FILE_READBACK_OK","HOST_SETTLED"],
    ["STAGE_REQUEST","HOST_ADMIT","FILE_SAVED","HOST_SETTLED"],
    ["STAGE_REQUEST","HOST_ADMIT","FILE_SAVED","HOST_EXIT",
     "FILE_READBACK_OK","HOST_SETTLED"],
    ["STAGE_REQUEST","HOST_ADMIT","FILE_SAVE_FAILURE",
     "FILE_SAVED","FILE_READBACK_OK","HOST_SETTLED"],
    ["STAGE_REQUEST","HOST_ADMIT","FILE_SAVED",
     "FILE_READBACK_MISMATCH","FILE_READBACK_OK","HOST_SETTLED"]
]) {
    const observed=review(events);
    assert.equal(observed.saveChains,0,events.join("/"));
    assert.equal(observed.chainObserved,false);
}
const orderIndependent=review(["FILE_INITIAL_LOAD","HOST_HELLO",
    "STAGE_REQUEST","HOST_ADMIT","FILE_SAVED",
    "FILE_READBACK_OK","HOST_SETTLED"]);
assert.equal(orderIndependent.saveChains,1);
let multiple=review(["STAGE_REQUEST","HOST_ADMIT","FILE_SAVED",
    "FILE_READBACK_OK","HOST_SETTLED",
    "STAGE_REQUEST","HOST_ADMIT","FILE_SAVED",
    "FILE_READBACK_OK","HOST_SETTLED"]);
assert.equal(multiple.saveChains,2);
assert.equal(multiple.recoveryObserved,false);

let trimmed=state.empty();
for(let i=0;i<110;i++)
    trimmed=state.append(trimmed,"FILE_INITIAL_LOAD","JSON_ACTIVE");
assert.equal(trimmed.sequence,110);
assert.equal(trimmed.events.length,state.LIMIT);
assert.equal(trimmed.dropped,110-state.LIMIT);
assert.equal(trimmed.events[0].seq,110-state.LIMIT+1);
assert.equal(state.recent(trimmed,4).split("  ").length,4);
const stale=state.append(trimmed,"PRIVATE_FILE_PATH_SECRET","JSON_ACTIVE");
assert.equal(stale,trimmed);
const sanitized=state.append(trimmed,"HOST_HELLO","/home/person/private");
assert.equal(sanitized.events[sanitized.events.length-1].phase,"UNKNOWN");
assert.ok(!JSON.stringify(sanitized).includes("/home"));
assert.equal(state.summarize(null).label,"NO_EVIDENCE");
assert.equal(state.recent(null,4),"NONE");
assert.equal(state.empty().events.length,0);
console.log("M11i bounded privacy-safe native callback chronology and no false acceptance: PASS");
