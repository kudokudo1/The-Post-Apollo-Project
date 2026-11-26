const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const ctx=vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname,"../../services/diagnostics/DiagnosticCalibration.js"),"utf8"),ctx);
const run=x=>{ctx.input=JSON.stringify(x);return vm.runInContext("previewCalibration(JSON.parse(input))",ctx)};
const plain=x=>JSON.parse(JSON.stringify(x));
for(const k of ["threads","memory","census","storage","inventory","appcontrol"]){
    const d=plain(ctx.defaultsFor(k));
    assert.equal(run(d).ok,true,k);
}
const t=plain(ctx.defaultsFor("threads"));
assert.equal(run({...t,durationSeconds:10,intervalMs:500,topCount:6}).ok,true);
assert.equal(run({...t,intervalMs:100}).ok,false);
assert.equal(run({...t,topCount:12}).ok,false);
assert.equal(run({...t,durationSeconds:120,intervalMs:5000}).ok,true);
assert.equal(run({...t,topCount:"4"}).ok,false);
assert.equal(run({...t,pid:12}).ok,false);
assert.equal(run({...t,command:"anything"}).ok,false);
assert.equal(run({...t,durationSeconds:0}).ok,false);
assert.equal(run({...t,durationSeconds:121}).ok,false);
assert.equal(run({...t,intervalMs:333}).ok,false);
assert.equal(run({...t,intervalMs:5000,durationSeconds:1}).ok,false);
assert.equal(run({...plain(ctx.defaultsFor("memory")),intervalMs:5000}).ok,false);
assert.equal(run({...plain(ctx.defaultsFor("memory")),durationSeconds:60,intervalMs:5000}).observations,13);
assert.equal(run({...plain(ctx.defaultsFor("census")),durationSeconds:60,intervalMs:20000}).ok,true);
assert.equal(run({...plain(ctx.defaultsFor("census")),intervalMs:5000}).ok,false);
assert.equal(run({...plain(ctx.defaultsFor("storage")),durationSeconds:31}).ok,false);
assert.equal(run({...plain(ctx.defaultsFor("appcontrol")),topCount:3}).ok,false);
assert.equal(run(plain(ctx.defaultsFor("appcontrol"))).fixed,true);
assert.equal(run({kind:"gpu"}).ok,false);
assert.equal(run({kind:"inventory",detail:true}).ok,false);
assert.equal(run(null).ok,false);
assert.equal(vm.runInContext('previewCalibration({kind:"threads",get durationSeconds(){throw Error("must not read")},intervalMs:1000,topCount:4}).ok',ctx),false);
assert.equal(vm.runInContext('previewCalibration(Object.create({kind:"inventory"})).ok',ctx),false);
assert.equal(vm.runInContext('previewCalibration({kind:"inventory",[Symbol("extra")]:1}).ok',ctx),false);
const d=plain(ctx.defaultsFor("threads"));d.topCount=12;
assert.equal(ctx.defaultsFor("threads").topCount,4);
console.log("DIAG D1a calibration preview contracts PASS");

ctx.input=JSON.stringify({...t,durationSeconds:2,intervalMs:500,topCount:2});
const plan=plain(vm.runInContext('threadLaunchPlan(JSON.parse(input),p=>"/local/"+p)',ctx));
assert.deepEqual(plan.args,["/usr/bin/timeout","--kill-after=3s","145s","/usr/bin/python3","-B",
    "/local/scripts/syntagma_quickshell_thread_sampler.py","--workshop","--duration","2","--interval","0.5","--top","2"]);
