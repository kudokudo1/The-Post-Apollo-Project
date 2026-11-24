const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const {execFileSync} = require("node:child_process");
const root = path.resolve(__dirname,"../..");
const p=vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(root,"widgets/forest/ui2/PublicHistoryDisplay.js"),"utf8"),p);
const scope={treeKey:"CHERRY",generation:1,sessionId:"demo",revision:10,viewKey:"local-view-a"};
const id=n=>"fixture_request_"+String(n).padStart(4,"0");
const row=(n,body="Public "+n)=>({turn_id:"turn-"+n,ordinal:n,role:n%2?"user":"assistant",text:body});
function frame(request,rows,complete=false) {
    const {after,limit,...fields}=request;
    return {schema:"postapollo.forest.public-history-display.v1",...fields,messages:rows,complete};
}
function opened(v=scope,limit=2) { const c=p.createController(); const o=c.open(v,id(1),limit); assert.equal(o.state,"PENDING"); return [c,o.request]; }
function partial(v=scope) { const [c,r]=opened(v); assert.equal(c.receive(frame(r,[row(1),row(2)]),v).state,"PARTIAL"); return c; }
function empty(o,state="UNAVAILABLE") {
    assert.equal(o.state,state); assert.equal(o.messages.length,0); assert.equal(o.request,null);
    assert.equal(o.nextAfter,null); assert.equal(o.sourceAuthenticated,false); assert.equal(o.permissionGranted,false);
    assert.equal(o.safeActions.length,0);
}
let count=0;
function check(name,fn){fn();count++;console.log("PASS",name);}
check("actual M4 pages accumulate with explicit continuation",()=>{
    const pages=JSON.parse(execFileSync("python3",["-B",path.join(__dirname,"ui2_m4_public_fixture.py")],{encoding:"utf8"}));
    const {requestId,after,limit,...view}=pages[0].ref;
    const v={...view,viewKey:"local-m4"};
    const c=p.createController();
    const a=c.open(v,requestId,limit);
    assert.equal(a.request.after,0);
    const first=c.receive(pages[0].frame,v);
    assert.equal(first.state,"PARTIAL");assert.equal(first.request,null);assert.equal(first.nextAfter,1);
    const b=c.next(v,pages[1].ref.requestId,1);
    assert.equal(b.request.after,1);
    const done=c.receive(pages[1].frame,v);
    assert.equal(done.state,"COMPLETE");assert.equal(done.messages.length,2);
    assert.equal(done.messages[1].body,"Public reply\nsecond line 🌲");
    assert.equal(done.nextAfter,null);assert.equal(done.permissionGranted,false);
});
check("default closed",()=>empty(p.createController().observe(scope),"CLOSED"));
check("no automatic request after partial",()=>{const c=partial();const o=c.observe(scope);assert.equal(o.request,null);assert.equal(o.nextAfter,2);});
check("valid next page retains prior rows pending",()=>{const c=partial();const o=c.next(scope,id(2),2);assert.equal(o.messages.length,2);assert.equal(o.request.after,2);assert.equal(c.receive(frame(o.request,[row(3)],true),scope).messages.length,3);});
check("cross-page duplicate clears entire snapshot",()=>{const c=partial();const r=c.next(scope,id(2),2).request;empty(c.receive(frame(r,[{...row(3),turn_id:"turn-1"}],true),scope));});
check("gap clears entire snapshot",()=>{const c=partial();const r=c.next(scope,id(2),2).request;empty(c.receive(frame(r,[row(4)],true),scope));});
check("old page cannot settle current request",()=>{const [c,r]=opened();const f=frame(r,[row(1)]);c.receive(f,scope);c.next(scope,id(2),2);empty(c.receive(f,scope));});
check("duplicate request ID refused after reset",()=>{const c=partial();c.close();empty(c.open(scope,id(1),2));});
check("new explicit open replaces prior rows",()=>{const c=partial();const o=c.open(scope,id(2),2);assert.equal(o.state,"PENDING");assert.equal(o.messages.length,0);assert.equal(o.request.after,0);});
check("revision change clears",()=>empty(partial().observe({...scope,revision:11})));
check("Tree change clears",()=>empty(partial().observe({...scope,treeKey:"MAPLE"})));
check("session change clears",()=>empty(partial().observe({...scope,sessionId:"other"})));
check("view generation change clears",()=>empty(partial().observe({...scope,generation:2})));
check("local attachment key change clears",()=>empty(partial().observe({...scope,viewKey:"local-view-b"})));
check("lost current view clears",()=>empty(partial().observe(null)));
check("detach cannot auto restore",()=>{const c=partial();empty(c.close(),"CLOSED");empty(c.observe(scope),"CLOSED");});
check("host refusal clears pending and retained history",()=>{const c=partial();c.next(scope,id(2),2);empty(c.reject());});
check("wrong page received after detach refuses",()=>{const [c,r]=opened();c.close();empty(c.receive(frame(r,[row(1)]),scope));});
check("complete empty session",()=>{const v={...scope,revision:0};const [c,r]=opened(v);const o=c.receive(frame(r,[],true),v);assert.equal(o.state,"COMPLETE");assert.equal(o.messages.length,0);});
check("next after complete refused",()=>{const [c,r]=opened();c.receive(frame(r,[row(1)],true),scope);empty(c.next(scope,id(2),2));});
check("invalid scope or page size",()=>{const c=p.createController();empty(c.open({...scope,viewKey:"bad\n"},id(1),2));empty(c.open(scope,id(2),17));});
check("returned references and messages cannot mutate controller",()=>{const [c,r]=opened();const f=frame(r,[row(1)]);r.after=9;const o=c.receive(f,scope);o.messages[0].body="changed";assert.equal(c.observe(scope).messages[0].body,"Public 1");});
check("bounded retained row count",()=>{
    const v={...scope,revision:300};const c=p.createController();
    let o=c.open(v,id(1),16);
    for(let j=0;j<16;j++){o=c.receive(frame(o.request,Array.from({length:16},(_,i)=>row(j*16+i+1))),v);assert.equal(o.state,"PARTIAL");o=c.next(v,id(j+2),16);}
    const end=c.receive(frame(o.request,[row(257)]),v);empty(end);assert.equal(end.reason,"DISPLAY_LIMIT");
});
check("bounded retained byte count",()=>{
    const v={...scope,revision:100};const c=p.createController();let o=c.open(v,id(1),1);
    for(let i=1;i<=32;i++){o=c.receive(frame(o.request,[row(i,"é".repeat(8000))]),v);assert.equal(o.state,"PARTIAL");o=c.next(v,id(i+1),1);}
    const end=c.receive(frame(o.request,[row(33,"é".repeat(8000))]),v);empty(end);assert.equal(end.reason,"DISPLAY_LIMIT");
});
check("bounded unique request lifetime",()=>{
    const c=p.createController();for(let i=1;i<=1024;i++)assert.equal(c.open(scope,id(i),1).state,"PENDING");
    const o=c.open(scope,id(1025),1);empty(o);assert.equal(o.reason,"INVALID_OR_EXHAUSTED_REQUEST");
});
console.log(count+" checks passed (public history display lifecycle only)");
