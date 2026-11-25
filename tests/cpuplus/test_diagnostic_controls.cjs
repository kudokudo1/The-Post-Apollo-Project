const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "../..");
const read = name => fs.readFileSync(path.join(root, name), "utf8");
const policy = vm.createContext({});
vm.runInContext(read("services/diagnostics/CpuPlusDiagnosticsPolicy.js"), policy);
const args = kind => JSON.parse(JSON.stringify(policy.argumentsFor(kind, p => "/local/" + p)));
assert.equal(args("arbitrary"), null);
assert.deepEqual(args("memory").slice(-4), ["--duration", "120", "--interval", "10"]);
assert.equal(args("inventory").at(-1), "/local/scripts/cpuplus_qml_workload_inventory.py");
assert.deepEqual(args("threads").slice(-6), ["--duration", "30", "--interval", "1", "--top", "4"]);
for (const kind of ["memory", "inventory", "threads", "census"]) {
    assert.equal(args(kind)[0], "/usr/bin/timeout");
    assert.ok(args(kind).includes("/usr/bin/python3"));
}
const jsonl = rows => rows.map(row => JSON.stringify(row)).join("\n");
const first = {event:"memory",pid:12,startTicks:99,memoryKiB:{Pss:1048576,SwapPss:0},cpuPct:null};
const second = {...first,memoryKiB:{Pss:2097152,SwapPss:1048576},cpuPct:45};
const done = {event:"complete",pid:12,startTicks:99};
assert.match(policy.summarize("memory",jsonl([first,second,done])), /1.00 \/ 2.00 \/ 2.00 GiB/);
assert.equal(policy.summarize("memory",jsonl([first,second])), null);
assert.equal(policy.summarize("memory",jsonl([first,{...second,startTicks:100},done])), null);
assert.equal(policy.summarize("memory",jsonl([first,{...second,pid:13},done])), null);
assert.equal(policy.summarize("memory",jsonl([first,{event:"stopped"},done])), null);
assert.match(policy.summarize("threads",jsonl([{event:"threads",pid:12,totalCpuPct:89},done])), /89.0%/);
const inventory = {schema:"post-apollo-qml-workload-inventory-v1",scannedQml:826,trackedQml:826,skipped:[],totals:{Timer:426,Process:415,Repeater:743}};
assert.match(policy.summarize("inventory",JSON.stringify(inventory)), /826 files/);
assert.equal(policy.summarize("inventory",JSON.stringify({...inventory,skipped:["missing.qml"]})), null);
assert.equal(policy.summarize("inventory","malformed"), null);
const owner = read("services/diagnostics/CpuPlusDiagnostics.qml");
const ui = read("widgets/cpuplus/CpuPlusDiagnosticsPane.qml");
const parent = read("widgets/cpuplus/CpuPlusMemoryActuatorPane.qml");
assert.match(owner,/pragma Singleton/);
assert.match(owner,/if \(busy \|\| faulted \|\| worker.running \|\| archive.busy\) return false/);
assert.match(owner,/if \(!busy \|\| !received \|\| !exited\) return/);
assert.match(owner,/worker\.exec\(args\)/);
assert.match(owner,/maximumReport: 65536/);
assert.doesNotMatch(owner,/Component.onCompleted|repeat:\s*true|running:\s*true|pkexec|sudo/);
assert.match(ui,/onLeftClicked:\s*\{\s*if \(CpuPlusDiagnostics.request\(modelData.kind\)\)/);
assert.match(ui,/reportText.copy\(\)/);
assert.match(parent,/active: root.page === "DIAG"\s+visible: active\s+sourceComponent: CpuPlusDiagnosticsPane/);
assert.doesNotMatch(ui,/Process\s*\{|Timer\s*\{/);
console.log("CPU++ on-demand diagnostics policy and integration contracts PASS");

assert.deepEqual(args("census").slice(-4), ["--duration","30","--interval","10"]);
const censusRow = {pid:12,name:"quickshell",rssKiB:1048576,cpuPct:90,readBps:null,writeBps:2048};
const sample = {schema:"post-apollo-process-census-v1",event:"census",sequence:1,scope:"same-user",
    observed:1,cpuMeasured:1,ioMeasured:0,coverage:{truncated:false},previousCoverage:{truncated:false},rows:[censusRow]};
const end = {schema:sample.schema,event:"complete",samples:1};
assert.match(policy.summarize("census",jsonl([sample,end])), /TOP CPU \/\/ quickshell #12 90.0%/);
assert.equal(policy.summarize("census",jsonl([sample])),null);
assert.equal(policy.summarize("census",jsonl([sample,{...end,samples:2}])),null);
assert.equal(policy.summarize("census",jsonl([{...sample,sequence:2},end])),null);
assert.equal(policy.summarize("census",jsonl([{...sample,rows:[{...censusRow,writeBps:-1}]},end])),null);
assert.match(policy.summarize("census",jsonl([{...sample,coverage:{truncated:true}},end])), /SCAN LIMIT REACHED/);
assert.match(ui,/PROCESS CENSUS \/\/ 30s/);

const archived = {kind:"memory",id:"session-abc-def-1",status:"COMPLETE",summary:"summary",text:"raw",finishedAt:"2026-11-24T12:00:00.000Z"};
const document = {schema:"post-apollo-diagnostic-archive-v1",rows:[archived],savedId:archived.id};
assert.equal(policy.archiveResponse(document,{action:"save",record:archived})[0],archived);
assert.equal(policy.archiveResponse(document,{action:"save",record:{...archived,text:"other"}}),null);
assert.equal(policy.archiveResponse({...document,rows:[archived,archived]},{action:"save",record:archived}),null);
assert.equal(policy.archiveResponse(document,{action:"list"}),null);
assert.equal(policy.archiveResponse({...document,savedId:null},{action:"list"}).length,1);
assert.equal(policy.archiveResponse({...document,rows:Array(9).fill(archived)},{action:"save",record:archived}),null);
assert.match(owner,/archive.invoke\(\{action: "save", record:/);
assert.match(ui,/LOAD HISTORY/);
const archive = read("services/diagnostics/DiagnosticReportArchive.qml");
assert.match(archive,/stdinEnabled: true/);
assert.match(archive,/worker.write\(store.frame\)/);
assert.doesNotMatch(archive,/Component.onCompleted|repeat:\s*true|running:\s*true|pkexec|sudo/);

const storageIds = ["notifications.history","notifications.favorites","notifications.policies","notifications.scroll",
    "weather.cache","weather.history","weather.events","weather.places","weather.dossier",
    "hub.layout","hub.notes","hub.todo","social.identities","git.journal","git.delta",
    "forest.preferences","finance.manual","company.hubs"];
const storageSample = {schema:"post-apollo-storage-observation-v1",event:"storage",sequence:1,
    intervals:10,elapsedMs:10000,rows:storageIds.map(id=>({id,initialState:"present",finalState:"present",
        initialBytes:100,finalBytes:100,changedIntervals:0,replacementIntervals:0,
        unavailableIntervals:0,comparableIntervals:10}))};
storageSample.rows[0].changedIntervals=3;
const storageEnd={schema:storageSample.schema,event:"complete",samples:1};
const storageText=jsonl([storageSample,storageEnd]);
assert.match(policy.summarize("storage",storageText), /notifications.history \/\/ 3 changed intervals/);
assert.equal(policy.summarize("storage",jsonl([storageSample])),null);
assert.equal(policy.summarize("storage",jsonl([{...storageSample,rows:storageSample.rows.slice(1)},storageEnd])),null);
assert.equal(policy.summarize("storage",jsonl([{...storageSample,rows:[{...storageSample.rows[0],changedIntervals:11},...storageSample.rows.slice(1)]},storageEnd])),null);
assert.equal(policy.argumentsFor("storage",p=>"/local/"+p),null);
assert.deepEqual(JSON.parse(JSON.stringify(policy.argumentsFor("storage",p=>"/local/"+p,"/data"))).slice(-6),
    ["--data-dir","/data","--shell-dir","/local/.","--duration","30"]);
assert.match(ui,/STORAGE OBSERVE \/\/ 30s/);
assert.match(read("scripts/cpuplus_diagnostic_archive.py"),/KINDS = \{[^}]*"storage"/);
const comparePolicy=vm.createContext({});
vm.runInContext(read("services/diagnostics/DiagnosticComparison.js"),comparePolicy);
const baseStorage={kind:"storage",id:"session-abc-def-1",status:"COMPLETE",text:storageText,finishedAt:"2026-11-24T12:00:00.000Z"};
const nextStorage={...baseStorage,id:"session-abc-def-2",finishedAt:"2026-11-24T12:01:00.000Z",
    text:jsonl([{...storageSample,rows:[{...storageSample.rows[0],changedIntervals:1},...storageSample.rows.slice(1)]},storageEnd])};
const storageCompare=comparePolicy.compare(baseStorage,nextStorage,policy.summarize);
assert.equal(storageCompare.error,"");
assert.equal(storageCompare.rows.find(r=>r.label==="notifications.history CHANGED INTERVALS").delta,-2);
assert.match(storageCompare.note,/not writes, transactions or writer identity/);

const breakdown=vm.createContext({});
vm.runInContext(ui.slice(ui.indexOf("    function memoryBreakdown("),ui.indexOf("    function comparisonLabel(")),breakdown);
const memorySample={event:"memory",pid:12,startTicks:99,tsMs:1000,cpuTicks:100,cpuPct:null,sampleIntervalMs:null,
    memoryKiB:{Rss:2097152,Pss:1048576,Pss_Anon:524288,Pss_File:262144,Pss_Shmem:262144,
        Private_Dirty:524288,Swap:131072,SwapPss:65536},pssPlusSwapPssKiB:1114112};
const memoryNext={...memorySample,tsMs:11000,cpuTicks:110,cpuPct:1,sampleIntervalMs:10000,
    memoryKiB:{...memorySample.memoryKiB,Rss:3145728,Pss:1572864,Private_Dirty:1048576},pssPlusSwapPssKiB:1638400};
const memoryReport={status:"COMPLETE",text:jsonl([memorySample,memoryNext,done])};
const result=breakdown.memoryBreakdown("memory",memoryReport);
assert.equal(result.pid,12);
assert.equal(result.durationMs,10000);
assert.equal(result.rows.length,5);
assert.equal(result.rows.find(r=>r.label==="PSS").change,524288);
assert.equal(result.rows.find(r=>r.label==="PRIVATE DIRTY").last,1048576);
assert.equal(result.anon,524288);
assert.equal(breakdown.memoryBreakdown("memory",{...memoryReport,text:jsonl([memorySample,done])}).rows[0].change,null);
for(const invalid of [
    {...memoryReport,status:"CANCELLED"},
    {...memoryReport,text:jsonl([memorySample,memoryNext])},
    {...memoryReport,text:jsonl([memorySample,{...memoryNext,pid:13},done])},
    {...memoryReport,text:jsonl([memorySample,{...memoryNext,startTicks:100},done])},
    {...memoryReport,text:jsonl([memorySample,{...memoryNext,memoryKiB:{Pss:1}},done])},
    {...memoryReport,text:jsonl([memorySample,{...memoryNext,sampleIntervalMs:0},done])},
    {...memoryReport,text:jsonl([memorySample,{...memoryNext,pssPlusSwapPssKiB:1},done])},
    {...memoryReport,text:jsonl([memorySample,{event:"stopped"},done])},
    {...memoryReport,text:"x".repeat(65537)}
]) assert.equal(breakdown.memoryBreakdown("memory",invalid),null);
assert.equal(breakdown.memoryBreakdown("inventory",memoryReport),null);
assert.match(ui,/objectName: "cpuplusMemoryBreakdown"/);
assert.match(ui,/HISTORICAL CAPTURE \/\/ NOT LIVE/);
assert.match(ui,/Private dirty is not total private memory/);
console.log("CPU++ completed memory capture presentation PASS");

const extendedFirst={...memorySample,memoryKiB:{...memorySample.memoryKiB,Private_Clean:262144},privateResidentKiB:786432};
const extendedNext={...memoryNext,memoryKiB:{...memoryNext.memoryKiB,Private_Clean:524288},privateResidentKiB:1572864};
const extendedReport={...memoryReport,text:jsonl([extendedFirst,extendedNext,done])};
const extended=breakdown.memoryBreakdown("memory",extendedReport,true);
assert.equal(extended.privateResidentAvailable,true);
assert.equal(extended.rows.length,7);
assert.equal(extended.rows.find(r=>r.label==="PRIVATE RESIDENT").change,786432);
assert.equal(extended.rows.find(r=>r.label==="PRIVATE CLEAN").last,524288);
const legacy=breakdown.memoryBreakdown("memory",memoryReport,true);
assert.equal(legacy.privateResidentAvailable,false);
assert.equal(legacy.rows.length,5);
assert.deepEqual(JSON.parse(JSON.stringify(breakdown.memoryBreakdown("memory",extendedReport))),
    JSON.parse(JSON.stringify(result)));
for (const row of [
    {...extendedNext,privateResidentKiB:1},
    {...extendedNext,memoryKiB:{...extendedNext.memoryKiB,Private_Clean:-1}},
    {...extendedNext,memoryKiB:{...extendedNext.memoryKiB,Private_Clean:4194304},privateResidentKiB:5242880},
    memoryNext
]) assert.equal(breakdown.memoryBreakdown("memory",{...memoryReport,text:jsonl([extendedFirst,row,done])},true),null);
assert.equal(breakdown.memoryBreakdown("memory",{...memoryReport,text:jsonl([extendedFirst,done])},true)
    .rows.find(r=>r.label==="PRIVATE RESIDENT").change,null);
assert.match(ui,/memoryBreakdown\(selectedReport, report, true, true\)/);
console.log("CPU++ private resident capture presentation PASS");

const hostA={MemTotal:33554432,MemAvailable:8388608,MemFree:1024,AnonPages:1024,Cached:1024,Shmem:0,SReclaimable:0,SUnreclaim:0,SwapTotal:1024,SwapFree:1024};
const hostB={...hostA,MemAvailable:6291456};
const pairedFirst={...memorySample,hostObservation:{beforeKiB:hostA,afterKiB:hostA,spanMs:2}};
const pairedNext={...memoryNext,hostObservation:{beforeKiB:hostA,afterKiB:hostB,spanMs:3}};
const hostView=rows=>breakdown.memoryBreakdown("memory",{status:"COMPLETE",text:jsonl([...rows,done])},true,true);
const h=hostView([pairedFirst,pairedNext]).hostContext;
assert.equal(h.paired,2);assert.equal(h.minimum,6291456);assert.equal(h.maxSpan,3);
assert.equal(h.total,33554432);assert.equal(h.start,8388608);assert.equal(h.final,6291456);
assert.equal(h.delta,-2097152);assert.equal(h.pssDelta,524288);
for(const value of [null,{...pairedNext.hostObservation,spanMs:-1},{...pairedNext.hostObservation,afterKiB:{...hostB,MemAvailable:999999999}}]){
    const v=hostView([pairedFirst,{...pairedNext,hostObservation:value}]);
    assert.equal(v.rows.length,5);assert.equal(v.hostContext.paired,1);
    assert.equal(v.hostContext.delta,null);assert.equal(v.hostContext.pssDelta,null);
}
const changed=hostView([pairedFirst,{...pairedNext,hostObservation:{beforeKiB:{...hostA,MemTotal:67108864},afterKiB:{...hostB,MemTotal:67108864},spanMs:3}}]).hostContext;
assert.equal(changed.paired,2);assert.equal(changed.complete,false);assert.equal(changed.total,null);
assert.equal(hostView([memorySample,memoryNext]).hostContext.minimum,null);
assert.equal(hostView([pairedFirst]).hostContext.delta,null);
assert.match(ui,/objectName: "cpuplusDiagHostInstrument"/);
assert.match(ui,/OBSERVED SAMPLES ONLY \/\/ CORRELATION, NOT CAUSE/);
console.log("CPU++ M10 host RAM instrument projection PASS");