ctx.input=JSON.stringify({...t,pid:7});
assert.equal(vm.runInContext('threadLaunchPlan(JSON.parse(input),p=>p)',ctx),null);
ctx.input=JSON.stringify(plain(ctx.defaultsFor("memory")));
assert.equal(vm.runInContext('threadLaunchPlan(JSON.parse(input),p=>p)',ctx),null);
const policyCtx=vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname,"../../services/diagnostics/CpuPlusDiagnosticsPolicy.js"),"utf8"),policyCtx);
const comparisonCtx=vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname,"../../services/diagnostics/DiagnosticComparison.js"),"utf8"),comparisonCtx);
const tag={workshopSchema:"post-apollo-thread-calibration-v1",startTicks:456,pid:123};
const main={tid:123,cpuPct:55};
const row={event:"threads",pid:123,startTicks:456,sampleIntervalMs:500,totalCpuPct:55,threadCount:1,main,top:[main]};
const start={...tag,event:"start",durationSeconds:2,intervalMs:500,topCount:2};
const end={...tag,event:"complete",samples:4,observedMs:2000};
const encode=rows=>rows.map(x=>JSON.stringify(x)).join("\n");
const rows=[start,row,row,row,row,end];
const valid=encode(rows);
assert.deepEqual(plain(policyCtx.configuredThreadEvidence(valid,plan.config)),plan.config);
assert.match(policyCtx.summarize("threads",valid),/CALIBRATION \/\/ 2 s \/ 500 ms \/ TOP 2/);
assert.equal(policyCtx.configuredThreadEvidence(valid,{...plan.config,topCount:1}),null);
for(const bad of [
    [start,row,row,row,row,{...end,samples:3}],
    [start,row,row,row,row,{...end,observedMs:1900}],
    [start,row,row,row,{...row,startTicks:999},end],
    [start,row,row,row,{...row,top:[main,main]},end],
    [start,row,row,row,{...row,pid:124},end],
    [start,row,row,row,row,{...end,startTicks:999}],
    [start,row,row,row,row],
    [start,row,row,row,row,{...end,workshopSchema:"other"}]
]) assert.equal(policyCtx.configuredThreadEvidence(encode(bad),plan.config),null);
assert.equal(policyCtx.summarize("threads",encode([start,row,end])),null);
const legacy=encode([{event:"start",pid:123},row,{event:"complete",pid:123}]);
assert.equal(policyCtx.configuredThreadEvidence(legacy,plan.config),null);
const first={id:"first",kind:"threads",status:"COMPLETE",text:valid,finishedAt:"2026-11-24T00:00:00Z"};
const second={...first,id:"second",finishedAt:"2026-11-24T00:01:00Z"};
assert.equal(comparisonCtx.compare(first,second,policyCtx.summarize).error,"");
assert.equal(comparisonCtx.compare(first,{...second,text:legacy},policyCtx.summarize).error,"THREAD CALIBRATION MUST MATCH");
assert.equal(comparisonCtx.compare(first,{...second,text:encode([{...start,topCount:3},row,row,row,row,end])},policyCtx.summarize).error,"THREAD CALIBRATION MUST MATCH");
console.log("DIAG D1b configured launch, evidence and comparison PASS");

