// M4s2: detached encrypted portable export/preview. No import authority.
function exact(v, keys) {
    return v!==null && typeof v==="object" && !Array.isArray(v)
        && Object.keys(v).length===keys.length
        && keys.every(function(k){return Object.prototype.hasOwnProperty.call(v,k);});
}
function integer(v,min,max){return Number.isSafeInteger(v)&&v>=min&&v<=max;}
function portableId(v){return typeof v==="string"&&/^banking-[0-9a-f]{32}\.sealed\.json$/.test(v)&&v.length===52;}
function hash(v){return typeof v==="string"&&v.length===64&&/^[0-9a-f]{64}$/.test(v);}
function validPassword(v){
    if(typeof v!=="string"||v.length<12||v.length>1024||/[\x00-\x1f\x7f]/.test(v))return false;
    try {
        // Match Python's Unicode code point minimum and UTF-8 byte maximum.
        var points=v.replace(/[\uD800-\uDBFF][\uDC00-\uDFFF]/g,"x").length;
        return points>=12&&encodeURIComponent(v).replace(/%[0-9A-F]{2}/g,"x").length<=1024;
    } catch(error){return false;}
}
function validIntent(r){
    if(!r)return false;
    if(r.action==="export")return exact(r,["action","expectedRevision","confirmExport"])
        &&integer(r.expectedRevision,1,2147483645)&&r.confirmExport===true;
    if(r.action==="preview")return exact(r,["action","portableId"])&&portableId(r.portableId);
    return false;
}
function candidate(c,action,id){
    if(!c||c.enabled!==true||c.active!==true||c.busy!==false)return null;
    var r=null;
    if(action==="export"&&c.ready===true&&c.dirty===false&&c.localSaved===true)
        r={action:"export",expectedRevision:c.revision,confirmExport:true};
    if(action==="preview")r={action:"preview",portableId:id};
    return validIntent(r)?r:null;
}
function sameIntent(a,b){
    if(!validIntent(a)||!validIntent(b)||a.action!==b.action)return false;
    return a.action==="export"?a.expectedRevision===b.expectedRevision:a.portableId===b.portableId;
}
function frame(intent,password){
    if(!validIntent(intent)||!validPassword(password))return null;
    var r=JSON.parse(JSON.stringify(intent));
    r.password=password;
    return JSON.stringify(r)+"\n";
}
function accept(raw,code,intent){
    if(code!==0||!validIntent(intent)||typeof raw!=="string"||raw.length>4096)return null;
    var prefix="FINANCEW_BANKING_PORTABLE_RESULT ";
    var lines=raw.split(/\r?\n/);
    if(lines.length!==2||lines[1]!==""||!lines[0].startsWith(prefix))return null;
    try {
        var v=JSON.parse(lines[0].slice(prefix.length));
        if(!v||v.source!=="LOCAL_OPERATOR_BANKING_PORTABLE"||v.connected!==false
           ||v.bankVerified!==false||v.action!==intent.action||!portableId(v.portableId)
           ||!hash(v.sha256)||!integer(v.sourceRevision,1,2147483646))return null;
        var base=["source","connected","bankVerified","action","portableId","sha256","sourceRevision"];
        if(v.action==="export"&&exact(v,base.concat(["encrypted"]))&&v.encrypted===true
           &&v.sourceRevision===intent.expectedRevision)
            return {action:v.action,portableId:v.portableId,sha256:v.sha256,sourceRevision:v.sourceRevision};
        if(v.action==="preview"&&exact(v,base.concat(["accountCount","entryCount","ciphertextAuthenticated","originAuthenticated"]))
           &&v.portableId===intent.portableId&&v.ciphertextAuthenticated===true&&v.originAuthenticated===false
           &&integer(v.accountCount,1,12)&&integer(v.entryCount,0,300))
            return {action:v.action,portableId:v.portableId,sha256:v.sha256,sourceRevision:v.sourceRevision,
                accountCount:v.accountCount,entryCount:v.entryCount,ciphertextAuthenticated:true,originAuthenticated:false};
    }catch(error){}
    return null;
}
