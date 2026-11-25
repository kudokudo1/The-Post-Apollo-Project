// Local catalog only. No profile application or permission.
const SCHEMA="post-apollo-cpuplus-profiles-v1";
const RESERVED=["BALANCED","DEVELOPMENT","GAMING","LOCAL AI","STABILITY","CUSTOM"];
function exact(o,keys){return o!==null&&typeof o==="object"&&!Array.isArray(o)&&Object.keys(o).length===keys.length&&keys.every(k=>Object.prototype.hasOwnProperty.call(o,k));}
function name(s){return typeof s==="string"&&/^[A-Za-z0-9][A-Za-z0-9 _-]{0,31}$/.test(s)&&s.trim()===s&&!RESERVED.includes(s.toUpperCase());}
function targets(v){return exact(v,["capacityGiB","swappiness"])
    &&(v.capacityGiB===null||Number.isSafeInteger(v.capacityGiB)&&v.capacityGiB>=0&&v.capacityGiB<=64&&v.capacityGiB%4===0)
    &&(v.swappiness===null||Number.isSafeInteger(v.swappiness)&&v.swappiness>=0&&v.swappiness<=200)
    &&(v.capacityGiB!==null||v.swappiness!==null);}
function copyTargets(v){return {capacityGiB:v.capacityGiB,swappiness:v.swappiness};}
function document(v){
    if(!exact(v,["schema","revision","profiles"])||v.schema!==SCHEMA||!Number.isSafeInteger(v.revision)||v.revision<0
        ||!Array.isArray(v.profiles)||v.profiles.length>16)return null;
    const seen=new Set(),rows=[];
    for(const row of v.profiles){
        if(!exact(row,["name","targets"])||!name(row.name)||!targets(row.targets)||seen.has(row.name.toUpperCase()))return null;
        seen.add(row.name.toUpperCase());rows.push({name:row.name,targets:copyTargets(row.targets)});
    }
    return {schema:SCHEMA,revision:v.revision,profiles:rows};
}
function create(base,n,v){
    const b=document(base);
    if(!b||b.revision===Number.MAX_SAFE_INTEGER||b.profiles.length>=16||!name(n)||!targets(v)
        ||b.profiles.some(x=>x.name.toUpperCase()===n.toUpperCase()))return null;
    return {action:"create",expectedRevision:b.revision,name:n,targets:copyTargets(v)};
}
function accepted(raw,request,base){
    if(typeof raw!=="string"||raw.length>16385||!raw.endsWith("\n"))return null;
    let parsed;
    try{parsed=JSON.parse(raw);}catch(_){return null;}
    const result=document(parsed);
    // The private child emits a single compact ASCII JSON frame in canonical
    // field order. Reject duplicate keys, extra frames and malformed output.
    if(!result||JSON.stringify(result)+"\n"!==raw)return null;
    if(exact(request,["action"])&&request.action==="list")return result;
    const b=document(base);
    if(!b||!request||request.action!=="create"||!exact(request,["action","expectedRevision","name","targets"]))return null;
    const expected=create(b,request.name,request.targets);
    if(!expected||expected.expectedRevision!==request.expectedRevision)return null;
    const next={schema:SCHEMA,revision:b.revision+1,profiles:b.profiles.concat([{name:expected.name,targets:expected.targets}])};
    return JSON.stringify(next)===JSON.stringify(result)?result:null;
}