const observerPlan=config=>{ctx.input=JSON.stringify(config);return plain(vm.runInContext('observerLaunchPlan(JSON.parse(input),p=>"/local/"+p,"/data")',ctx));};
const memConfig={kind:"memory",durationSeconds:5,intervalMs:5000};
const censusConfig={kind:"census",durationSeconds:2,intervalMs:1000};
const storeConfig={kind:"storage",durationSeconds:1};
assert.deepEqual(observerPlan(memConfig).args.slice(-5),["--workshop","--duration","5","--interval","5"]);
assert.deepEqual(observerPlan(censusConfig).args.slice(-5),["--workshop","--duration","2","--interval","1"]);
assert.deepEqual(observerPlan(storeConfig).args.slice(-7),["--workshop","--duration","1","--data-dir","/data","--shell-dir","/local/."]);
for(const bad of [{...memConfig,pid:2},{...censusConfig,intervalMs:100},{...storeConfig,path:"/tmp"},{kind:"inventory"},plain(ctx.defaultsFor("appcontrol"))]) assert.equal(observerPlan(bad),null);
const receipt=(config,samples,ms,extra={})=>({event:"complete",workshopSchema:"post-apollo-observer-calibration-v1",calibration:config,samples,observedMs:ms,...extra});
const memBase={event:"memory",pid:123,startTicks:456,memoryKiB:{Pss:100,SwapPss:0},sampleIntervalMs:null,cpuPct:null};
const memRow={...memBase,sampleIntervalMs:5000,cpuPct:2};
const memEnd=receipt(memConfig,2,5000,{pid:123,startTicks:456});
const memoryText=encode([memBase,memRow,memEnd]);
assert.deepEqual(plain(policyCtx.configuredEvidence("memory",memoryText,memConfig)),memConfig);
assert.match(policyCtx.summarize("memory",memoryText),/CALIBRATION \/\/ 5 s \/ 5000 ms/);
for(const bad of [[memBase,memRow,{...memEnd,observedMs:4000}],[memBase,{...memRow,startTicks:457},memEnd],[memBase,memRow,{...memEnd,samples:1}],[memBase,memRow,{...memEnd,calibration:{...memConfig,pid:123}}]]) assert.equal(policyCtx.configuredEvidence("memory",encode(bad),memConfig),null);
assert.equal(policyCtx.configuredEvidence("memory",memoryText,{...memConfig,durationSeconds:6}),null);
const cenRow={schema:"post-apollo-process-census-v1",event:"census",scope:"same-user",sequence:1,observed:1,cpuMeasured:1,ioMeasured:1,coverage:{truncated:false},previousCoverage:{truncated:false},rows:[{pid:123,name:"quickshell",rssKiB:100,cpuPct:1,readBps:0,writeBps:0}]};
const cenEnd=receipt(censusConfig,2,2000,{schema:cenRow.schema});
const censusText=encode([cenRow,{...cenRow,sequence:2},cenEnd]);
assert.match(policyCtx.summarize("census",censusText),/CALIBRATION \/\/ 2 s \/ 1000 ms/);
assert.equal(policyCtx.configuredEvidence("census",encode([cenRow,cenRow,cenEnd]),censusConfig),null);
const ids=["notifications.history","notifications.favorites","notifications.policies","notifications.scroll","weather.cache","weather.history","weather.events","weather.places","weather.dossier","hub.layout","hub.notes","hub.todo","social.identities","git.journal","git.delta","forest.preferences","finance.manual","company.hubs"];
const storeRow={schema:"post-apollo-storage-observation-v1",event:"storage",sequence:1,intervals:1,elapsedMs:1000,rows:ids.map(id=>({id,initialState:"absent",finalState:"absent",initialBytes:null,finalBytes:null,changedIntervals:0,replacementIntervals:0,unavailableIntervals:0,comparableIntervals:1}))};
const storeEnd=receipt(storeConfig,1,1000,{schema:storeRow.schema});
const storageText=encode([storeRow,storeEnd]);
assert.match(policyCtx.summarize("storage",storageText),/CALIBRATION \/\/ 1 s \/ 1000 ms metadata cadence/);
assert.equal(policyCtx.configuredEvidence("storage",encode([{...storeRow,intervals:2},storeEnd]),storeConfig),null);
const oldStorage={id:"old",kind:"storage",status:"COMPLETE",text:encode([storeRow,{event:"complete",schema:storeRow.schema,samples:1}]),finishedAt:"2026-11-24T00:00:00Z"};
assert.equal(comparisonCtx.compare(oldStorage,{...oldStorage,id:"new",text:storageText,finishedAt:"2026-11-24T00:01:00Z"},policyCtx.summarize).error,"OBSERVER CALIBRATION MUST MATCH");
console.log("DIAG D1c configured observer launch and receipt PASS");

const workflowPreview=x=>{ctx.input=JSON.stringify(x);return plain(vm.runInContext("previewWorkflow(JSON.parse(input))",ctx));};
const workflow={durationSeconds:30,instruments:[
    {kind:"storage"},{kind:"memory",intervalMs:10000},{kind:"threads",intervalMs:1000,topCount:4},{kind:"census",intervalMs:10000}]};
