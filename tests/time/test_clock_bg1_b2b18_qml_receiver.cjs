"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),vm=require("node:vm"),path=require("node:path");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const qml=read("services/time/AlarmManagerService.qml");
const policy={};
vm.runInNewContext(read("services/time/AlarmNativeBridgeInboundPolicy.js")
    .replace(/^\.pragma library\s*$/m,""),policy);
const plain=v=>JSON.parse(JSON.stringify(v));
const nonce="a".repeat(64),digest="b".repeat(64);
function frame(gen=3,extra={}) {
    const p={action:"OBSERVE_FINAL_CANDIDATE",generation:gen,
             nonce,sourceDigest:digest,v:1,...extra};
    return JSON.stringify(Object.fromEntries(
        Object.keys(p).sort().map(k=>[k,p[k]])));
}
const terminal=g=>({phase:"QUIESCING",localQueueDrained:true,
    acceptedGeneration:g,observedSaveGeneration:g});
function deny(r) {
    assert.equal(r.ok,false);
    for(const k of ["nativeSenderAuthenticated","quickshellProcessBound",
      "durableRevisionWitnessed","writerStopped","releaseAcknowledged",
      "oldWriterRestartPrevented","canTransferOwnership","canRing","canNotify"])
        assert.equal(r[k],false,k);
}
function method(name){
    const start=qml.indexOf("function "+name+"(");
    assert(start>=0,"missing actual QML method: "+name);
    const open=qml.indexOf("{",start);
    let depth=0;
    for(let i=open;i<qml.length;i++){
        if(qml[i]==="{")depth++;
        if(qml[i]==="}"&&--depth===0)return qml.slice(open+1,i);
    }
    throw Error("unclosed actual QML function");
}
test("canonical candidate with matching local generation is not an authority",()=>{
    const res=plain(policy.inspectCandidate(frame(),terminal(3)));
    assert.equal(res.reason,"LOCAL_SAVE_GENERATION_CANDIDATE_ONLY");
    assert.equal(res.frameSyntaxObserved,true);
    assert.equal(res.localSaveGenerationMatched,true);
    deny(res);
    assert.equal(JSON.stringify(res).includes(nonce),false);
    assert.equal(JSON.stringify(res).includes(digest),false);
});
test("bad frames, malformed JSON, injections and duplicate fields refuse",()=>{
    const samples=[null,undefined,{},[],"",NaN,"not json","{}",
       frame()+"\n",frame()+"\r",frame()+"\u0000","x".repeat(513),
       frame().repeat(2),frame().replace('"v":1}', '"v":1,"v":1}'),
       '{"__proto__":{"canRing":true}}',
       frame().replace('"action":','"action":"OBSERVE_FINAL_CANDIDATE","action":')];
    for(const x of samples){
        const res=plain(policy.inspectCandidate(x,terminal(3)));
        assert.equal(res.frameSyntaxObserved,false,String(x).slice(0,50));
        deny(res);
    }
});
test("canonical field set rejects forged authority and alternative encodings",()=>{
    const samples=[
      frame(3,{action:"REQUEST_PAUSE"}),frame(3,{v:2}),
      frame(-1),frame(0),frame(1.2),frame("3"),frame(true),
      frame(3,{nonce:"F".repeat(64)}),frame(3,{nonce:"a"}),
      frame(3,{sourceDigest:"B".repeat(64)}),frame(3,{sourceDigest:"b"}),
      frame(3,{canRing:true}),frame(3,{releaseAcknowledged:true}),
      frame(3,{trusted:true}),frame(3,{nativeSenderAuthenticated:true}),
      frame(Number.MAX_SAFE_INTEGER+1),
      frame().replace('"v":1}', '"v":1 }'),
      frame().replace('"generation":3','"generation":3.0')];
    for(const x of samples){
       const res=plain(policy.inspectCandidate(x,terminal(3)));
       assert.equal(res.frameSyntaxObserved,false,x.slice(0,75));
       deny(res);
    }
});
test("terminal phase, accepted and observed generations must match",()=>{
    for(const delta of [{phase:"ACTIVE"},{phase:"DRAINING"},
       {phase:"FAILED"},{localQueueDrained:false},
       {acceptedGeneration:4},{observedSaveGeneration:2},
       {acceptedGeneration:NaN},{observedSaveGeneration:"3"}]){
        const res=plain(policy.inspectCandidate(frame(),{...terminal(3),...delta}));
        assert.equal(res.frameSyntaxObserved,true);
        assert.equal(res.localSaveGenerationMatched,false);
        assert.equal(res.reason,"LOCAL_FINAL_SAVE_NOT_WITNESSED");
        deny(res);
    }
    for(const value of [null,{},false,[],"QUIESCING"]){
        const res=plain(policy.inspectCandidate(frame(),value));
        assert.equal(res.localSaveGenerationMatched,false);
        deny(res);
    }
});
test("mounted QML receiver exists but cannot open a listener",()=>{
    assert.match(qml,/import "AlarmNativeBridgeInboundPolicy.js" as NativeBridge/);
    assert.match(qml,/SocketServer\s*\{\s*id: nativeBridgeReceiver\s*active: false\s*path: ""/);
    assert.match(qml,/handler: Socket\s*\{\s*parser: SplitParser/);
    assert.match(qml,/onRead: message => \{\s*nativeBridgeIngress\.inspectFrame\(message\)/);
    assert.match(qml,/readonly property bool nativeWriterDrainBridgeInstalled: false/);
    assert.match(qml,/readonly property string alarmWriterBarrierPhase: "ACTIVE"/);
    assert.doesNotMatch(qml,/nativeBridgeReceiver\.active\s*=/);
    assert.doesNotMatch(qml,/nativeBridgeReceiver\.path\s*=/);
});
test("actual mounted QML inspection refuses in live hard-off mode",()=>{
    const ctx={NativeBridge:policy,
       manager:{nativeWriterDrainBridgeInstalled:false,
                localWriterDrainStatus:terminal(3)},
       nativeBridgeReceiver:{active:false}};
    const before=JSON.stringify(ctx.manager);
    const inspect=vm.runInNewContext("(function(raw){"+method("inspectFrame")+"})",ctx);
    const res=plain(inspect(frame()));
    assert.equal(res.reason,"NATIVE_QML_BRIDGE_NOT_INSTALLED");
    assert.equal(res.frameSyntaxObserved,false);
    deny(res);
    assert.equal(JSON.stringify(ctx.manager),before);
});
test("future mocked ingress can only observe matching local generation",()=>{
    const ctx={NativeBridge:policy,
       manager:{nativeWriterDrainBridgeInstalled:true,
                localWriterDrainStatus:terminal(3)},
       nativeBridgeReceiver:{active:true}};
    const before=JSON.stringify(ctx.manager);
    const inspect=vm.runInNewContext("(function(raw){"+method("inspectFrame")+"})",ctx);
    const res=plain(inspect(frame()));
    assert.equal(res.localSaveGenerationMatched,true);
    deny(res);
    assert.equal(JSON.stringify(ctx.manager),before);
});
test("writer, alarm, public pause and actual FileView remain protected",()=>{
    assert.match(method("requestAlarmWriterPause"),
       /return WriterBarrier\.requestPause\(writerPauseSnapshot\(\)\)/);
    assert.match(method("requestWriterRelease"),
       /return WriterQuiescence\.requestRelease\(writerQuiescenceSnapshot\(\)\)/);
    assert.match(method("beginInternalSaveDrain"),/!manager\.nativeWriterDrainBridgeInstalled/);
    assert.doesNotMatch(method("inspectFrame"),
       /beginInternalSaveDrain|writerDrain\.|requestAlarmWriterPause|alarmFile|syncSound|takeOwnership/);
    assert.equal(qml.match(/alarmFile\.setText\(/g)?.length,1);
    assert.match(qml,/atomicWrites: true/);
    assert.match(qml,/blockWrites: false/);
    assert.doesNotMatch(qml,/Process\s*\{/);
});
test("inactive status always refuses transfer and ringing",()=>{
    const result=plain(policy.inactiveStatus());
    assert.equal(result.reason,"NATIVE_QML_BRIDGE_NOT_INSTALLED");
    deny(result);
});
