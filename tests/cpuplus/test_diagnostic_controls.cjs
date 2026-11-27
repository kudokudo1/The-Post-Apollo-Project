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
assert.match(owner,/if \(busy \|\| faulted \|\| worker.running \|\| archive.busy \|\| \(setActive && !setDispatching\)\) return false/);
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
assert.match(ui,/RELOAD ARCHIVE/);
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

// Runtime capture, fixed parent sampler and stable mode interval projection.
assert.deepEqual(args("appcontrol").slice(-7),["--parent-quickshell","--duration","30","--interval","1","--top","4"]);
const acModes=[{tsMs:1000,mode:"closed"},{tsMs:2000,mode:"app"},{tsMs:3500,mode:"kill"}];
const acStages=["graph-invalidation","mode-restore","selection","probe-schedule","refresh-dispatch","focus","handler-total"];
const acOpen=acStages.map((stage,i)=>({stage,sequence:1,tsMs:2100+i,elapsedMs:i===6?6:1}));
const acRows=[{event:"start",pid:123,tsMs:1000,durationSeconds:30},
    ...[2000,3000,4000,5000].map((tsMs,i)=>({event:"threads",pid:123,tsMs,sampleIntervalMs:1000,totalCpuPct:50+i*10,main:{tid:123,cpuPct:25+i*5}})),
    {event:"complete",pid:123,tsMs:5000}];
const ac=policy.combineAppControl(jsonl(acRows),acModes,acOpen,false);
assert.ok(ac);
const acMetrics=policy.appControlMetrics(ac);
assert.equal(acMetrics.all.count,4);
assert.equal(acMetrics.app.count,1);
assert.equal(acMetrics.kill.count,1);
assert.equal(acMetrics.openings,1);
assert.match(policy.summarize("appcontrol",ac),/OPENINGS \/\/ 1/);
assert.equal(policy.combineAppControl(jsonl(acRows),acModes,acOpen,true),null);
assert.equal(policy.combineAppControl(jsonl(acRows.slice(0,-1)),acModes,acOpen,false),null);
assert.equal(policy.combineAppControl(jsonl(acRows.map((row,i)=>i===1?{...row,pid:124}:row)),acModes,acOpen,false),null);
assert.match(ui,/APPCONTROL \/\/ TEST 30s/);
assert.match(owner,/appControlCaptureActive: busy && kind === "appcontrol"/);
assert.match(read("shell.qml"),/diagnosticCaptureActive: CpuPlusDiagnostics.appControlCaptureActive/);
const acReport={kind:"appcontrol",id:"session-abc-def-1",status:"COMPLETE",text:ac,finishedAt:"2026-11-24T12:00:00.000Z"};
const acComp=comparePolicy.compare(acReport,{...acReport,id:"session-abc-def-2",finishedAt:"2026-11-24T12:01:00.000Z"},policy.summarize,policy.appControlMetrics);
assert.equal(acComp.error,"");
assert.equal(acComp.rows.find(row=>row.label==="KILL TOTAL CPU").delta,0);

const detailedOpen = [
    {stage:"graph-invalidation",sequence:1,tsMs:2101,elapsedMs:1},
    {stage:"mode-restore",sequence:1,tsMs:2102,elapsedMs:1},
    {stage:"selection-state",sequence:1,tsMs:2103,elapsedMs:1},
    {stage:"selection-row",sequence:1,tsMs:2203,elapsedMs:100},
    {stage:"selection-detail",sequence:1,tsMs:2204,elapsedMs:1},
    {stage:"selection",sequence:1,tsMs:2204,elapsedMs:102},
    {stage:"probe-schedule",sequence:1,tsMs:2205,elapsedMs:1},
    {stage:"refresh-dispatch",sequence:1,tsMs:2206,elapsedMs:1},
    {stage:"focus",sequence:1,tsMs:2207,elapsedMs:1},
    {stage:"handler-total",sequence:1,tsMs:2207,elapsedMs:107}
];
const work=[{stage:"task-rows",tsMs:3900,elapsedMs:35},{stage:"task-rows",tsMs:4400,elapsedMs:15},
    {stage:"mini-history-revisions",tsMs:4500,elapsedMs:7},{stage:"task-rows",tsMs:5001,elapsedMs:1}];
