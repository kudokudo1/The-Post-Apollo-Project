// Local catalog only. No profile application or permission.
const SCHEMA="post-apollo-cpuplus-profiles-v1";
const V2="post-apollo-cpuplus-profiles-v2";
const RESERVED=["BALANCED","DEVELOPMENT","GAMING","LOCAL AI","STABILITY","CUSTOM"];
function exact(o,keys){return o!==null&&typeof o==="object"&&!Array.isArray(o)&&Object.keys(o).length===keys.length&&keys.every(k=>Object.prototype.hasOwnProperty.call(o,k));}
function name(s){return typeof s==="string"&&/^[A-Za-z0-9][A-Za-z0-9 _-]{0,31}$/.test(s)&&s.trim()===s&&!RESERVED.includes(s.toUpperCase());}
function targets(v){return exact(v,["capacityGiB","swappiness"])
    &&(v.capacityGiB===null||Number.isSafeInteger(v.capacityGiB)&&v.capacityGiB>=0&&v.capacityGiB<=64&&v.capacityGiB%4===0)
    &&(v.swappiness===null||Number.isSafeInteger(v.swappiness)&&v.swappiness>=0&&v.swappiness<=200)
    &&(v.capacityGiB!==null||v.swappiness!==null);}
function int(v,min,max){return Number.isSafeInteger(v)&&v>=min&&v<=max;}
function hint(v,zram){return typeof v==="string"&&/^\/[A-Za-z0-9_./ -]{1,255}$/.test(v)
    &&!v.split("/").slice(1).some(x=>["",".",".."].includes(x))
    &&(!zram||/^\/dev\/zram[0-9]{1,6}$/.test(v));}
function empty(){return {capacityGiB:null,swappiness:null,zram:null,priority:null,advanced:null};}
function emptyAdvanced(){return {cachePressure:null,background:null,writer:null,writebackCentisecs:null,expireCentisecs:null};}
function pair(v){return exact(v,["unit","value"])&&["%","B"].includes(v.unit)
    &&int(v.value,1,v.unit==="%"?100:Number.MAX_SAFE_INTEGER);}
function advanced(v){return exact(v,Object.keys(emptyAdvanced()))
    &&Object.keys(v).some(k=>v[k]!==null)
    &&["cachePressure","writebackCentisecs","expireCentisecs"].every(k=>v[k]===null||int(v[k],0,Number.MAX_SAFE_INTEGER))
    &&["background","writer"].every(k=>v[k]===null||pair(v[k]));}
