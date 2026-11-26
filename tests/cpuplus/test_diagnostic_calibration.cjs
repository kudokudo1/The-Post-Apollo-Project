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