const detailed=policy.combineAppControl(jsonl(acRows),acModes,detailedOpen,false,work);
assert.ok(detailed);
const dm=policy.appControlMetrics(detailed);
assert.equal(dm.openings,1);
assert.equal(dm.selection["selection-row"][0],100);
assert.equal(dm.killWork["task-rows"].count,2);
assert.equal(dm.killWork["task-rows"].totalMs,50);
assert.equal(dm.killWork["task-rows"].maxMs,35);
assert.match(policy.summarize("appcontrol",detailed),/SELECTION-ROW \/\/ mean 100.0 ms/);
assert.equal(policy.combineAppControl(jsonl(acRows),acModes,detailedOpen,false,[{stage:"unknown",tsMs:3900,elapsedMs:1}]),null);
assert.equal(policy.combineAppControl(jsonl(acRows),acModes,[...detailedOpen].reverse(),false,work),null);
assert.equal(policy.appControlMetrics(ac).openings,1);
assert.deepEqual(JSON.parse(JSON.stringify(policy.appControlMetrics(ac).killWork)),{});


const moreWork=[{stage:"app-model-read",mode:"closed",tsMs:2100,elapsedMs:80},
    {stage:"app-index-write",mode:"app",tsMs:2200,elapsedMs:100},
    {stage:"task-rows",mode:"app",tsMs:2300,elapsedMs:60},
    {stage:"event-loop-gap",mode:"app",tsMs:2900,elapsedMs:600},
    {stage:"event-loop-gap",mode:"kill",tsMs:5001,elapsedMs:400}];
const more=policy.combineAppControl(jsonl(acRows),acModes,detailedOpen,false,work,moreWork);
assert.ok(more);
const moreMetrics=policy.appControlMetrics(more);
assert.equal(moreMetrics.work["closed / app-model-read"].maxMs,80);
assert.equal(moreMetrics.work["app / event-loop-gap"].totalMs,600);
assert.equal(moreMetrics.work["kill / event-loop-gap"],undefined);
assert.equal(moreMetrics.killWork["task-rows"].totalMs,50);
assert.equal(policy.combineAppControl(jsonl(acRows),acModes,detailedOpen,false,work,[{...moreWork[0],mode:"unknown"}]),null);
assert.equal(policy.combineAppControl(jsonl(acRows),acModes,detailedOpen,false,work,Array(257).fill(moreWork[0])),null);
assert.deepEqual(JSON.parse(JSON.stringify(policy.appControlMetrics(ac).work)),{});
assert.match(policy.summarize("appcontrol",more),/APP \/ EVENT-LOOP-GAP/);