const w=workflowPreview(workflow);
assert.equal(w.ok,true);
assert.equal(w.launchReady,false);
assert.deepEqual(w.instruments.map(x=>x.config.kind),["threads","memory","census","storage"]);
assert.equal(w.sharedQuickshellIdentityRequired,true);
assert.equal(w.maximumCombinedPayloadBytes,4*65536);
assert.equal(w.estimatedObservations,40);
assert.deepEqual(workflowPreview({...workflow,instruments:workflow.instruments.slice().reverse()}),w);
assert.equal(workflowPreview({...workflow,durationSeconds:31}).ok,false);
assert.equal(workflowPreview({...workflow,instruments:[{kind:"memory",intervalMs:10000},{kind:"memory",intervalMs:10000}]}).ok,false);
assert.equal(workflowPreview({...workflow,instruments:[{kind:"storage"}]}).ok,false);
assert.equal(workflowPreview({...workflow,instruments:[{kind:"storage"},{kind:"appcontrol"}]}).ok,false);
assert.equal(workflowPreview({...workflow,instruments:[{kind:"storage"},{kind:"memory",intervalMs:10000,pid:123}]}).ok,false);
assert.equal(workflowPreview({...workflow,instruments:[{kind:"storage"},{kind:"threads",intervalMs:100,topCount:4}]}).ok,false);
assert.equal(workflowPreview({...workflow,instruments:[{kind:"storage"},{kind:"memory",intervalMs:10000,durationSeconds:10}]}).ok,false);
assert.equal(workflowPreview({...workflow,autoStart:true}).ok,false);
assert.equal(vm.runInContext('previewWorkflow({durationSeconds:30,instruments:[{kind:"storage"}, {get kind(){throw Error("getter must not run")}}]}).ok',ctx),false);
assert.equal(vm.runInContext('previewWorkflow({durationSeconds:30,instruments:[{kind:"storage"},,]}).ok',ctx),false);
console.log("DIAG D2a shared calibration workflow contracts PASS");

ctx.input=JSON.stringify(workflow);
const workflowLaunch=plain(vm.runInContext('workflowLaunchPlan(JSON.parse(input),p=>"/local/"+p,"/data")',ctx));
assert.deepEqual(workflowLaunch.args.slice(0,7),["/usr/bin/timeout","--kill-after=3s","145s","/usr/bin/python3","-B","/local/scripts/cpuplus_diagnostic_workflow.py","--plan"]);
assert.deepEqual(JSON.parse(workflowLaunch.args[7]),workflowLaunch.plan);
assert.deepEqual(workflowLaunch.plan.instruments.map(x=>x.kind),["threads","memory","census","storage"]);
assert.equal(vm.runInContext('workflowLaunchPlan(JSON.parse(input),p=>p,"relative")',ctx),null);
console.log("DIAG D2b fixed workflow command contract PASS");


// D2c: actual existing policies must validate child metrics, not just transport.
const pairedPlan={durationSeconds:5,instruments:[{kind:"threads",intervalMs:1000,topCount:2},{kind:"memory",intervalMs:5000}]};
const pairedPin={pid:123,startTicks:456};
const threadConfig={...pairedPlan.instruments[0],durationSeconds:5};
const memoryConfig={...pairedPlan.instruments[1],durationSeconds:5};
const threadRecords=[{...tag,event:"start",durationSeconds:5,intervalMs:1000,topCount:2,monotonicMs:1000},
    ...Array.from({length:5},(_,i)=>({...row,sampleIntervalMs:1000,monotonicMs:2000+i*1000})),
    {...tag,event:"complete",samples:5,observedMs:5000,monotonicMs:6000}];
const memoryRecords=[{...memBase,monotonicMs:1100},{...memRow,monotonicMs:6100},
    {...memEnd,monotonicMs:6100}];
const collected=(config,records,first,last)=>({config,records,status:"COLLECTED",exitCode:0,error:"",
    launchMonotonicMs:900,payloadBytes:encode(records).length+1,firstMonotonicMs:first,lastMonotonicMs:last});
const combined={schema:"post-apollo-diagnostic-workflow-transport-v1",status:"COLLECTED",durationSeconds:5,
    pinnedQuickshell:pairedPin,startedMonotonicMs:900,finishedMonotonicMs:6200,overlapMs:4900,
    instruments:[collected(threadConfig,threadRecords,1000,6000),collected(memoryConfig,memoryRecords,1100,6100)]};
