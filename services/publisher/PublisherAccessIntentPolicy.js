.pragma library

// SocialW Publisher P1.5: LOCAL ACCOUNT ACCESS INTENTS, NEVER AUTHORITY.
// Identities are layout labels; account aliases are unverified user labels.
// Real permits require a separate host-owned, signed, revocable broker grant.
var VERSION = 1;
var MAX_RECORDS = 150;
var MAX_BYTES = 200000;
var MAX_ID = 1000000000;
var PROVIDERS = {
    "discord":["post.text","post.image"],
    "bluesky":["post.text","post.image"],
    "youtube":["post.video"],
    "tiktok":["post.video","post.image"],
    "facebook-page":["post.text","post.image","post.video"],
    "instagram":["post.image","post.video"],
    "website":["post.text","post.image","post.video"]
};
var CONTEXTS = ["personal","organization"];

function emptyDocument() {return {version:VERSION,nextId:1,intents:[]};}
function plain(v) {
    return v !== null && typeof v === "object" && !Array.isArray(v)
        && Object.prototype.toString.call(v) === "[object Object]";
}
function exact(v, keys) {
    if (!plain(v)) return false;
    var one=Object.keys(v).sort(),two=keys.slice().sort();
    return one.length===two.length && one.every(function(k,i){return k===two[i];});
}
function numberIn(v,low,high) {
    return typeof v === "number" && isFinite(v)
        && Math.floor(v) === v && v >= low && v <= high;
}
function validIdentity(v) {
    return typeof v === "string" && /^identity-[1-9][0-9]*$/.test(v)
        && numberIn(Number(v.slice(9)),1,MAX_ID);
}
function validAlias(v) {
    return typeof v === "string" && v.length > 0 && v.length <= 80
        && v.trim() === v && !/[\x00-\x1f\x7f]/.test(v);
}
function validScope(provider,scope) {
    return Object.prototype.hasOwnProperty.call(PROVIDERS,provider)
        && PROVIDERS[provider].indexOf(scope) !== -1;
}
function validIntent(item) {
    return exact(item,["id","identityId","context","provider",
                       "accountAlias","scope","status","createdAtMs","updatedAtMs"])
        && typeof item.id === "string" && /^r[1-9][0-9]*$/.test(item.id)
        && numberIn(Number(item.id.slice(1)),1,MAX_ID)
        && validIdentity(item.identityId) && CONTEXTS.indexOf(item.context) !== -1
        && validAlias(item.accountAlias) && validScope(item.provider,item.scope)
        && (item.status === "requested" || item.status === "withdrawn")
        && numberIn(item.createdAtMs,1,Number.MAX_SAFE_INTEGER)
        && numberIn(item.updatedAtMs,item.createdAtMs,Number.MAX_SAFE_INTEGER);
}
function validate(doc) {
    if (!plain(doc)) return {ok:false,reason:"INVALID_DOCUMENT"};
    if (doc.version !== VERSION) return {ok:false,reason:"UNSUPPORTED_VERSION"};
    if (!exact(doc,["version","nextId","intents"]))
        return {ok:false,reason:"UNKNOWN_FIELDS"};
    if (!numberIn(doc.nextId,1,MAX_ID)) return {ok:false,reason:"INVALID_SEQUENCE"};
    if (!Array.isArray(doc.intents)||doc.intents.length > MAX_RECORDS)
        return {ok:false,reason:"INTENT_CAPACITY"};
    var ids={},seen={},high=0;
    for(var i=0;i<doc.intents.length;i++){
        var item=doc.intents[i];
        if(!validIntent(item))return {ok:false,reason:"INVALID_INTENT"};
        if(Object.prototype.hasOwnProperty.call(ids,item.id))
            return {ok:false,reason:"DUPLICATE_INTENT_ID"};
        ids[item.id]=true; high=Math.max(high,Number(item.id.slice(1)));
        if(item.status === "requested"){
            var key=JSON.stringify([item.identityId,item.context,item.provider,
                                    item.accountAlias,item.scope]);
            if(Object.prototype.hasOwnProperty.call(seen,key))
                return {ok:false,reason:"DUPLICATE_ACTIVE_INTENT"};
            seen[key]=true;
        }
    }
    if(high>=doc.nextId)return {ok:false,reason:"SEQUENCE_REWIND"};
    if(JSON.stringify(doc).length > MAX_BYTES)
        return {ok:false,reason:"DOCUMENT_TOO_LARGE"};
    return {ok:true,reason:""};
}
function parse(raw){
    if(typeof raw!=="string" ||raw.length===0||raw.length>MAX_BYTES)
        return {ok:false,reason:"INVALID_SOURCE"};
    var data;
    try{data=JSON.parse(raw);}catch(e){return {ok:false,reason:"MALFORMED_JSON"};}
    var v=validate(data);
    return v.ok?{ok:true,document:data}:v;
}
function clone(doc){
    return {version:VERSION,nextId:doc.nextId,intents:doc.intents.map(function(r){
        return {id:r.id,identityId:r.identityId,context:r.context,
                provider:r.provider,accountAlias:r.accountAlias,
                scope:r.scope,status:r.status,
                createdAtMs:r.createdAtMs,updatedAtMs:r.updatedAtMs};
    })};
}
function request(doc,identityId,context,provider,accountAlias,scope,now){
    var v=validate(doc);
    if(!v.ok)return v;
    if(!validIdentity(identityId)||CONTEXTS.indexOf(context)===-1
       ||!validScope(provider,scope)||!validAlias(accountAlias)
       ||!numberIn(now,1,Number.MAX_SAFE_INTEGER))
        return {ok:false,reason:"INVALID_ACCOUNT_INTENT"};
    var duplicate=doc.intents.find(function(r){
        return r.status==="requested" && r.identityId===identityId
            && r.context===context && r.provider===provider
            && r.accountAlias===accountAlias && r.scope===scope;
    });
    if(duplicate)return {ok:true,unchanged:true,intentId:duplicate.id};
    if(doc.intents.length>=MAX_RECORDS||doc.nextId>=MAX_ID)
        return {ok:false,reason:"INTENT_CAPACITY"};
    var next=clone(doc),id="r"+next.nextId++;
    next.intents.push({id:id,identityId:identityId,context:context,provider:provider,
        accountAlias:accountAlias,scope:scope,status:"requested",
        createdAtMs:now,updatedAtMs:now});
    return {ok:true,document:next,intentId:id};
}
function withdraw(doc,id,now){
    var v=validate(doc);
    if(!v.ok)return v;
    if(typeof id!=="string"||!numberIn(now,1,Number.MAX_SAFE_INTEGER))
        return {ok:false,reason:"INVALID_WITHDRAWAL"};
    var next=clone(doc),target=next.intents.find(function(r){return r.id===id;});
    if(!target)return {ok:false,reason:"UNKNOWN_INTENT"};
    if(target.status!=="requested")return {ok:false,reason:"NOT_ACTIVE"};
    if(now<target.updatedAtMs)return {ok:false,reason:"STALE_TIME"};
    target.status="withdrawn";
    target.updatedAtMs=now;
    return {ok:true,document:next,intentId:id};
}
function evaluate(requested,receipt) {
    // No user-editable JSON, Social layout, browser login, API key or receipt
    // argument may activate this gate. Later host verification must be added
    // as a separate, reviewed system-owned boundary, NEVER via QML flags.
    if(!plain(requested)||!validIdentity(requested.identityId)
       ||!validScope(requested.provider,requested.scope)
       ||!validAlias(requested.accountAlias))
        return {allowed:false,reason:"INVALID_REQUEST"};
    if(requested.status==="withdrawn")
        return {allowed:false,reason:"INTENT_WITHDRAWN"};
    return {allowed:false,reason:"TRUSTED_PUBLISHING_BROKER_NOT_CONNECTED"};
}
function view(state,doc,error){
    var v=validate(doc),ok=v.ok;
    return {state:state,error:error||"",
        writable:ok&&(state==="ready"||state==="empty"),
        hostConnected:false,canPublish:false,grants:[],
        intents:ok?doc.intents.map(function(r){return Object.assign({},r);}):[]};
}
function scopes(provider){
    return Object.prototype.hasOwnProperty.call(PROVIDERS,provider)
        ? PROVIDERS[provider].slice():[];
}
function providerIds(){return Object.keys(PROVIDERS);}