const workshop=read("widgets/cpuplus/CpuPlusDiagnosticWorkshop.qml");
const workshopSlider=read("widgets/cpuplus/CpuPlusDiagnosticSlider.qml");
const executionFace=read("widgets/cpuplus/CpuPlusDiagnosticExecutionButton.qml");
assert.match(ui,/sourceComponent: CpuPlusDiagnosticWorkshop\s*\{/);
assert.match(workshopSlider,/SelectorSlider\s*\{/);
assert.match(workshopSlider,/rotation: 90/);
assert.match(workshopSlider,/horizontalStepPresentation: true/);
assert.match(workshopSlider,/property color subjectColor: Colors.white/);
assert.match(workshopSlider,/property color fillColor: Colors.omnitrix/);
assert.match(workshop,/SelectorDial\s*\{/);
assert.match(workshop,/markerColor: Colors.orange/);
assert.match(workshop,/Colors.resourceColor\(modelData.subject\)/);
assert.match(workshop,/if \(ready\) \{[\s\S]*?requestWorkshopCapture\(frozen\)/);
assert.match(workshop,/onPlanTextChanged: disarm\(\)/);
assert.match(workshop,/running: root.visible && root.recording && !CpuPlusDiagnostics.cancelled/);
assert.match(executionFace,/phase === "COMPLETE" \? Colors.omnitrix/);
assert.match(owner,/property var workshopDraft:/);
assert.doesNotMatch(workshop,/Process\s*\{|Component.onCompleted/);
console.log("DIAG D3a canonical Workshop instrument and explicit activation contracts PASS");

assert.match(ui,/property string viewMode: "WORK"/);
assert.match(ui,/id: reportRail\s+visible: root.viewMode === "REPORT"/);
assert.match(ui,/id: compareRail\s+visible: root.viewMode === "COMPARE"/);
assert.match(workshop,/options: \["1","2","3","4","5","6","7","8","9","10","11","12"\]/);
assert.match(workshop,/numericDetentInterval: 1/);
assert.match(workshop,/fillColor: Colors.cyan/);
assert.match(workshop,/fillColor: Colors.magenta/);
assert.match(workshop,/fillColor: Colors.orange/);
assert.match(workshop,/normalFace: true/);
console.log("DIAG D3b compact Workshop and contextual controls PASS");

assert.match(workshop,/readoutColor: Colors.cyan/);
assert.match(workshop,/interactionGlowColor: Colors.magenta/);
assert.match(workshop,/objectName: "cpuplusWorkshopStorageInstrument"/);
assert.match(ui,/normalFace: true/);
assert.doesNotMatch(workshop,/text: "FIXED CADENCE"/);
assert.match(workshop,/storageCadenceExplicit:true/);
assert.match(workshop,/root.changeStorageCadence\(cadenceRow.field,1\)/);
assert.match(workshop,/root.changeStorageCadence\(cadenceRow.field,-1\)/);
assert.match(workshop,/storagePreview.observations/);

assert.match(workshop,/compactLayout: viewportHeight > 0 && viewportHeight < 480/);
assert.match(workshop,/instrumentHeight: compactLayout \? 112 : Math.min\(240,176\+/);
assert.match(workshopSlider,/height: root.compact \? 22 : 32/);
assert.match(workshopSlider,/width: parent.height\s+height: parent.width/);
assert.match(ui,/viewportHeight: root.workshopViewportHeight/);
console.log("DIAG D3c adaptive full-width layout contracts PASS");

assert.match(owner,/stallCaptureActive: busy && \(kind === "stall" \|\| \(kind === "workflow" && workflowStallRequested\)\) && !cancelled && !exited/);
assert.match(owner,/stallTicks.push\(timestampMs\)/);
assert.match(read("shell.qml"),/running: shellRoot.syntagmaLagProbeEnabled \|\| CpuPlusDiagnostics.appControlCaptureActive \|\| CpuPlusDiagnostics.stallCaptureActive/);
assert.match(read("shell.qml"),/CpuPlusDiagnostics.recordStallTick\(now\)/);
assert.match(owner,/Policy.combineStall\(output, stallTicks, JSON.parse\(activeCalibration\)\)/);
console.log("DIAG D3d reuse existing shell heartbeat contract PASS");

assert.match(workshop,/objectName: "cpuplusWorkshopStallThreshold"/);
assert.match(workshop,/numericDetentInterval: 50/);
assert.match(read("services/diagnostics/DiagnosticCalibration.js"),/thresholdMs:d.stallThresholdMs/);
assert.match(workshop,/onValueRequested: value=>root.edit\("stallThresholdMs",Math.round\(value\)\)/);
assert.match(owner,/Policy.attachWorkflowStall\(output,expected,stallTicks,stallOverflow\)/);

assert.doesNotMatch(parent,/diagnosticTopRail/);
assert.match(ui,/objectName: "cpuplusDiagnosticWorkspaceRail"/);
assert.match(ui,/model: \[\{key:"WORK",label:"CONTROLS"\},\{key:"PRESETS",label:"WORKFLOWS"\}\]/);
assert.match(ui,/objectName: "cpuplusDiagnosticWorkflowCatalog"/);
assert.match(ui,/id: diagnosticIndex\s+objectName: "cpuplusDiagnosticContextRail"\s+height: 25/);
assert.match(workshop,/Calibration.workshopPlanFromDraft\(d\)/);
assert.match(owner,/function saveWorkshopPreset\(name\)/);
assert.match(owner,/function loadWorkshopPreset\(name\)/);

assert.match(ui,/model: root.viewMode==="PRESETS" \? \[\{key:"LIBRARY",label:"LIBRARY"\}/);
assert.match(ui,/\{key:"RESULTS",label:"RESULTS"\}/);
assert.match(ui,/objectName: "cpuplusDiagBottomControls"\s+width: parent.width\s+spacing: 3\s+height: 53/);
assert.match(ui,/objectName: "cpuplusDiagnosticReportActions"\s+width: parent.width\s+visible: \["REPORT","HISTORY","COMPARE"\]/);
assert.match(parent,/onNavigationChanged: scroll.contentY=0/);
assert.match(ui,/label: presets.armedQueue!==""\?"CONFIRM RUN":"RUN QUEUE"/);
assert.match(owner,/onArchiveBusyChanged: if\(setActive&&!archiveBusy\) Qt.callLater\(dispatchSetStep\)/);
assert.match(owner,/archiveRows.find\(x=>x.id===setCurrentId&&x.kind===setCurrentKind\)/);
assert.match(owner,/if\(setStopRequested\)\{finishSet\("SET CANCELLED"\);return;\}/);
console.log("DIAG D4b ordered set session contracts PASS");

for(const color of ["cyan","magenta","orange"])assert.ok(workshop.includes("subjectColor: Colors."+color));
assert.match(workshopSlider,/handleColor: root.hardwareFace/);
assert.match(workshopSlider,/font.pixelSize: 12/);
assert.match(workshopSlider,/semanticGlowColor: root.fillColor/);
assert.match(workshop,/idleRingGlowStrength: 0.65/);
assert.match(workshop,/titleColor: accentColor/);
assert.ok(workshop.indexOf('objectName: "cpuplusWorkshopTopThreads"')<workshop.indexOf('objectName: "cpuplusWorkshopStorageInstrument"'));
assert.ok(workshop.indexOf('objectName: "cpuplusWorkshopStorageInstrument"')<workshop.indexOf('objectName: "cpuplusWorkshopStallThreshold"'));
assert.doesNotMatch(workshop,/selected(Foreground|Border|ContentGlow|SoftGlow)Color: accentColor/);

assert.match(workshopSlider,/frameColor: "#FFFFFF"/);
assert.match(workshopSlider,/accentColor: root.subjectColor/);
assert.match(workshop,/activeDetentColor: Colors.magenta/);
assert.match(workshop,/outlinedOptionLabels: true/);
assert.match(workshop,/accentColor: Colors.yellow\s+markerColor: Colors.magenta/);
assert.match(workshop,/objectName: "cpuplusWorkshopStorageContents"/);

assert.match(workshopSlider,/frameGlowColor: root.fillColor/);
assert.match(workshopSlider,/handleGlowColor: root.fillColor/);
assert.match(workshopSlider,/activityGlowColor: root.fillColor/);
assert.match(read("components/SelectorSlider.qml"),/property color frameGlowColor: frameColor/);

assert.match(workshopSlider,/responsiveHardware: true/);
assert.match(workshopSlider,/energizedValueFill: true/);
assert.match(workshop,/parent: root.filterTarget \|\| root/);
assert.match(ui,/filterTarget: root.workshopFilterTarget/);
assert.match(read("components/SelectorSlider.qml"),/property bool responsiveHardware: false/);
assert.match(read("components/SelectorSlider.qml"),/property bool energizedValueFill: false/);

assert.match(workshop,/storageMechanical: !smallestStorageLayout && storageDialWidth>=92/);
assert.match(workshop,/objectName: "cpuplusWorkshopStorage-sample-dial"/);
assert.match(workshop,/objectName: "cpuplusWorkshopStorage-report-dial"/);
assert.doesNotMatch(workshop,/storageDialCell/);
assert.match(workshop,/selectorColor: field==="sample" \? Colors.orange : Colors.magenta/);
assert.match(workshop,/accentColor: Colors.red\s+normalFace: true\s+label: "−"/);
assert.match(workshop,/accentColor: Colors.green\s+normalFace: true\s+label: "\+"/);
assert.match(workshop,/objectName: "cpuplusWorkshopCalibrationStatus"/);
assert.match(read("widgets/cpuplus/CpuPlusMemoryReadout.js"),/\|INT\|RPT\|/);
assert.match(executionFace,/washStrength: 0.24/);
assert.match(executionFace,/idleFillColor: preparationFace \? steadyWashColor : Colors.dark/);
assert.doesNotMatch(executionFace,/model: root.preparationFace/);

const stopwatchDialSource=read("components/SelectorDial.qml");
assert.match(stopwatchDialSource,/property bool stopwatchFace: false/);
assert.match(stopwatchDialSource,/model: dialRoot.stopwatchFace \? 0 : dialRoot.optionCount\(\)/);
assert.match(stopwatchDialSource,/sourceComponent: AutomotiveDial/);
const automotive=read("components/AutomotiveDial.qml"), chassis=read("components/InstrumentChassis.qml");
assert.match(automotive,/objectName: "selectorStopwatchCenter"/);
assert.match(automotive,/Math.max\(65,Math.min\(95,armReach\)\)/);
assert.match(automotive,/property string armStyle: "tapered"/);
assert.match(automotive,/property string gaugeStyle: "segmented"/);
assert.match(automotive,/property string scaleStyle: "ticks"/);
assert.match(chassis,/property real clearance: 10/);
assert.match(chassis,/property string chassisStyle: "square"/);
assert.match(chassis,/faceDiameter \+ 2\*safeClearance/);
assert.ok(automotive.indexOf("selectorStopwatchCenter") < automotive.indexOf("selectorStopwatchHand"));
assert.doesNotMatch(automotive,/\bTimer\s*\{|\bProcess\s*\{/);
assert.doesNotMatch(chassis,/\bTimer\s*\{|\bProcess\s*\{/);
for(const variant of ["industrial","capsule","continuous","dualRail","radialTeeth","sparse","numbers","none"]) assert.ok(automotive.includes(variant));
assert.match(read("components/qmldir"),/AutomotiveDial 1\.0 AutomotiveDial\.qml/);
assert.match(stopwatchDialSource,/stopwatchLitSegments: Math.ceil\(30\*stopwatchVisualFraction\)/);
assert.equal((workshop.match(/stopwatchFace: true/g)||[]).length,2);
assert.equal((workshop.match(/stopwatchFraction: stopwatch \? stopwatch.fraction : -1/g)||[]).length,2);

// Responsive components draw in their allocated pixel geometry, never a shrunk face texture.
assert.doesNotMatch(automotive,/width: 216; height: 216|scale: Math.min\(root.faceDiameter/);
assert.doesNotMatch(workshop,/scale: root.storageDialScale/);
assert.match(automotive,/width: root.actualFaceDiameter; height: width/);
assert.match(automotive,/readonly property string detailTier:/);
assert.match(automotive,/readonly property int unitPixelSize: Math.max\(9,/);
assert.match(automotive,/function cut\(m,k,fill,stroke\)/);
assert.match(chassis,/readonly property real screwSlotWidth: Math.max\(1.5,/);
assert.match(chassis,/function cross\(half,arm,fill\)/);
assert.match(chassis,/cross\(half,arm,metal\(arm,/);
assert.match(stopwatchDialSource,/objectName: "selectorDialReadableValue"/);

// Inset readouts use the actual chamfer vertices and never overlap the numeric text.
assert.match(automotive,/function insetWindowFits\(g\)/);
assert.match(automotive,/readonly property real minimumSegmentGap: 2/);
assert.match(automotive,/root.minimumSegmentGap\/\(inner\*u\)/);
assert.match(automotive,/height: Math.max\(0,parent.height-2-parent.unitHeight\)/);
assert.match(automotive,/width: Math.max\(0,parent.width-4-parent.unitWidth\)/);
assert.match(chassis,/readonly property real screwEdgeClearance: screwInset-screwDiameter\/2/);
assert.match(chassis,/createLinearGradient\(-head,-head,head,head\)/);
for(const source of [chassis,automotive,stopwatchDialSource]) assert.match(source,/property color screwColor: "#40899b"/);
assert.match(automotive,/screwColor: root.screwColor/);
assert.equal((stopwatchDialSource.match(/screwColor: dialRoot.screwColor/g)||[]).length,2);
assert.match(chassis,/function onScrewColorChanged\(\) \{ plate.requestPaint\(\) \}/);
for(const source of [chassis,automotive,stopwatchDialSource]) assert.match(source,/property real screwColorStrength: 0\.75/);
assert.match(automotive,/screwColorStrength: root.screwColorStrength/);
assert.equal((stopwatchDialSource.match(/screwColorStrength: dialRoot.screwColorStrength/g)||[]).length,2);
assert.match(chassis,/function onScrewColorStrengthChanged\(\) \{ plate.requestPaint\(\) \}/);
assert.match(chassis,/Math.max\(0,Math.min\(1,screwColorStrength\)\)/);
for(const [property,value] of [["screwShadow","0.75"],["screwDirectLight","0.20"],["screwReflectedLight","0.10"],["screwCatchlight","0.40"],["screwRecessDepth","0.14"]]) assert.ok(chassis.includes("readonly property real "+property+": "+value));
assert.ok(chassis.indexOf("disk(head,shade)") > chassis.indexOf("cross(half,arm,metal"));
assert.ok(chassis.indexOf("Fixed screen-space top-right catchlight") > chassis.indexOf("disk(head,shade)"));
assert.match(chassis,/Math.atan2\(height\/2-y,width\/2-x\)-Math.PI\/4/);
assert.doesNotMatch(chassis,/c.arc\(x\+0.35,y\+0.55/);
assert.match(stopwatchDialSource,/externalUnitReadout: true/);
