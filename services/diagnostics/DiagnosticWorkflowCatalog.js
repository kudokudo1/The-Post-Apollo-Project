// Pure catalog policy. No launch, filesystem or authority API.
// Supply the existing calibration functions and initialWorkflowFavorites.
const catalogSchema="post-apollo-diagnostic-workflow-catalog-v1";
const catalogLimit=64;
function exactFields(o, fields) {
    return !!o && Object.getPrototypeOf(o)===Object.prototype &&
        Reflect.ownKeys(o).length===fields.length && fields.every(k=>{
            const d=Object.getOwnPropertyDescriptor(o,k);
            return d && Object.prototype.hasOwnProperty.call(d,"value");
        });
}
function validCatalogName(n) {
    return typeof n==="string" && /^[A-Za-z0-9][A-Za-z0-9 _-]{0,31}$/.test(n) && n.trim()===n;
}
function validatedCatalog(input, defaults, calibration) {
    try {
        if (!exactFields(input,["schema","nextId","rows"]) || input.schema!==catalogSchema ||
            !Number.isSafeInteger(input.nextId)||input.nextId<1 ||
            !Array.isArray(input.rows)||input.rows.length>catalogLimit ||
            Reflect.ownKeys(input.rows).length!==input.rows.length+1) return null;
        const ids=new Set(), names=new Set(), rows=[];
        for(let i=0;i<input.rows.length;i++){
            const descriptor=Object.getOwnPropertyDescriptor(input.rows,String(i));
            if(!descriptor||!Object.prototype.hasOwnProperty.call(descriptor,"value"))return null;
            const row=descriptor.value;
            if(!row||Object.getPrototypeOf(row)!==Object.prototype)return null;
            const exec=Object.getOwnPropertyDescriptor(row,"execution");
            if(!exec||!Object.prototype.hasOwnProperty.call(exec,"value"))return null;
            const fixed=exec.value==="fixed";
            if(!exactFields(row,["id","name","favorite","execution",fixed?"kind":"plan"])||
                (!fixed&&row.execution!=="configured")||typeof row.id!=="string"||
                !validCatalogName(row.name)||typeof row.favorite!=="boolean")return null;
            const seed=defaults.find(d=>d.id===row.id);
            const match=/^user-([1-9][0-9]*)$/.exec(row.id);
            if(!seed&&(!match||!Number.isSafeInteger(Number(match[1]))||Number(match[1])>=input.nextId))return null;
            const name=row.name.toLowerCase();
            if(ids.has(row.id)||names.has(name))return null;
            ids.add(row.id);names.add(name);
            const core={id:row.id,name:row.name,favorite:row.favorite,execution:row.execution};
            if(fixed){
                if(!seed||seed.execution!=="fixed"||row.kind!==seed.kind)return null;
                rows.push(Object.assign(core,{kind:row.kind}));
            }else{
                if(seed&&seed.execution!=="configured")return null;
                const draft=calibration.workshopDraftFromPlan(row.plan);
                if(!draft)return null;
                rows.push(Object.assign(core,{plan:calibration.workshopPlanFromDraft(draft)}));
            }
        }
        return {schema:catalogSchema,nextId:input.nextId,rows:rows};
    } catch (_) {return null;}
}
function newCatalog(defaults,calibration) {
    return validatedCatalog({schema:catalogSchema,nextId:1,rows:defaults},defaults,calibration);
}
function editCatalog(input,edit,defaults,calibration) {
    const doc=validatedCatalog(input,defaults,calibration);
    if(!doc||!edit||Object.getPrototypeOf(edit)!==Object.prototype)return null;
    const kind=Object.getOwnPropertyDescriptor(edit,"action");
    if(!kind||!Object.prototype.hasOwnProperty.call(kind,"value"))return null;
    if(kind.value==="create"){
        if(!exactFields(edit,["action","name","plan","favorite"])||
            doc.rows.length>=catalogLimit||doc.nextId>=Number.MAX_SAFE_INTEGER)return null;
        doc.rows.push({id:"user-"+doc.nextId++,name:edit.name,plan:edit.plan,
            favorite:edit.favorite,execution:"configured"});
    }else{
        const action=kind.value;
        const keys=action==="favorite"?["action","id","favorite"]:
            action==="rename"?["action","id","name"]:
            action==="replace"?["action","id","plan"]:action==="remove"?["action","id"]:null;
        if(!keys||!exactFields(edit,keys))return null;
        const index=doc.rows.findIndex(r=>r.id===edit.id);
        if(index<0)return null;
        const row=doc.rows[index];
        if(action==="remove")doc.rows.splice(index,1);
        else if(action==="favorite")row.favorite=edit.favorite;
        else if(action==="rename")row.name=edit.name;
        else if(row.execution==="configured")row.plan=edit.plan;
        else return null;
    }
    return validatedCatalog(doc,defaults,calibration);
}
function queueProjection(row,calibration) {
    if(!row||row.execution!=="configured"||!validCatalogName(row.name))return null;
    const draft=calibration.workshopDraftFromPlan(row.plan);
    return draft?{name:row.name,plan:calibration.workshopPlanFromDraft(draft)}:null;
}
