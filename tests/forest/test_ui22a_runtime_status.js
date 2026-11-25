const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const {execFileSync}=require("node:child_process");
const p=vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname,"../../widgets/forest/ui2/PublicRuntimeStatusDisplay.js"),"utf8"),p);
const a={requestId:"a".repeat(32),viewKey:"b".repeat(32),generation:1};
const b={requestId:"c".repeat(32),viewKey:"d".repeat(32),generation:2};
const packet=status=>({schema:"postapollo.forest.public-runtime-status.v1",status,sourceAuthenticated:false,permissionGranted:false,productionAuthority:false,modelExecutionPermitted:false,safeActions:[]});
const unit=(ref,sequence,status)=>({...ref,sequence,kind:"STATUS",statusPacket:packet(status)});
const withdrawal=(ref,sequence)=>({...ref,sequence,kind:"WITHDRAW",statusPacket:null});
function opened(){const c=p.createConsumer();assert.equal(c.open(a,a).state,"ATTACHED");return c;}
function checkFalse(o){for(const k of ["sourceAuthenticated","permissionGranted","productionAuthority","modelExecutionPermitted","sendEnabled","stopEnabled"])assert.equal(o[k],false);assert.equal(o.safeActions.length,0);}
function empty(o,state){assert.equal(o.state,state);assert.equal(o.label,"");assert.equal(o.status,"");checkFalse(o);}
let n=0;function check(name,fn){fn();console.log("PASS",name);n++;}
check("actual merged R4b recorded units",()=>{
    const units=JSON.parse(execFileSync("python3",["-B",path.join(__dirname,"ui2_r4b_public_fixture.py")],{encoding:"utf8"}));
    const {requestId,viewKey,generation}=units[0],ref={requestId,viewKey,generation};
    const c=p.createConsumer();c.open(ref,ref);
    assert.deepEqual(units.map(x=>x.sequence),[1,2,3,4,5]);
    for(let i=0;i<4;i++){const o=c.receive(units[i],ref);assert.equal(o.state,"DISPLAYING");assert.equal(o.status,units[i].statusPacket.status);checkFalse(o);}
    empty(c.receive(units[4],ref),"CLOSED");
});
check("incoming never opens",()=>empty(p.createConsumer().receive(unit(a,1,"REQUEST_PENDING"),a),"CLOSED"));
check("fresh explicit open requires exact current scope",()=>empty(p.createConsumer().open(a,b),"UNAVAILABLE"));
check("wrong token casing, newline, equal token, bool or unsafe generation",()=>{
 for(const bad of [{...a,requestId:"A".repeat(32)},{...a,requestId:a.requestId+"\n"},{...a,viewKey:a.requestId},{...a,generation:true},{...a,generation:2**53}])empty(p.createConsumer().open(bad,bad),"UNAVAILABLE");
});
check("no IDLE publication",()=>empty(opened().receive(unit(a,1,"IDLE"),a),"UNAVAILABLE"));
check("early unknown is terminal",()=>{const c=opened();assert.equal(c.receive(unit(a,1,"UNKNOWN_HOLD"),a).status,"UNKNOWN_HOLD");empty(c.receive(unit(a,2,"REQUEST_PENDING"),a),"UNAVAILABLE");});
check("stop request not cancellation; local commit not delivery",()=>{const c=opened();c.receive(unit(a,1,"REQUEST_PENDING"),a);let o=c.receive(unit(a,2,"STOP_REQUESTED"),a);assert.equal(o.label,"STOP REQUESTED // OUTCOME PENDING");o=c.receive(unit(a,3,"LOCAL_COMMIT_RECORDED"),a);assert.equal(o.label,"LOCAL COMMIT RECORDED // DELIVERY UNCONFIRMED");checkFalse(o);});
check("terminal cannot be promoted",()=>{const c=opened();for(const [i,s] of ["REQUEST_PENDING","PREPARING","GENERATING","LOCAL_COMMIT_RECORDED"].entries())c.receive(unit(a,i+1,s),a);empty(c.receive(unit(a,5,"UNKNOWN_HOLD"),a),"UNAVAILABLE");});
check("withdraw before first status closes",()=>empty(opened().receive(withdrawal(a,1),a),"CLOSED"));
check("withdrawal irreversible",()=>{const c=opened();c.receive(withdrawal(a,1),a);empty(c.receive(unit(a,2,"REQUEST_PENDING"),a),"CLOSED");empty(c.open(a,a),"UNAVAILABLE");});
check("stale status and withdrawal cannot clear new view",()=>{const c=opened();c.open(b,b);c.receive(unit(b,1,"REQUEST_PENDING"),b);assert.equal(c.receive(unit(a,2,"GENERATING"),b).status,"REQUEST_PENDING");assert.equal(c.receive(withdrawal(a,2),b).status,"REQUEST_PENDING");assert.equal(c.invalidate(a).status,"REQUEST_PENDING");});
check("uncorrelatable inputs ignored",()=>{const c=opened();c.receive(unit(a,1,"REQUEST_PENDING"),a);for(const x of [null,{},[],{requestId:a.requestId,viewKey:a.viewKey,generation:false}])assert.equal(c.receive(x,a).status,"REQUEST_PENDING");});
check("current extra fields and private fields refuse",()=>empty(opened().receive({...unit(a,1,"REQUEST_PENDING"),operationId:"internal"},a),"UNAVAILABLE"));
check("current malformed packet authority refuses",()=>{const u=unit(a,1,"REQUEST_PENDING");u.statusPacket.permissionGranted=true;empty(opened().receive(u,a),"UNAVAILABLE");});
check("all nonfalse flags refuse",()=>{for(const k of ["sourceAuthenticated","permissionGranted","productionAuthority","modelExecutionPermitted"]){const u=unit(a,1,"REQUEST_PENDING");u.statusPacket[k]=0;empty(opened().receive(u,a),"UNAVAILABLE");}});
check("safeActions and extra text refuse",()=>{for(const bad of [{safeActions:["SEND"]},{text:"private"},{status:"<b>raw</b>"}]){const u=unit(a,1,"REQUEST_PENDING");Object.assign(u.statusPacket,bad);empty(opened().receive(u,a),"UNAVAILABLE");}});
check("gap duplicate out-of-order and unsafe sequence close",()=>{for(const seq of [1,0,3,true,2**53]){const c=opened();c.receive(unit(a,1,"REQUEST_PENDING"),a);empty(c.receive(unit(a,seq,"PREPARING"),a),"UNAVAILABLE");}});
check("duplicate generating transition closes",()=>{const c=opened();c.receive(unit(a,1,"REQUEST_PENDING"),a);c.receive(unit(a,2,"PREPARING"),a);c.receive(unit(a,3,"GENERATING"),a);empty(c.receive(unit(a,4,"GENERATING"),a),"UNAVAILABLE");});
check("detach observed without callback",()=>{const c=opened();c.receive(unit(a,1,"REQUEST_PENDING"),a);empty(c.observe(null),"CLOSED");empty(c.receive(unit(a,2,"PREPARING"),a),"CLOSED");});
check("owner invalidation after callback clears matching only",()=>{const c=opened();c.receive(unit(a,1,"REQUEST_PENDING"),a);empty(c.invalidate(a),"UNAVAILABLE");empty(c.receive(unit(a,2,"PREPARING"),a),"UNAVAILABLE");});
check("copies and local token reuse fence",()=>{const c=opened(),u=unit(a,1,"REQUEST_PENDING");const o=c.receive(u,a);u.statusPacket.status="GENERATING";o.status="GENERATING";assert.equal(c.observe(a).status,"REQUEST_PENDING");c.close();empty(c.open({...b,viewKey:a.viewKey},{...b,viewKey:a.viewKey}),"UNAVAILABLE");});
console.log(n+" checks passed (recorded public status presentation only)");