const validateWorkflow=(x,p=pairedPlan)=>plain(policyCtx.workflowEvidence(JSON.stringify(x),p));
assert.equal(validateWorkflow(combined).complete,2);
assert.match(policyCtx.summarize("workflow",JSON.stringify(combined)),/2 \/ 2 VERIFIED/);
assert.equal(validateWorkflow({...combined,overlapMs:5000}),null);
assert.equal(validateWorkflow({...combined,pinnedQuickshell:{...pairedPin,startTicks:999}}),null);
assert.equal(validateWorkflow(combined,{...pairedPlan,durationSeconds:6}),null);
assert.equal(validateWorkflow({...combined,instruments:combined.instruments.slice().reverse()}),null);
const invalid=plain(combined);invalid.instruments[0].records[1].totalCpuPct=-1;
assert.equal(validateWorkflow(invalid),null);
const badMemory=plain(combined);badMemory.instruments[1].records[1].memoryKiB.Pss=-1;
assert.equal(validateWorkflow(badMemory),null);
const badClock=plain(combined);badClock.instruments[0].records[2].monotonicMs=1000;
assert.equal(validateWorkflow(badClock),null);
const partial=plain(combined);partial.status="NOT VERIFIED";partial.overlapMs=null;
partial.instruments[1]={config:memoryConfig,records:[],status:"NOT VERIFIED",exitCode:1,error:"COLLECTOR EXIT",launchMonotonicMs:900,payloadBytes:0};
assert.equal(validateWorkflow(partial).complete,1);
assert.equal(policyCtx.summarize("workflow",JSON.stringify(partial)),null);
assert.equal(validateWorkflow({...partial,status:"COLLECTED"}),null);
assert.equal(validateWorkflow({...partial,status:"CANCELLED"}).status,"CANCELLED");
const archiveWorkflow={kind:"workflow",id:"session-abc-def-1",status:"COMPLETE",summary:"summary",text:"x".repeat(300000),finishedAt:"2026-11-24T12:00:00.000Z"};
assert.ok(policyCtx.archiveResponse({schema:"post-apollo-diagnostic-archive-v1",rows:[archiveWorkflow],savedId:null},{action:"list"}));
assert.equal(policyCtx.archiveResponse({schema:"post-apollo-diagnostic-archive-v1",rows:[{...archiveWorkflow,text:"x".repeat(300001)}],savedId:null},{action:"list"}),null);
console.log("DIAG D2c combined evidence and report capacity PASS");


// D3d: calibration selects real shell heartbeat gaps, never arbitrary commands.
const stall={kind:"stall",durationSeconds:5,thresholdMs:350};
assert.equal(run(stall).ok,true);
for(const bad of [{...stall,durationSeconds:4},{...stall,thresholdMs:100},
                  {...stall,thresholdMs:351},{...stall,thresholdMs:2050},{...stall,pid:123}])
    assert.equal(run(bad).ok,false);
ctx.input=JSON.stringify(stall);
assert.deepEqual(plain(vm.runInContext('observerLaunchPlan(JSON.parse(input),p=>"/local/"+p,"/data")',ctx)).args,
    ["/usr/bin/timeout","--kill-after=3s","145s","/usr/bin/python3","-B","/local/scripts/cpuplus_stall_clock_witness.py","--duration","5"]);
const witness={schema:"post-apollo-stall-clock-v1",durationSeconds:5,startWallMs:10000,endWallMs:15000,elapsedMs:5000};
const ticks=Array.from({length:49},(_,i)=>10100+i*100);
const stalled=ticks.filter(t=>t<12000||t>=12400);
const combinedStall=policyCtx.combineStall(JSON.stringify(witness),stalled,stall);
assert.ok(combinedStall);
let evidenceStall=plain(policyCtx.stallEvidence(combinedStall,stall));
assert.equal(evidenceStall.gaps.length,1);
assert.equal(evidenceStall.maxGapMs,500);
assert.equal(evidenceStall.coverageMs,4800);
assert.match(policyCtx.summarize("stall",combinedStall),/GAPS \/\/ 1/);
const cleanStall=policyCtx.combineStall(JSON.stringify(witness),ticks,stall);
assert.equal(policyCtx.stallEvidence(cleanStall,stall).gaps.length,0);
assert.equal(policyCtx.stallEvidence(combinedStall,{...stall,thresholdMs:400}),null);
for(const bad of [[],[10100],[10100,10000],ticks.slice(10),ticks.slice(0,-10),Array(1501).fill(10100)])
    assert.equal(policyCtx.combineStall(JSON.stringify(witness),bad,stall),null);
