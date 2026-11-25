const assert=require("node:assert/strict");
const fs=require("node:fs"), path=require("node:path"), vm=require("node:vm");
const w=vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname,"r6_parent/ParentWire.js"),"utf8"),w);
const trial="a".repeat(32);
const frame=(data={},action=1,kind="RESULT")=>({v:1,trial,action,kind,data});
const line=(data={},action=1,kind="RESULT")=>w.canonical(frame(data,action,kind),w.RESPONSE);
let n=0; function test(name,fn){fn();n++;console.log("PASS",name);}
function rejected(raw) {
    const p=w.createWire(); let called=0;
    assert.equal(p.receive(raw,()=>{called++;return true}),false);
    assert.equal(called,0);assert.equal(p.snapshot().failed,true);
    assert.equal(p.snapshot().retained,0);
    assert.equal(p.receive(line(),()=>{called++;return true}),false);
    assert.equal(called,0);
}
test("fragmented and coalesced complete frames",()=>{
    const p=w.createWire(), seen=[], a=line({code:"READY",units:[]}), b=line({code:"ACTIVE",units:[]},2);
    const cb=x=>{seen.push(x.action);return true;};
    assert.equal(p.receive(a.slice(0,11),cb),true);
    assert.equal(p.snapshot().retained,11);assert.deepEqual(seen,[]);
    assert.equal(p.receive(a.slice(11)+b,cb),true);assert.deepEqual(seen,[1,2]);
    assert.equal(p.snapshot().bytes,a.length+b.length);assert.equal(p.snapshot().frames,2);
    assert.equal(p.end(),true);
});
test("exact maximum response including LF",()=>{
    const empty=line({sample:""});
    const full=line({sample:"a".repeat(w.RESPONSE-empty.length)});
    assert.equal(full.length,w.RESPONSE);
    const p=w.createWire(); assert.equal(p.receive(full.slice(0,-1),()=>false),true);
    assert.equal(p.snapshot().retained,w.RESPONSE-1);
    assert.equal(p.receive("\n",()=>true),true);assert.equal(p.end(),true);
});
test("unterminated overflow and truncated EOF",()=>{
    rejected("a".repeat(w.RESPONSE));
    const p=w.createWire();assert.equal(p.receive("partial",()=>false),true);
    assert.equal(p.end(),false);assert.equal(p.snapshot().retained,0);
});
test("nonascii/control/BOM/CR and empty line",()=>{
    for(const bad of ["é","\u0000","\ufeff","\r\n","\n"])rejected(bad);
});
test("duplicate, prototype keys, noncanonical order",()=>{
    const a=line({code:"READY"});
    for(const bad of [a.replace('"code":"READY"','"code":"READY","code":"READY"'),
        a.replace('"code":"READY"','"__proto__":{}'),
        a.replace('"code":"READY"','"constructor":0'),
        a.replace('"code":"READY"','"prototype":false'),
        JSON.stringify(frame({code:"READY"}))+"\n",
        a.replace('"action":1','"action":1,"action":1')])rejected(bad);
});
test("alternate numbers/escapes and invalid JSON",()=>{
    const a=line({value:1});
    for(const val of ["1.0","1e0","-0","01","9007199254740992","undefined","NaN",
        '"\\u0041"','"\\n"','"\\/"',"[1,]","{"])rejected(a.replace('"value":1','"value":'+val));
    rejected(a.replace('"value":1','"value": 1'));
});
test("lexical depth and node bounds before parse",()=>{
    const a=line({value:1});
    rejected(a.replace('"value":1','"value":'+"[".repeat(7)+"0"+"]".repeat(7)));
    rejected(a.replace('"value":1','"value":['+Array(256).fill("0").join(",")+"]"));
    rejected(a.replace('"value":1','"value":{"a":'+Array(260).fill("0").join(",")+"}"));
});
test("quote and backslash canonical string",()=>{
    const a=line({sample:'quote" and slash\\'});
    const p=w.createWire();assert.equal(p.receive(a,f=>f.data.sample==='quote" and slash\\'),true);
});
test("exact envelope types and field set",()=>{
    for(const o of [{...frame(),v:true},{...frame(),action:0},{...frame(),action:65},
        {...frame(),trial:trial.toUpperCase()},{...frame(),data:[]},{...frame(),extra:1}])
        rejected(w.canonical(o,w.RESPONSE));
});
test("outbound reserve and attempted bytes",()=>{
    const p=w.createWire();assert.equal(p.reserve(true),true);
    const a=p.prepare(frame({},1,"HELLO"));assert.equal(typeof a,"string");
    assert.equal(p.snapshot().bytes,a.length);assert.equal(p.snapshot().frames,1);
    p.stop();assert.equal(p.prepare(frame()),null);assert.equal(p.snapshot().bytes,a.length);
});
test("control cap exact and one byte overflow",()=>{
    const base=w.canonical(frame({sample:""}),w.CONTROL);
    const p=w.createWire(), q=w.createWire();
    assert.equal(p.prepare(frame({sample:"a".repeat(w.CONTROL-base.length)})).length,w.CONTROL);
    assert.equal(q.prepare(frame({sample:"a".repeat(w.CONTROL-base.length+1)})),null);
});
test("cumulative budget and no reserve beyond worst case",()=>{
    const p=w.createWire();
    const full=line({sample:"a".repeat(w.RESPONSE-line({sample:""}).length)});
    for(let i=0;i<7;i++)assert.equal(p.receive(full,()=>true),true);
    assert.equal(p.reserve(true),false);assert.equal(p.reserve(false),false);
    assert.equal(p.receive(full,()=>true),true);
    assert.equal(p.snapshot().bytes,w.TOTAL);
    assert.equal(p.receive("a",()=>true),false);
});
test("frame cap independent of byte cap",()=>{
    const p=w.createWire();
    for(let i=0;i<w.FRAMES;i++)assert.equal(p.receive(line(),()=>true),true);
    assert.equal(p.receive(line(),()=>true),false);
});
test("callback failure stops coalesced remainder, charges observed chunk",()=>{
    const p=w.createWire(), a=line();let calls=0;
    assert.equal(p.receive(a+a,()=>{calls++;return false;}),false);
    assert.equal(calls,1);assert.equal(p.snapshot().bytes,a.length*2);
});
test("callback may prepare ACK, not recursively receive",()=>{
    const p=w.createWire();
    assert.equal(p.receive(line(),()=>typeof p.prepare(frame({},1,"OPEN_ACK"))==="string"),true);
    const q=w.createWire();
    assert.equal(q.receive(line(),()=>q.receive(line(),()=>true)),false);
});
test("bytes after end refused; callback throw sanitized",()=>{
    const p=w.createWire();assert.equal(p.end(),true);assert.equal(p.receive(line(),()=>true),false);
    const q=w.createWire();assert.equal(q.receive(line(),()=>{throw Error("private");}),false);
    assert.equal(q.snapshot().failed,true);
});
console.log(n+" R6 parent framing checks PASS");
