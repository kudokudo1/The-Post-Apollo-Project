const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "../..");
const read = p => fs.readFileSync(path.join(root,p),"utf8");
const policy = vm.createContext({});
const comp = vm.createContext({});
vm.runInContext(read("services/diagnostics/CpuPlusDiagnosticsPolicy.js"),policy);
vm.runInContext(read("services/diagnostics/DiagnosticComparison.js"),comp);
const jsonl = rows => rows.map(row => JSON.stringify(row)).join("\n");
const beforeId = "session-abc-def-1", afterId = "session-abc-def-2";
const report = (kind, data, after=false) => ({kind,status:"COMPLETE",
    id:after?afterId:beforeId,finishedAt:after?"2026-11-24T12:30:00.000Z":"2026-11-24T12:00:00.000Z",
    text:typeof data==="string"?data:jsonl(data)});
const sample = (pss,ms,cpu,pid=12) => ({event:"memory",pid,startTicks:99,
    memoryKiB:{Pss:pss,SwapPss:0},sampleIntervalMs:ms,cpuPct:cpu});
const end = {event:"complete",pid:12,startTicks:99};
const original = report("memory",[sample(1048576,null,null),sample(2097152,10000,80),
    sample(1048576,20000,20),end]);
const patched = report("memory",[sample(1048576,null,null),sample(1048576,10000,30),
    sample(1048576,20000,30),end],true);
const compare = (a,b) => comp.compare(a,b,policy.summarize);
const get = (result,label) => result.rows.find(row=>row.label===label);
let result = compare(original,patched);
assert.equal(result.error,"");
assert.equal(get(result,"CPU MEAN").before,40);
assert.equal(get(result,"CPU MEAN").delta,-10);
assert.equal(get(result,"PSS MEAN (EST.)").before,1.5);
assert.equal(get(result,"PSS PEAK").delta,-1);
assert.equal(get(result,"PSS FINAL").delta,0);
assert.equal(get(result,"OBSERVED TIME").before,30);
assert.match(result.note,/Observed differences only/);
assert.match(compare(original,original).error,/DIFFERENT/);
assert.match(compare(patched,original).error,/NEWER/);
assert.match(compare(original,{...patched,kind:"threads"}).error,/TYPES/);
assert.match(compare(original,{...patched,status:"CANCELLED"}).error,/COMPLETED/);
assert.match(compare(original,null).error,/SELECT TWO/);
assert.match(compare(original,report("memory",[sample(1048576,null,null),sample(1048576,0,1),end],true)).error,/EVIDENCE/);
assert.match(compare(original,report("memory",[sample(1048576,null,null),sample(1048576,10000,1,99),end],true)).error,/EVIDENCE/);
assert.match(compare(original,report("memory",[sample(1048576,null,null),sample(1048576,10000,1),end],true)).note,/UNEQUAL DURATIONS/);
// RSS/PSS may fall while proportional swapped footprint grows.
const swapSample = (pss,swap,ms,cpu,priv) => {
    const r = sample(pss,ms,cpu);
    r.memoryKiB.SwapPss = swap;
    if (priv !== undefined) {
        r.memoryKiB.Rss = 4000000;
        r.memoryKiB.Private_Clean = 100;
        r.memoryKiB.Private_Dirty = priv-100;
        r.privateResidentKiB = priv;
    }
    return r;
};
const oldCapture = report("memory",[swapSample(1048576,0,null,null),
    swapSample(524288,786432,10000,10),end]);
const newCapture = report("memory",[swapSample(1048576,0,null,null,524288),
    swapSample(524288,786432,10000,10,786432),end],true);
result = compare(oldCapture,newCapture);
assert.equal(result.error,"");
assert.equal(get(result,"PSS NET CHANGE").after,-512);
assert.equal(get(result,"PSS + SWAP PSS NET CHANGE").after,256);
assert.equal(get(result,"PRIVATE RESIDENT NET CHANGE").before,null);
assert.equal(get(result,"PRIVATE RESIDENT NET CHANGE").after,256);
assert.equal(get(result,"PRIVATE RESIDENT NET CHANGE").delta,null);
assert.match(result.note,/boot identity and continuity/);
const otherProcess = report("memory",[{...swapSample(1048576,0,null,null,524288),pid:13},
    {...swapSample(524288,786432,10000,10,786432),pid:13},
    {...end,pid:13}],true);