assert.equal(policyCtx.combineStall(JSON.stringify({...witness,elapsedMs:6000}),ticks,stall),null);
assert.equal(policyCtx.combineStall(JSON.stringify({...witness,durationSeconds:6}),ticks,stall),null);
console.log("DIAG D3d stall calibration, threshold and coverage contracts PASS");


const withStall={durationSeconds:5,instruments:[...pairedPlan.instruments,{kind:"stall",thresholdMs:350}]};
assert.equal(workflowPreview(withStall).ok,true);
assert.equal(workflowPreview({...withStall,instruments:[...withStall.instruments,{kind:"stall",thresholdMs:350}]}).ok,false);
const allFive={durationSeconds:10,instruments:[{kind:"threads",intervalMs:1000,topCount:2},
    {kind:"memory",intervalMs:5000},{kind:"census",intervalMs:5000},{kind:"storage"},{kind:"stall",thresholdMs:350}]};
assert.equal(workflowPreview(allFive).maximumCombinedPayloadBytes,4*65536+24000);
const workflowWitness={...witness,startedMonotonicMs:1000,monotonicMs:6000};
const transportStall=plain(combined);
transportStall.instruments.push(collected(stall,[workflowWitness],1000,6000));
const attached=policyCtx.attachWorkflowStall(JSON.stringify(transportStall),withStall,stalled,false);
assert.ok(attached);
assert.equal(validateWorkflow(JSON.parse(attached),withStall).complete,3);
assert.equal(JSON.parse(attached).overlapMs,4300);
assert.match(policyCtx.summarize("workflow",attached),/STALL \/\/ 1 GAPS/);
assert.equal(validateWorkflow(transportStall,withStall),null);
const missing=policyCtx.attachWorkflowStall(JSON.stringify(transportStall),withStall,[],false);
assert.equal(validateWorkflow(JSON.parse(missing),withStall).complete,2);
assert.equal(JSON.parse(missing).status,"NOT VERIFIED");
assert.equal(policyCtx.summarize("workflow",missing),null);
assert.equal(JSON.parse(policyCtx.attachWorkflowStall(JSON.stringify(transportStall),withStall,stalled,true)).status,"NOT VERIFIED");
assert.equal(policyCtx.attachWorkflowStall(JSON.stringify({...transportStall,overlapMs:999}),withStall,stalled,false),null);
assert.equal(validateWorkflow(JSON.parse(attached),{...withStall,instruments:[...pairedPlan.instruments,{kind:"stall",thresholdMs:400}]}),null);
const damaged=JSON.parse(attached);damaged.instruments[2].records[0].ticks=[];
assert.equal(validateWorkflow(damaged,withStall),null);
console.log("DIAG D3e coordinated stall coverage and five-instrument calibration PASS");


