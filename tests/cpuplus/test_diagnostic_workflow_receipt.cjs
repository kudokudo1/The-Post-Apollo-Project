const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const assert=require("node:assert/strict");
const root=path.join(__dirname,"../../services/diagnostics");
const context=vm.createContext({assert});
for(const file of ["DiagnosticWorkflowDefaults.js","DiagnosticWorkflowCatalog.js","DiagnosticCalibration.js","DiagnosticWorkflowReceipt.js"])
    vm.runInContext(fs.readFileSync(path.join(root,file),"utf8"),context);
function verify(assert,Receipt,Catalog,Defaults,Cal) {
    const defaults=Defaults.initialWorkflowFavorites();
    const validate=d=>Catalog.validatedCatalog(d,defaults,Cal);
    const seed=()=>Catalog.newCatalog(defaults,Cal);
    const qualify=(r,q)=>Receipt.qualifyReceipt(r,q,validate,seed);
    const load={action:"load"};
    const initial=seed();
    const missing=qualify({status:"MISSING",document:null},load);
    assert(missing.status==="READY"&&missing.document.rows.length===6&&missing.expected===null,"seed only missing");
    const empty={...initial,rows:[]};
    const loaded=qualify({status:"LOADED",document:empty},load);
    assert(loaded.document.rows.length===0&&loaded.expected!==empty,"empty retained");
    const edit=Catalog.editCatalog(initial,{action:"favorite",id:"default-memory",favorite:false},defaults,Cal);
    const save={action:"save",expected:initial,document:edit};
    const saved=qualify({status:"SAVED",document:edit},save);
    assert(saved.document.rows[0].favorite===false,"saved edit confirmed");
    assert(saved.document!==edit&&saved.expected!==edit,"detached receipt");
    assert(!qualify({status:"SAVED",document:initial},save),"wrong save refused");
    assert(!qualify({status:"MISSING",document:null},save),"missing save refused");
    assert(!qualify({status:"LOADED",document:edit},save),"wrong operation refused");
    assert(!qualify({status:"SAVED",document:edit},load),"wrong load receipt refused");
    const conflict=qualify({status:"CONFLICT",document:initial},save);
    assert(conflict.status==="CONFLICT"&&conflict.document===null,"conflict requires explicit reload");
    assert(!qualify({status:"CONFLICT",document:initial},load),"load conflict refused");
    assert(!qualify({status:"CONFLICT",document:{bad:true}},save),"invalid conflict refused");
    assert(!qualify({status:"MISSING",document:initial},load),"fake missing refused");
    assert(!qualify({status:"LOADED",document:{bad:true}},load),"invalid load refused");
    assert(!qualify({status:"LOADED",document:initial,extra:true},load),"extra field refused");
    const reordered={rows:edit.rows,nextId:edit.nextId,schema:edit.schema};
    assert(!!qualify({status:"SAVED",document:reordered},save),"key ordering irrelevant");
}

vm.runInContext(verify.toString()+"\nverify(assert,{qualifyReceipt},{validatedCatalog,newCatalog,editCatalog},{initialWorkflowFavorites},{workshopDraftFromPlan,workshopPlanFromDraft});",context);
const qml=fs.readFileSync(path.join(root,"DiagnosticWorkflowStore.qml"),"utf8");
assert(!/Component\.onCompleted|repeat:\s*true/.test(qml),"no auto IO or repeating timer");
assert(qml.includes('"-E","-s","-B"'),"helper sibling import support");
assert(qml.includes("if(!busy||!stdoutSeen||!exitSeen)return;"),"both terminal signals required");
console.log("diagnostic workflow receipt PASS");
