const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const assert=require("node:assert/strict");
const root=path.join(__dirname,"../../services/diagnostics");
const context=vm.createContext({assert});
for(const file of ["DiagnosticCalibration.js","DiagnosticTargetRegistry.js"])
    vm.runInContext(fs.readFileSync(path.join(root,file),"utf8"),context);
function verify(assert,T,C) {
    const rows=T.diagnosticTargets();
    assert(rows.length===16,"all registry entries");
    assert(new Set(rows.map(t=>t.id)).size===rows.length,"unique stable IDs");
    assert(rows.every(t=>T.targetCategories().includes(t.category)),"known categories");
    assert(T.searchDiagnosticTargets("appcontrol","APOLLO").some(t=>t.id==="appcontrol"),"search AppControl");
    assert(T.searchDiagnosticTargets("pid","PROCESS").some(t=>t.id==="process-instance"),"PID discoverable");
    assert(T.searchDiagnosticTargets("appcontrol","SYSTEM").length===0,"category enforced");
    assert(T.searchDiagnosticTargets("  HOST   CPU ","SYSTEM").some(t=>t.id==="host-cpu"),"case and whitespace");
    assert(T.searchDiagnosticTargets("","invalid").length===0,"invalid category refused");
    assert(T.searchDiagnosticTargets("x".repeat(129),"ALL").length===0,"bounded search");
    assert(T.findDiagnosticTarget("forest").available===false,"Forest not falsely selectable");
    assert(T.findDiagnosticTarget("process-instance").available===false,"PID not falsely selectable");
    assert(T.findDiagnosticTarget("unknown")===null,"unknown target refused");
    assert(T.fixedTargetCompatibility("appcontrol","appcontrol"),"existing specialized route");
    assert(!T.fixedTargetCompatibility("appcontrol","threads"),"no generic substitution");
    assert(T.fixedTargetCompatibility("source","inventory"),"static source route");
    assert(!T.fixedTargetCompatibility("cpuplus-kill","appcontrol"),"no false isolated widget attribution");
    const plan=(kind,duration,extra)=>({durationSeconds:duration,instruments:[Object.assign({kind},extra)]});
    const mem=plan("memory",120,{intervalMs:10000});
    const cpu=plan("hostcpu",10,{intervalMs:1000});
    const stall=plan("stall",5,{thresholdMs:350});
    const threads=plan("threads",30,{intervalMs:1000,topCount:4});
    const mixed={durationSeconds:10,instruments:[{kind:"threads",intervalMs:1000,topCount:4},{kind:"hostcpu",intervalMs:1000}]};
    const ok=(id,p)=>T.targetPlanCompatibility(id,p,C).ok;
    assert(ok("quickshell",mem)&&ok("quickshell",threads),"actual Quickshell instruments");
    assert(!ok("quickshell",cpu),"host CPU cannot become per-process");
    assert(ok("host-cpu",cpu),"host CPU matches");
    assert(ok("apollo-loop",stall)&&!ok("quickshell",stall),"launching vs newest shell distinct");
    assert(ok("automatic",mixed)&&!ok("quickshell",mixed),"mixed scope explicit");
    assert(!ok("appcontrol",threads),"specialized AppControl not generic");
    assert(!ok("process-instance",threads),"unqualified PID refuses");
    assert(!ok("automatic",{durationSeconds:0,instruments:[]}),"invalid calibration refused");
    for(const t of rows.filter(r=>r.route==="configured"&&r.id!=="automatic")){
        for(const kind of t.kinds){
            const config=C.defaultsFor(kind);
            const {durationSeconds,...instrument}=config;
            assert(ok(t.id,{durationSeconds,instruments:[instrument]}),t.id+" matches actual preview scope");
        }
    }
    rows[0].kinds.length=0;assert(T.diagnosticTargets()[0].kinds.length===10,"detached registry");
}

vm.runInContext(verify.toString()+"\nverify(assert,{diagnosticTargets,targetCategories,findDiagnosticTarget,searchDiagnosticTargets,targetPlanCompatibility,fixedTargetCompatibility},{workshopDraftFromPlan,previewCalibration,defaultsFor});",context);
console.log("diagnostic target registry PASS");