// D4a: named session presets reuse validated calibration, not launch state.
ctx.input=JSON.stringify(allFive);
const presetDraft=plain(vm.runInContext("workshopDraftFromPlan(JSON.parse(input))",ctx));
assert.deepEqual(presetDraft.selected,["threads","memory","census","storage","stall"]);
assert.equal(presetDraft.stallThresholdMs,350);
ctx.input=JSON.stringify(presetDraft);
assert.deepEqual(plain(vm.runInContext("workshopPlanFromDraft(JSON.parse(input))",ctx)),allFive);
for(const bad of [{...allFive,autoStart:true},{...allFive,durationSeconds:1},{durationSeconds:5,instruments:[{kind:"stall",thresholdMs:351}]},
                 {durationSeconds:5,instruments:[{kind:"appcontrol",intervalMs:1000,topCount:4}]},
                 {durationSeconds:5,instruments:[{kind:"stall",thresholdMs:350,durationSeconds:5}]}]){
    ctx.input=JSON.stringify(bad);
    assert.equal(vm.runInContext("workshopDraftFromPlan(JSON.parse(input))",ctx),null);
}
ctx.input=JSON.stringify({durationSeconds:5,instruments:[{kind:"stall",thresholdMs:500}]});
assert.equal(vm.runInContext("workshopDraftFromPlan(JSON.parse(input)).stallThresholdMs",ctx),500);
console.log("DIAG D4a shared preset calibration PASS");

const setPlan=[{name:"A",plan:allFive},{name:"B",plan:{durationSeconds:5,instruments:[{kind:"stall",thresholdMs:500}]}},{name:"A",plan:allFive}];
ctx.input=JSON.stringify(setPlan);
const checkedSet=plain(vm.runInContext("validatedWorkshopSet(JSON.parse(input))",ctx));
assert.deepEqual(checkedSet.items,setPlan);
assert.equal(checkedSet.durationSeconds,25);
for(const bad of [[],Array(5).fill(setPlan[0]),[{...setPlan[0],autoStart:true}],
    [{name:"BAD",plan:{durationSeconds:5,instruments:[{kind:"stall",thresholdMs:351}]}}],
    Array(3).fill({name:"LONG",plan:{durationSeconds:120,instruments:[{kind:"stall",thresholdMs:350}]}})]){
    ctx.input=JSON.stringify(bad);
    assert.equal(vm.runInContext("validatedWorkshopSet(JSON.parse(input))",ctx),null);
}
console.log("DIAG D4b detached bounded ordered sets PASS");

const explicitStorage={kind:"storage",durationSeconds:5,sampleSeconds:2,reportSeconds:4};
assert.equal(run(explicitStorage).ok,true);
assert.equal(run(explicitStorage).intervals,3);
assert.equal(run(explicitStorage).observations,2);
for(const bad of [{...explicitStorage,sampleSeconds:0},{...explicitStorage,reportSeconds:3},
    {...explicitStorage,durationSeconds:30,sampleSeconds:1,reportSeconds:4},
    {kind:"storage",durationSeconds:5,sampleSeconds:2}]) assert.equal(run(bad).ok,false);
const extendedRow=(seq,intervals,elapsedMs)=>({...storeRow,sequence:seq,intervals,elapsedMs,
    rows:storeRow.rows.map(r=>({...r,comparableIntervals:intervals}))});
const extendedEnd={...storeEnd,calibration:explicitStorage,samples:2,observedMs:5000};
const explicitText=encode([extendedRow(1,2,4000),extendedRow(2,3,5000),extendedEnd]);
assert.deepEqual(plain(policyCtx.configuredEvidence("storage",explicitText,explicitStorage)),explicitStorage);
assert.match(policyCtx.summarize("storage",explicitText),/2 s metadata cadence \/ 4 s reports/);
assert.equal(policyCtx.configuredEvidence("storage",explicitText,{kind:"storage",durationSeconds:5}),null);
assert.equal(policyCtx.configuredEvidence("storage",explicitText,{...explicitStorage,reportSeconds:2}),null);
assert.equal(policyCtx.configuredEvidence("storage",encode([extendedRow(1,2,3999),extendedRow(2,3,5000),extendedEnd]),explicitStorage),null);
const cadencePlan={durationSeconds:5,instruments:[{kind:"storage",sampleSeconds:2,reportSeconds:4},{kind:"stall",thresholdMs:350}]};
assert.equal(workflowPreview(cadencePlan).ok,true);
ctx.input=JSON.stringify(cadencePlan);
assert.deepEqual(plain(vm.runInContext("workshopPlanFromDraft(workshopDraftFromPlan(JSON.parse(input)))",ctx)),
    cadencePlan);
console.log("DIAG D5a bounded storage cadence and legacy evidence contracts PASS");