function validDraft(v){
    return exact(v,Object.keys(empty()))
        &&(v.capacityGiB===null||int(v.capacityGiB,0,64)&&v.capacityGiB%4===0)
        &&(v.swappiness===null||int(v.swappiness,0,200))
        &&(v.zram===null||exact(v.zram,["deviceHint","sizeKiB","algorithm"])&&hint(v.zram.deviceHint,true)
            &&int(v.zram.sizeKiB,1,Number.MAX_SAFE_INTEGER)&&typeof v.zram.algorithm==="string"&&/^[A-Za-z0-9_-]{1,64}$/.test(v.zram.algorithm))
        &&(v.priority===null||exact(v.priority,["deviceHint","sizeKiB","value"])&&hint(v.priority.deviceHint,false)
            &&int(v.priority.sizeKiB,1,Number.MAX_SAFE_INTEGER)&&int(v.priority.value,0,32767))
        &&(v.advanced===null||advanced(v.advanced));
}
function validTargets(v,schema){return schema===V2?validDraft(v)&&Object.keys(v).some(k=>v[k]!==null):targets(v);}
function copyPair(v){return v===null?null:{unit:v.unit,value:v.value};}
function copyTargets(v,schema=SCHEMA){
    const base={capacityGiB:v.capacityGiB,swappiness:v.swappiness};
    if(schema!==V2)return base;
    const a=v.advanced;
    return Object.assign(base,{
        zram:v.zram===null?null:{deviceHint:v.zram.deviceHint,sizeKiB:v.zram.sizeKiB,algorithm:v.zram.algorithm},
        priority:v.priority===null?null:{deviceHint:v.priority.deviceHint,sizeKiB:v.priority.sizeKiB,value:v.priority.value},
        advanced:a===null?null:{cachePressure:a.cachePressure,background:copyPair(a.background),writer:copyPair(a.writer),
            writebackCentisecs:a.writebackCentisecs,expireCentisecs:a.expireCentisecs}});
}
function capture(d,key,value){
    if(!validDraft(d)||!Object.keys(empty()).includes(key))return null;
    const next=Object.assign({},d,{[key]:value});
    return validDraft(next)?copyTargets(next,V2):null;
}
function captureAdvanced(d,key,unit,value){
    if(!validDraft(d)||!Object.keys(emptyAdvanced()).includes(key))return null;
    const expected=key==="background"||key==="writer"?["%","B"]:key==="cachePressure"?["RAW"]:["cs"];
    if(!expected.includes(unit))return null;
    const a=Object.assign({},d.advanced||emptyAdvanced(),{[key]:expected.length===2?{unit,value}:value});
    return capture(d,"advanced",a);
}
function extendedSummary(d){
    if(!validDraft(d))return "EXTENDED TARGETS UNAVAILABLE";
    const a=d.advanced;
    const lines=[
        "ZRAM // "+(d.zram?d.zram.deviceHint+" / "+d.zram.algorithm:"NOT SET"),
        "SWAP PRIORITY // "+(d.priority?d.priority.deviceHint+" / "+d.priority.value:"NOT SET")];
    if(d.zram)lines.push("ZRAM SAVED SIZE // "+d.zram.sizeKiB+" KiB");
    if(d.priority)lines.push("PRIORITY SAVED SIZE // "+d.priority.sizeKiB+" KiB");
    const label=(v)=>v===null?"NOT SET":v.value+" "+v.unit;
    lines.push("CACHE PRESSURE // "+(a&&a.cachePressure!==null?a.cachePressure:"NOT SET"));
    lines.push("BACKGROUND WRITEBACK // "+(a?label(a.background):"NOT SET"));
    lines.push("WRITER WRITEBACK // "+(a?label(a.writer):"NOT SET"));
    lines.push("FLUSH INTERVAL // "+(a&&a.writebackCentisecs!==null?a.writebackCentisecs+" cs":"NOT SET"));
    lines.push("DIRTY DATA AGE // "+(a&&a.expireCentisecs!==null?a.expireCentisecs+" cs":"NOT SET"));
    return lines.join("\n");
}
function document(v){
    if(!exact(v,["schema","revision","profiles"])||![SCHEMA,V2].includes(v.schema)||!Number.isSafeInteger(v.revision)||v.revision<0
        ||!Array.isArray(v.profiles)||v.profiles.length>16)return null;
    const seen=new Set(),rows=[];
    for(const row of v.profiles){
        if(!exact(row,["name","targets"])||!name(row.name)||!validTargets(row.targets,v.schema)||seen.has(row.name.toUpperCase()))return null;
        seen.add(row.name.toUpperCase());rows.push({name:row.name,targets:copyTargets(row.targets,v.schema)});
    }
    return {schema:v.schema,revision:v.revision,profiles:rows};
}
function create(base,n,v){
    const b=document(base);
    if(!b||b.revision===Number.MAX_SAFE_INTEGER||b.profiles.length>=16||!name(n)||!validTargets(v,b.schema)
        ||b.profiles.some(x=>x.name.toUpperCase()===n.toUpperCase()))return null;
    const request={action:"create",expectedRevision:b.revision,name:n,targets:copyTargets(v,b.schema)};
    if(b.schema===V2)request.schema=V2;
    return request;
}
function change(base,action,n,value){
    const b=document(base);
    if(!b||b.revision===Number.MAX_SAFE_INTEGER||!name(n)||!["edit","rename","delete"].includes(action))return null;
    const row=b.profiles.find(x=>x.name===n);
    if(!row)return null;
    const request={action:action,expectedRevision:b.revision,name:n};
    if(action==="edit"){
        if(!validTargets(value,b.schema))return null;
        request.targets=copyTargets(value,b.schema);
    }else if(action==="rename"){
        if(!name(value)||value===n||b.profiles.some(x=>x.name!==n&&x.name.toUpperCase()===value.toUpperCase()))return null;
        request.newName=value;
    }else if(value!==null)return null;
    if(b.schema===V2)request.schema=V2;
    return request;
}
function expectedDocument(base,request){
    const b=document(base);
    if(!b||!request)return null;
    let expected;
    if(request.action==="create")expected=create(b,request.name,request.targets);
    else if(request.action==="edit")expected=change(b,"edit",request.name,request.targets);
    else if(request.action==="rename")expected=change(b,"rename",request.name,request.newName);
    else if(request.action==="delete")expected=change(b,"delete",request.name,null);
    else return null;
    if(!expected||!exact(request,Object.keys(expected))
        ||!Object.keys(expected).every(k=>k==="targets"
            ? validTargets(request.targets,b.schema)&&JSON.stringify(copyTargets(request.targets,b.schema))===JSON.stringify(expected.targets)
            :request[k]===expected[k]))return null;
    let rows=b.profiles;
    if(request.action==="create")rows=rows.concat([{name:expected.name,targets:expected.targets}]);
    else if(request.action==="edit")rows=rows.map(x=>x.name===expected.name?{name:x.name,targets:expected.targets}:x);
    else if(request.action==="rename")rows=rows.map(x=>x.name===expected.name?{name:expected.newName,targets:x.targets}:x);
    else rows=rows.filter(x=>x.name!==expected.name);
    return {schema:b.schema,revision:b.revision+1,profiles:rows};
}
function accepted(raw,request,base){
    if(typeof raw!=="string"||raw.length>16385||!raw.endsWith("\n"))return null;
    let parsed;
    try{parsed=JSON.parse(raw);}catch(_){return null;}
    const result=document(parsed);
    // The private child emits a single compact ASCII JSON frame in canonical
    // field order. Reject duplicate keys, extra frames and malformed output.
    if(!result||JSON.stringify(result)+"\n"!==raw)return null;
    if(exact(request,["action"])&&request.action==="list")return result.schema===SCHEMA?result:null;
    if(exact(request,["action","schema"])&&request.action==="list"&&request.schema===V2)return result.schema===V2?result:null;
    const next=expectedDocument(base,request);
    return next!==null&&JSON.stringify(next)===JSON.stringify(result)?result:null;
}
