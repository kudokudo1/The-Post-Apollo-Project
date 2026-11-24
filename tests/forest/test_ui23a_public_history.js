const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const {execFileSync} = require("node:child_process");
const root = path.resolve(__dirname,"../..");
const policy = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(root,"widgets/forest/ui2/PublicHistoryDisplay.js"),"utf8"),policy);
const ref = {requestId:"fixture_request_001",treeKey:"CHERRY",generation:1,
    sessionId:"demo",revision:4,after:0,limit:2};
const row = {turn_id:"turn-a",ordinal:1,role:"user",text:"Public\nquestion\t🌲"};
const frame = rows => ({schema:"postapollo.forest.public-history-display.v1",
    requestId:ref.requestId,treeKey:ref.treeKey,generation:ref.generation,
    sessionId:ref.sessionId,revision:ref.revision,messages:rows,complete:false});
let count=0;
function check(name, fn) {fn(); count++; console.log("PASS",name);}
function denied(f, r=ref,c=r) {
    const p=policy.project(f,r,c);
    assert.equal(p.state,"UNAVAILABLE"); assert.equal(p.messages.length,0);
    assert.equal(p.nextAfter,null); assert.equal(p.sourceAuthenticated,false);
    assert.equal(p.permissionGranted,false); assert.equal(p.safeActions.length,0);
}
check("actual M4 producer interoperability and explicit pagination",()=>{
    const pages=JSON.parse(execFileSync("python3",["-B",path.join(__dirname,"ui2_m4_public_fixture.py")],{encoding:"utf8"}));
    const a=policy.project(pages[0].frame,pages[0].ref,pages[0].ref);
    const b=policy.project(pages[1].frame,pages[1].ref,pages[1].ref);
    assert.equal(a.state,"STRUCTURALLY_VALID_PUBLIC_FIXTURE");
    assert.equal(a.nextAfter,1); assert.equal(a.complete,false);
    assert.equal(a.messages[0].direction,"outgoing");
    assert.equal(b.state,"STRUCTURALLY_VALID_PUBLIC_FIXTURE");
    assert.equal(b.messages[0].direction,"incoming");
    assert.equal(b.messages[0].body,"Public reply\nsecond line 🌲");
    assert.equal(b.complete,true); assert.equal(b.nextAfter,null);
    assert.notEqual(pages[0].ref.requestId,pages[1].ref.requestId);
    assert.equal(a.sourceAuthenticated,false); assert.equal(b.permissionGranted,false);
    denied(pages[0].frame,pages[1].ref);
});
check("fresh copied plain-text projection",()=>{
    const f=frame([row]); const p=policy.project(f,ref,ref);
    assert.equal(p.messages[0].body,row.text); assert.equal(p.nextAfter,1);
    p.messages[0].body="mutated"; assert.equal(f.messages[0].text,"Public\nquestion\t🌲");
    assert.equal(p.safeActions.length,0);
});
check("stale generation",()=>denied(frame([row]),ref,{...ref,generation:2}));
check("stale request",()=>denied(frame([row]),ref,{...ref,requestId:"fixture_request_002"}));
check("cross Tree",()=>denied(frame([row]),ref,{...ref,treeKey:"MAPLE"}));
check("cross session",()=>denied(frame([row]),ref,{...ref,sessionId:"other"}));
check("changed revision",()=>denied(frame([row]),ref,{...ref,revision:5}));
check("changed cursor",()=>denied(frame([row]),ref,{...ref,after:1}));
check("changed limit",()=>denied(frame([row]),ref,{...ref,limit:1}));
check("unknown envelope field",()=>denied({...frame([row]),owner_key:"other"}));
check("unknown row field",()=>denied(frame([{...row,model:"model"}])));
check("invalid role",()=>denied(frame([{...row,role:"tool"}])));
check("duplicate ID",()=>denied(frame([row,{...row,ordinal:2}])));
check("ordinal gap",()=>denied(frame([{...row,ordinal:2}])));
check("row limit",()=>denied(frame([row,{...row,turn_id:"b",ordinal:2},{...row,turn_id:"c",ordinal:3}])));
check("empty incomplete",()=>denied(frame([])));
check("complete empty history",()=>{
    const r={...ref,revision:0};
    const p=policy.project({...frame([]),revision:0,complete:true},r,r);
    assert.equal(p.state,"STRUCTURALLY_VALID_PUBLIC_FIXTURE");assert.equal(p.complete,true);
});
check("complete may precede revision because revision is not turn count",()=>{
    const p=policy.project({...frame([row]),complete:true},ref,ref);
    assert.equal(p.state,"STRUCTURALLY_VALID_PUBLIC_FIXTURE");assert.equal(p.nextAfter,null);
});
check("incomplete cannot exceed revision",()=>{
    const r={...ref,revision:1};denied({...frame([row]),revision:1},r);
});
check("UTF8 row bound",()=>denied(frame([{...row,text:"🌲".repeat(4001)}])));
check("invalid surrogate",()=>denied(frame([{...row,text:String.fromCharCode(0xd800)}])));
check("controls and bidi",()=>{for(const x of [0,13,0x7f,0x202e,0x2066])denied(frame([{...row,text:"x"+String.fromCharCode(x)}]));});
check("trailing newline in ID",()=>denied(frame([{...row,turn_id:"turn-a\n"}])));
check("candidate compact JSON byte cap",()=>{
    const r={...ref,revision:6,limit:6};
    const rows=Array.from({length:6},(_,i)=>({...row,turn_id:"turn-"+i,ordinal:i+1,text:"é".repeat(8000)}));
    denied({...frame(rows),revision:6,complete:true},r);
});
check("whole snapshot refusal",()=>denied(frame([row,{...row,turn_id:"b",ordinal:2,text:""}])));
console.log(count+" checks passed (public M4 projection only)");
