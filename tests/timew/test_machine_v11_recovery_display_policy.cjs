// M11 display policy: no actions, strict identity and request correlation.
const fs = require("fs"), path = require("path"), vm = require("vm"), assert = require("assert");
const root = path.resolve(__dirname, "../..");
const ctx = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(root, "services/time/MachineV3LocalSaveRecoveryPolicy.js"),
    "utf8").replace(/^\.pragma library\s*/, ""), ctx);
const request = "11111111-1111-4111-8111-111111111111";
const cid = "22222222-2222-4222-8222-222222222222";
const aid = "33333333-3333-4333-8333-333333333333";
const token2 = "44444444-4444-4444-8444-444444444444";
const ordinary = ctx.MATCH, exact = ctx.EXACT;
let checks = 0;
function check(value, msg) { assert(value, msg); checks++; }
function packet(status, o=null, f=null, a=null) {
    const p = {kind:ctx.KIND, request_id:request, mode:"inspect", checkpoint_id:cid,
        status, ordinary_status:o, fractional_status:f, fractional_attempt_id:a,
        count:0, intent_ids:[], read_only:true, local_data_only:true,
        manual_review_required:true, safe_actions:[]};
    ctx.DENIALS.forEach(k => p[k] = false);
    return p;
}
function accept(p, token=request, mode="inspect", key=cid) {
    return ctx.accept(p, token, mode, key);
}
function reject(p, token=request, mode="inspect", key=cid) {
    const r = accept(p, token, mode, key);
    check(r.valid === false && r.status === "RECOVERY UNAVAILABLE // HOLD", "refusal");
    check(r.intentIds.length === 0 && r.ordinary === "UNKNOWN" && r.fractional === "UNKNOWN", "no stale data");
}
const states = [
    [packet("COORDINATED_SAVE_UNKNOWN_HOLD"), "UNKNOWN // HOLD", "UNKNOWN", "UNKNOWN"],
    ...Array.from(ctx.ORDINARY).map((s,i) => [
        packet("ORDINARY_SAVE_UNRESOLVED_HOLD",s), "ORDINARY SAVE // HOLD",
        ["PREPARED // NO PAIR OBSERVED","MARKED // NO PAIR OBSERVED","CONFLICT","UNKNOWN"][i], "NOT VERIFIED"]),
    [packet("ORDINARY_OBSERVED_FRACTIONAL_UNLINKED_HOLD",ordinary), "PARTIAL // HOLD","LOCAL PAIR OBSERVED","UNLINKED"],
    [packet("FRACTIONAL_LINK_CONFLICT_HOLD",ordinary,null,aid), "CONFLICT // HOLD","LOCAL PAIR OBSERVED","LINK CONFLICT"],
    ...Array.from(ctx.FRACTIONAL).map((f,i)=>[
        packet("ORDINARY_OBSERVED_FRACTIONAL_UNRESOLVED_HOLD",ordinary,f,aid), "PARTIAL // HOLD",
        "LOCAL PAIR OBSERVED", ["ROWS OBSERVED // UNRESOLVED","NO ROWS OBSERVED","CONFLICT","CONFLICT","CONFLICT","UNKNOWN"][i]]),
    [packet("COORDINATED_LOCAL_RECORDS_OBSERVED_UNTRUSTED",ordinary,exact,aid),
        "LOCAL RECORDS OBSERVED // HOLD","LOCAL PAIR OBSERVED","LOCAL ROWS OBSERVED"]
];
for (const [p, status, o, f] of states) {
    const r=accept(p);
    check(r.valid && r.status===status && r.ordinary===o && r.fractional===f, "mapping");
    check(Object.keys(r).sort().join(",")==="detail,fractional,intentIds,ordinary,status,valid","display only");
    for (const flag of ctx.DENIALS) {
        reject({...p,[flag]:true});
        reject({...p,[flag]:0});
    }
    reject({...p,checkpoint_id:aid});
    reject({...p,request_id:token2});
    reject(p,token2);
    reject({...p,safe_actions:["retry"]});
    reject({...p,reason:"private"});
    reject({...p,read_only:1});
    reject({...p,local_data_only:false});
    reject({...p,manual_review_required:false});
    reject({...p,kind:"future"});
    reject({...p,count:1});
    reject({...p,fractional_attempt_id:"bad"});
}
const match=states[states.length-1][0];
for (const k of Object.keys(match)) {
    const bad={...match}; delete bad[k]; reject(bad);
}
for (const bad of [
    {...match,ordinary_status:null}, {...match,fractional_status:null},
    {...match,fractional_attempt_id:null}, {...match,status:"SAVED"},
    {...match,status:"ORDINARY_OBSERVED_FRACTIONAL_UNLINKED_HOLD"},
    {...match,status:"ORDINARY_SAVE_UNRESOLVED_HOLD"},
    {...match,status:"FRACTIONAL_LINK_CONFLICT_HOLD"},
    {...match,status:"COORDINATED_SAVE_UNKNOWN_HOLD"},
    {...match,status:"UNAVAILABLE_HOLD"}, null, []
]) reject(bad);
function list(ids, status="LOCAL_INTENTS_OBSERVED") {
    return {...packet(status), mode:"list", checkpoint_id:null, count:ids.length,intent_ids:ids};
}
const p=list([cid,aid]);
const r=accept(p,request,"list",null);
check(r.valid && r.intentIds.join()=== [cid,aid].join(),"bounded list");
check(accept(list([],"NO_LOCAL_INTENTS_OBSERVED"),request,"list",null).valid,"empty list");
for (const bad of [list([]),list([aid,cid]),list([cid,cid]),list(["bad"]),
    list(Array(65).fill(cid)),list([cid],"NO_LOCAL_INTENTS_OBSERVED"),
    {...p,ordinary_status:ordinary},{...p,count:"2"},{...p,checkpoint_id:cid},
    {...p,request_id:token2},{...p,status:"UNAVAILABLE_HOLD"}])
    reject(bad,request,"list",null);
reject(p,request,"inspect",cid);
reject(p,request,"list",cid);
console.log("TIMEW M11 RECOVERY DISPLAY POLICY // " + checks + " display-only checks PASS");
