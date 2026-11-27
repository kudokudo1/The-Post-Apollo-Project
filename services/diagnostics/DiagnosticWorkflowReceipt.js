// Receipt qualification for the private workflow helper; never dispatches a diagnostic.
function sameValue(a,b) {
    if(a===b)return true;
    if(!a||!b||typeof a!=="object"||typeof b!=="object"||Array.isArray(a)!==Array.isArray(b))return false;
    const ak=Object.keys(a),bk=Object.keys(b);
    return ak.length===bk.length&&ak.every(k=>Object.prototype.hasOwnProperty.call(b,k)&&sameValue(a[k],b[k]));
}
function qualifyReceipt(response, request, validate, seed) {
    try {
        if(!response||Object.getPrototypeOf(response)!==Object.prototype||
            Object.keys(response).sort().join(",")!=="document,status"||!request)return null;
        const status=response.status,raw=response.document;
        if(request.action==="load"&&status==="MISSING"&&raw===null){
            const doc=seed();
            return doc?{status:"READY",document:doc,expected:null}:null;
        }
        if(request.action==="save"&&status==="CONFLICT"){
            if(raw!==null&&!validate(raw))return null;
            return {status:"CONFLICT",document:null,expected:null};
        }
        if(!((request.action==="load"&&status==="LOADED")||(request.action==="save"&&status==="SAVED")))return null;
        const doc=validate(raw);
        if(!doc)return null;
        if(request.action==="save"&&!sameValue(raw,request.document))return null;
        return {status:"READY",document:doc,expected:JSON.parse(JSON.stringify(raw))};
    }catch(_){return null;}
}
