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