assert.match(compare(oldCapture,otherProcess).note,/PROCESS IDENTITY CHANGED/);
const partial = report("memory",[swapSample(1048576,0,null,null),
    swapSample(524288,786432,10000,10,786432),end],true);
assert.equal(get(compare(oldCapture,partial),"PRIVATE RESIDENT FINAL").after,null);
const invalidPrivate = swapSample(524288,786432,10000,10,786432);
invalidPrivate.privateResidentKiB++;
assert.match(compare(oldCapture,report("memory",[swapSample(1048576,0,null,null,524288),
    invalidPrivate,end],true)).error,/EVIDENCE/);
assert.equal(get(compare({...newCapture,id:beforeId,finishedAt:original.finishedAt},newCapture),
    "PRIVATE RESIDENT NET CHANGE").delta,0);
const inventory = {schema:"post-apollo-qml-workload-inventory-v1",scannedQml:826,trackedQml:826,skipped:[],
    totals:{Timer:426,Process:415,Repeater:743}};
result = compare(report("inventory",JSON.stringify(inventory)),report("inventory",JSON.stringify({...inventory,totals:{...inventory.totals,Timer:420}}),true));
assert.equal(get(result,"TIMER MARKERS").delta,-6);
assert.match(result.note,/not running objects/);
const thread = (cpu,main,ms=1000) => ({event:"threads",pid:12,totalCpuPct:cpu,sampleIntervalMs:ms,
    threadCount:10,main:main===null?null:{tid:12,cpuPct:main}});
result = compare(report("threads",[{event:"start",pid:12},thread(100,80),thread(50,40,3000),end]),
    report("threads",[{event:"start",pid:12},thread(40,null),thread(40,20,3000),end],true));
assert.equal(get(result,"THREAD CPU MEAN").before,62.5);
assert.equal(get(result,"MAIN CPU MEAN").delta,null);
const census = {schema:"post-apollo-process-census-v1",event:"census",sequence:1,scope:"same-user",
    observed:2,cpuMeasured:2,ioMeasured:1,coverage:{truncated:false},previousCoverage:{truncated:false},
    rows:[{pid:12,name:"quickshell",rssKiB:1048576,cpuPct:90,readBps:null,writeBps:2048}]};
const censusEnd = {schema:census.schema,event:"complete",samples:1};
result = compare(report("census",[census,censusEnd]),report("census",[{...census,rows:[{...census.rows[0],cpuPct:40}]},censusEnd],true));
assert.equal(get(result,"QS CPU (FINAL)").delta,-50);
assert.equal(get(result,"QS READ (FINAL)").delta,null);
assert.match(result.note,/RSS is not PSS/);
result = compare(report("census",[census,censusEnd]),report("census",[{...census,rows:[...census.rows,{...census.rows[0],pid:13}]},censusEnd],true));
assert.equal(get(result,"QS RSS (FINAL)").after,null);
assert.match(compare(report("census",[census,censusEnd]),report("census",[{...census,coverage:{truncated:true}},censusEnd],true)).error,/EVIDENCE/);
const owner = read("services/diagnostics/CpuPlusDiagnostics.qml");
const methods = owner.slice(owner.indexOf("    function selectComparison("),owner.indexOf("    readonly property var archiveRows"));
const state = vm.createContext({archiveBusy:false,archiveStatus:"READY",archiveRows:[original,patched],compareBeforeId:"",compareAfterId:""});
vm.runInContext(methods,state);
assert.equal(state.selectComparison("before",beforeId),true);
assert.equal(state.selectComparison("after",afterId),true);
assert.equal(state.compareBeforeId,beforeId);
assert.equal(state.compareAfterId,afterId);
assert.equal(state.selectComparison("before","evicted"),false);
assert.equal(state.selectComparison("bogus",afterId),false);
state.archiveBusy=true;
assert.equal(state.selectComparison("before",afterId),false);
const ui = read("widgets/cpuplus/CpuPlusDiagnosticsPane.qml");
assert.match(ui,/showComparison \? Compare.compare\(beforeRecord, afterRecord, Policy.summarize\) : null/);
assert.match(ui,/archiveRows.find\(row => row.id === CpuPlusDiagnostics.compareBeforeId\)/);
assert.match(ui,/archiveRows.find\(row => row.id === CpuPlusDiagnostics.compareAfterId\)/);
assert.doesNotMatch(ui,/Process\s*\{|Timer\s*\{/);
console.log("Diagnostic comparison arithmetic, identity, coverage and UI contracts PASS");
