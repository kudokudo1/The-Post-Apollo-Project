const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const assert=require("node:assert/strict");
const context=vm.createContext({assert});
for(const file of ["DiagnosticWorkflowDefaults.js","DiagnosticCalibration.js","DiagnosticTargetRegistry.js","DiagnosticWorkflowCatalog.js"])
    vm.runInContext(fs.readFileSync(path.join(__dirname,"../../services/diagnostics",file),"utf8"),context);
function verify(assert, defaults, cal, cat) {
    const seeds=defaults.initialWorkflowFavorites();
    const initial=cat.newCatalog(seeds,cal);
    assert(initial.rows.length===6,"six defaults");
    const validate=d=>cat.validatedCatalog(d,seeds,cal);
    const edit=(d,e)=>cat.editCatalog(d,e,seeds,cal);
    const round=d=>validate(JSON.parse(JSON.stringify(d)));
    assert(round(initial).rows.length===6,"JSON round trip");
    const unfav=edit(initial,{action:"favorite",id:"default-memory",favorite:false});
    assert(unfav.rows[0].favorite===false&&initial.rows[0].favorite===true,"favorite detached");
    assert(round(unfav).rows[0].favorite===false,"favorite round trip");
    const plan=initial.rows[0].plan;
    const saved=edit(unfav,{action:"create",name:"My memory",plan,favorite:true});
    assert(saved.rows[6].id==="user-1"&&saved.nextId===2,"save stable id");
    assert(saved.rows[6].plan!==plan,"save detached plan");
    assert(!edit(saved,{action:"create",name:"my MEMORY",plan,favorite:true}),"duplicate names refused");
    assert(!edit(saved,{action:"favorite",id:"missing",favorite:true}),"unknown id refused");
    assert(!edit(saved,{action:"favorite",id:"user-1",favorite:"true"}),"bad favorite refused");
    assert(!edit(saved,{action:"replace",id:"default-appcontrol",plan}),"fixed adapter protected");
    assert(!edit(saved,{action:"replace",id:"user-1",plan:{durationSeconds:0,instruments:[]}}),"invalid plan refused");
    const renamed=edit(saved,{action:"rename",id:"user-1",name:"Memory custom"});
    assert(renamed.rows[6].name==="Memory custom"&&renamed.rows[6].id==="user-1","rename stable id");
    const removed=edit(renamed,{action:"remove",id:"user-1"});
    assert(removed.rows.length===6&&removed.nextId===2,"delete not reuse id");
    const next=edit(removed,{action:"create",name:"Another",plan,favorite:false});
    assert(next.rows[6].id==="user-2","monotonic id");
    let empty=initial;
    for(const row of initial.rows)empty=edit(empty,{action:"remove",id:row.id});
    assert(round(empty).rows.length===0,"empty saved library not reseeded");
    assert(!validate({...initial,schema:"unknown"}),"unknown schema refused");
    assert(!validate({...initial,rows:[...initial.rows,initial.rows[0]]}),"duplicate id refused");
    assert(!validate({...initial,rows:[{...initial.rows[1],kind:"threads"}]}),"forged fixed route refused");
    assert(!validate({...initial,rows:[{...initial.rows[0],argv:["/bin/sh"]}]}),"executable fields refused");
    assert(!validate({...initial,rows:[{...initial.rows[0],id:"user-1"}]}),"unallocated id refused");
    const queue=cat.queueProjection(saved.rows[6],cal);
    assert(!!cal.validatedWorkshopSet([queue]),"queue projection valid");
    assert(Object.keys(queue).sort().join(",")==="name,plan","metadata stripped from queue");
    assert(cat.queueProjection(initial.rows[1],cal)===null,"fixed not misrepresented in queue");
    assert(!edit(initial,{action:"launch",id:"default-memory"}),"no execution action");
    let many=initial;
    for(let i=0;i<58;i++)many=edit(many,{action:"create",name:"Custom "+i,plan,favorite:false});
    assert(many.rows.length===64&&!edit(many,{action:"create",name:"Overflow",plan,favorite:false}),"catalog limit");
}

vm.runInContext(verify.toString()+"\nverify(assert,{initialWorkflowFavorites},{workshopDraftFromPlan,workshopPlanFromDraft,validatedWorkshopSet},{newCatalog,validatedCatalog,editCatalog,queueProjection});",context);
console.log("diagnostic workflow catalog PASS");

vm.runInContext(`
    const targetSeeds=initialWorkflowFavorites();
    const targetCal={workshopDraftFromPlan,workshopPlanFromDraft,
        targetCompatible:(id,p)=>targetPlanCompatibility(id,p,{workshopDraftFromPlan,previewCalibration}).ok};
    const legacy=newCatalog(targetSeeds,targetCal);
    const change={action:"create",name:"Event loop target",favorite:true,
        plan:{durationSeconds:5,instruments:[{kind:"stall",thresholdMs:350}]},targetId:"apollo-loop"};
    const explicit=editCatalog(legacy,change,targetSeeds,targetCal);
    assert(explicit.rows[6].targetId==="apollo-loop");
    assert(validatedCatalog(JSON.parse(JSON.stringify(explicit)),targetSeeds,targetCal).rows[6].targetId==="apollo-loop");
    for(const id of ["quickshell","process-instance","automatic","unknown"])
        assert(!editCatalog(legacy,{...change,targetId:id},targetSeeds,targetCal));
    assert(!queueProjection(explicit.rows[6],targetCal));
    assert(!editCatalog(explicit,{action:"replace",id:"user-1",plan:legacy.rows[0].plan},targetSeeds,targetCal));
    assert(!Object.hasOwn(legacy.rows[0],"targetId"));
`,context);
console.log("diagnostic target catalog custody PASS");
