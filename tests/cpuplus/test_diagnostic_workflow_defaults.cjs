const fs=require("node:fs"), path=require("node:path"), vm=require("node:vm");
const assert=require("node:assert/strict");
const root=path.resolve(__dirname,"../..");
function load(file) {
    const context=vm.createContext({});
    vm.runInContext(fs.readFileSync(path.join(root,file),"utf8"),context);
    return context;
}
function verify(assert, seeds, calibration, policy) {
    const rows=seeds.initialWorkflowFavorites();
    assert(rows.length===6,"six default records");
    assert(new Set(rows.map(r=>r.id)).size===6,"stable unique IDs");
    assert(rows.every(r=>r.favorite===true),"all initially favorited");
    assert(rows.map(r=>r.id).join(",")==="default-memory,default-inventory,default-threads,default-census,default-storage,default-appcontrol","existing QUICK order");
    const resolver=p=>"/shell/"+p, dataDir="/data";
    for(const row of rows) {
        if(row.execution==="configured") {
            const plan=row.plan;
            assert(calibration.workshopDraftFromPlan(plan)!==null,row.id+" accepts existing calibration");
            const config=Object.assign({},plan.instruments[0],{durationSeconds:plan.durationSeconds});
            const configured=calibration.observerLaunchPlan(config,resolver,dataDir);
            const fixed=policy.argumentsFor(config.kind,resolver,dataDir);
            assert(!!configured && !!fixed,row.id+" both command builders valid");
            // The calibrated transport adds only --workshop for these defaults.
            // Compare flags as pairs because storage builder orders them differently.
            const normalize=args=>{
                const flags=args.slice(6).filter(x=>x!=="--workshop");
                const pairs=[];
                for(let i=0;i<flags.length;i+=2) pairs.push(flags[i]+"="+flags[i+1]);
                return JSON.stringify([args.slice(0,6),pairs.sort()]);
            };
            assert(normalize(configured.args)===normalize(fixed),row.id+" same command and parameters");
        } else {
            assert(["inventory","appcontrol"].includes(row.kind),row.id+" fixed allowlisted");
            assert(!!policy.argumentsFor(row.kind,resolver,dataDir),row.id+" existing command preserved");
            assert(!Object.prototype.hasOwnProperty.call(row,"plan"),row.id+" not misrepresented as calibrated");
        }
    }
    const app=policy.argumentsFor("appcontrol",resolver,dataDir);
    assert(app.includes("--parent-quickshell"),"AppControl launching shell preserved");
    rows[0].favorite=false;rows[0].plan.instruments[0].intervalMs=999;
    const fresh=seeds.initialWorkflowFavorites();
    assert(fresh[0].favorite&&fresh[0].plan.instruments[0].intervalMs===10000,"fresh detached defaults");
}

// Run all plain-object validation in one realm, matching QML's JS engine.
const context=vm.createContext({assert});
for(const file of ["services/diagnostics/DiagnosticWorkflowDefaults.js","services/diagnostics/DiagnosticCalibration.js","services/diagnostics/CpuPlusDiagnosticsPolicy.js"])
    vm.runInContext(fs.readFileSync(path.join(root,file),"utf8"),context);
vm.runInContext(verify.toString()+"\nverify(assert,{initialWorkflowFavorites},{workshopDraftFromPlan,observerLaunchPlan},{argumentsFor});",context);
console.log("diagnostic default workflow contract PASS");
