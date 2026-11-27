"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const {spawnSync}=require("node:child_process");
const source=fs.readFileSync(path.resolve(__dirname,"../../services/system/ProcessLimits.qml"),"utf8");
function fn(name) {
    const a=source.indexOf("    function "+name+"("), b=source.indexOf("\n    }",a);
    assert.ok(a>=0&&b>a,name);
    return source.slice(a,b+6);
}
const row={pid:123,startTicks:456,comm:"test",vsz:1000};
const api=new Function("let softLimitPids={},applyError='';\n"+["identityKey","limitBytesFor","hasSoftLimit","validatedReply","consumeApply","applyCommand"].map(fn).join("\n")+"\nreturn {identityKey,limitBytesFor,hasSoftLimit,validatedReply,consumeApply,applyCommand,state:()=>({softLimitPids,applyError})};")();
test("exact identity and correlated readback",()=>{
    const key=api.identityKey(row);
    assert.notEqual(key,api.identityKey({...row,startTicks:457}));
    assert.notEqual(key,api.identityKey({...row,comm:"other"}));
    assert.equal(api.identityKey({...row,startTicks:0}),"");
    assert.equal(api.identityKey({...row,pid:1}),"");
    const request={serial:1,pid:123,startTicks:456,name:"test",key,capBytes:1024};
    const reply={serial:1,pid:123,startTicks:456,name:"test",requested:1024,ok:true,soft:1024};
    assert.equal(api.validatedReply(request,JSON.stringify({...reply,startTicks:457}),"",0,0,false),null);
    assert.equal(api.validatedReply(request,JSON.stringify({...reply,serial:2}),"",0,0,false),null);
    assert.equal(api.validatedReply(request,JSON.stringify(reply),"",1,0,false),null);
    assert.equal(api.validatedReply(request,JSON.stringify(reply),"",0,0,true),null);
    api.consumeApply(request,api.validatedReply(request,JSON.stringify(reply),"",0,0,false));
    assert.equal(api.limitBytesFor(row),1024);
    assert.equal(api.hasSoftLimit({...row,startTicks:457}),false);
    assert.equal(api.limitBytesFor({...row,startTicks:457}),0);
    api.consumeApply(request,{ok:false,attempted:false,error:"permission"});
    assert.equal(api.limitBytesFor(row),1024);
    api.consumeApply(request,null);
    assert.equal(api.hasSoftLimit(row),false);
    assert.match(api.state().applyError,/OUTCOME UNKNOWN/);
    api.consumeApply(request,{ok:true,soft:0});
    assert.equal(api.hasSoftLimit(row),true);
    api.consumeApply(request,{ok:true,soft:-1});
    assert.equal(api.hasSoftLimit(row),false);
});
test("bounded queue preserves accepted capture",()=>{
    const q=new Function("let queuedRequest=null,requestSerial=0,applyError='';let calls=0;\n"+["identityKey","setLimitMiB"].map(fn).join("\n")+"\nfunction minimumMiB(){return 128} function maximumMiB(){return 8192} function startQueuedApply(){calls++} return {setLimitMiB,state:()=>({queuedRequest,calls,applyError})};")();
    assert.equal(q.setLimitMiB({...row,startTicks:0},256),false);
    assert.equal(q.setLimitMiB(row,256),true);
    assert.equal(q.setLimitMiB({...row,startTicks:457},512),false);
    assert.equal(q.state().queuedRequest.startTicks,456);
    assert.equal(q.state().queuedRequest.capBytes,256*1024*1024);
    assert.equal(q.state().calls,1);
    assert.match(source,/!helperExited \|\| !stdoutDone \|\| !stderrDone/);
    assert.match(source,/validatedReply\(request, helperOutput, helperErrors/);
});
test("actual helper refuses stale identity and verifies RLIMIT_AS on disposable child",()=>{
    const script=api.applyCommand({})[2];
    const harness=[
        "import json,os,pathlib,resource,subprocess,sys",
        "script=sys.argv[1]",
        "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'])",
        "try:",
        "    raw=pathlib.Path(f'/proc/{p.pid}/stat').read_text(); end=raw.rfind(')')",
        "    name=raw[raw.index('(')+1:end]; born=int(raw[end+2:].split()[19])",
        "    original=resource.prlimit(p.pid,resource.RLIMIT_AS)",
        "    req=dict(serial=1,pid=p.pid,startTicks=born,name=name,capBytes=512*1024*1024)",
        "    def apply(**changes):",
        "        return json.loads(subprocess.check_output([sys.executable,'-c',script,json.dumps(dict(req,**changes))],timeout=5))",
        "    bad=apply(startTicks=born+1); assert not bad['ok'] and not bad['attempted']",
        "    bad=apply(name=name+'-wrong'); assert not bad['ok'] and not bad['attempted']",
        "    assert resource.prlimit(p.pid,resource.RLIMIT_AS)==original",
        "    good=apply(); assert good['ok'] and good['serial']==1 and good['startTicks']==born",
        "    assert resource.prlimit(p.pid,resource.RLIMIT_AS)[0]==good['soft']",
        "    assert resource.prlimit(p.pid,resource.RLIMIT_AS)[1]==original[1]",
        "finally:",
        "    p.terminate(); p.wait(timeout=5)"
    ].join("\n");
    const r=spawnSync("/usr/bin/python3",["-c",harness,script],{encoding:"utf8",timeout:20000});
    assert.equal(r.status,0,r.stderr||String(r.error||""));
});
