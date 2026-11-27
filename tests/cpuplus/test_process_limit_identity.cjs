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
function makeApi() {
    return new Function("let softLimitPids={},limitOwnership={},applyError='';\n"+["identityKey","limitStateFor","limitBytesFor","hasSoftLimit","validLimitToken","validatedReply","consumeApply","applyCommand"].map(fn).join("\n")+"\nreturn {identityKey,limitStateFor,limitBytesFor,hasSoftLimit,validatedReply,consumeApply,applyCommand,state:()=>({softLimitPids,limitOwnership,applyError})};")();
}
test("exact identity, original baseline and correlated release",()=>{
    const api=makeApi(),key=api.identityKey(row);
    assert.notEqual(key,api.identityKey({...row,startTicks:457}));
    assert.notEqual(key,api.identityKey({...row,comm:"other"}));
    assert.equal(api.identityKey({...row,startTicks:0}),"");
    assert.equal(api.identityKey({...row,pid:1}),"");
    const request={serial:1,pid:123,startTicks:456,name:"test",key,capBytes:1024,ownership:null};
    const reply={serial:1,pid:123,startTicks:456,name:"test",requested:1024,ok:true,mode:"managed",observedSoft:"1024",originalSoft:"2048",hard:"4096"};
    const validate=(req,data,code=0,timeout=false)=>api.validatedReply(req,JSON.stringify(data),"",code,0,timeout);
    assert.equal(validate(request,{...reply,startTicks:457}),null);
    assert.equal(validate(request,{...reply,serial:2}),null);
    assert.equal(validate(request,reply,1),null);
    assert.equal(validate(request,reply,0,true),null);
    api.consumeApply(request,validate(request,reply));
    assert.equal(api.limitBytesFor(row),1024);
    assert.equal(api.limitStateFor(row),"managed");
    assert.equal(api.hasSoftLimit({...row,startTicks:457}),false);
    assert.equal(api.limitBytesFor({...row,startTicks:457}),0);
    const owned=api.state().limitOwnership[key];
    const second={...request,serial:2,capBytes:1536,ownership:owned};
    const changed={...reply,serial:2,requested:1536,observedSoft:"1536"};
    assert.equal(validate(second,{...changed,originalSoft:"1024"}),null);
    api.consumeApply(second,validate(second,changed));
    assert.equal(api.state().limitOwnership[key].originalSoft,"2048");
    api.consumeApply(second,{ok:false,attempted:false,conflict:false,error:"permission"});
    assert.equal(api.limitBytesFor(row),1536);
    const release={...second,serial:3,capBytes:0,ownership:api.state().limitOwnership[key]};
    const restored={...reply,serial:3,requested:0,mode:"released",observedSoft:"2048"};
    assert.equal(validate(release,{...restored,observedSoft:"4096"}),null);
    api.consumeApply(release,validate(release,restored));
    assert.equal(api.limitStateFor(row),"unmanaged");
    assert.equal(api.hasSoftLimit(row),false);
    api.consumeApply(request,null);
    assert.equal(api.limitStateFor(row),"unknown");
    assert.match(api.state().applyError,/OUTCOME UNKNOWN/);
});
test("external change quarantines ownership and bounded queue preserves capture",()=>{
    const api=makeApi(),key=api.identityKey(row);
    const owned={originalSoft:"2048",hard:"4096",appliedSoft:"1024",uncertain:false};
    const request={serial:2,pid:123,startTicks:456,name:"test",key,capBytes:0,ownership:owned};
    api.consumeApply(request,{ok:false,attempted:false,conflict:true,error:"external"});
    assert.equal(api.limitStateFor(row),"unknown");
    assert.equal(api.state().limitOwnership[key].originalSoft,"2048");
    const q=new Function("let queuedRequest=null,requestSerial=0,applyError='',limitOwnership={};let calls=0;\n"+["identityKey","limitStateFor","setLimitMiB"].map(fn).join("\n")+"\nfunction minimumMiB(){return 128} function maximumMiB(){return 8192} function startQueuedApply(){calls++} return {setLimitMiB,state:()=>({queuedRequest,calls,applyError,limitOwnership})};")();
    assert.equal(q.setLimitMiB({...row,startTicks:0},256),false);
    assert.equal(q.setLimitMiB(row,256),true);
    assert.equal(q.setLimitMiB({...row,startTicks:457},512),false);
    assert.equal(q.state().queuedRequest.startTicks,456);
    assert.equal(q.state().queuedRequest.capBytes,256*1024*1024);
    assert.equal(q.state().calls,1);
    q.state().limitOwnership[key]={uncertain:true};
    assert.equal(q.setLimitMiB(row,256),false);
    assert.match(q.state().applyError,/OWNERSHIP UNKNOWN/);
    assert.match(source,/!helperExited \|\| !stdoutDone \|\| !stderrDone/);
    assert.match(source,/validatedReply\(request, helperOutput, helperErrors/);
});
test("actual helper restores original soft limit and refuses external drift",()=>{
    const script=makeApi().applyCommand({})[2];
    const harness=[
        "import json,pathlib,resource,subprocess,sys",
        "script=sys.argv[1]",
        "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'])",
        "try:",
        "    raw=pathlib.Path(f'/proc/{p.pid}/stat').read_text(); end=raw.rfind(')')",
        "    name=raw[raw.index('(')+1:end]; born=int(raw[end+2:].split()[19])",
        "    MiB=1024*1024; hard=resource.prlimit(p.pid,resource.RLIMIT_AS)[1]",
        "    assert hard==resource.RLIM_INFINITY or hard>=768*MiB",
        "    resource.prlimit(p.pid,resource.RLIMIT_AS,(768*MiB,hard))",
        "    req=dict(serial=1,pid=p.pid,startTicks=born,name=name,capBytes=512*MiB,ownership=None)",
        "    def apply(**changes):",
        "        return json.loads(subprocess.check_output([sys.executable,'-c',script,json.dumps(dict(req,**changes))],timeout=5))",
        "    def record(reply): return dict(originalSoft=reply['originalSoft'],hard=reply['hard'],appliedSoft=reply['observedSoft'],uncertain=False)",
        "    bad=apply(startTicks=born+1); assert not bad['ok'] and not bad['attempted']",
        "    bad=apply(name=name+'-wrong'); assert not bad['ok'] and not bad['attempted']",
        "    noop=apply(capBytes=0); assert noop['ok'] and noop['mode']=='noop'",
        "    assert resource.prlimit(p.pid,resource.RLIMIT_AS)==(768*MiB,hard)",
        "    first=apply(); assert first['ok'] and first['originalSoft']==str(768*MiB)",
        "    second=apply(serial=2,capBytes=640*MiB,ownership=record(first)); assert second['ok'] and second['originalSoft']==str(768*MiB)",
        "    restored=apply(serial=3,capBytes=0,ownership=record(second)); assert restored['ok'] and restored['mode']=='released'",
        "    assert resource.prlimit(p.pid,resource.RLIMIT_AS)==(768*MiB,hard)",
        "    first=apply(); assert first['ok']",
        "    resource.prlimit(p.pid,resource.RLIMIT_AS,(600*MiB,hard))",
        "    conflict=apply(capBytes=0,ownership=record(first)); assert not conflict['ok'] and conflict['conflict'] and not conflict['attempted']",
        "    assert resource.prlimit(p.pid,resource.RLIMIT_AS)==(600*MiB,hard)",
        "    if hard==resource.RLIM_INFINITY:",
        "        resource.prlimit(p.pid,resource.RLIMIT_AS,(hard,hard))",
        "        first=apply(); assert first['ok'] and first['originalSoft']=='-1'",
        "        restored=apply(capBytes=0,ownership=record(first)); assert restored['ok'] and restored['observedSoft']=='-1'",
        "        assert resource.prlimit(p.pid,resource.RLIMIT_AS)==(hard,hard)",
        "finally:",
        "    p.terminate(); p.wait(timeout=5)"
    ].join("\n");
    const r=spawnSync("/usr/bin/python3",["-c",harness,script],{encoding:"utf8",timeout:20000});
    assert.equal(r.status,0,r.stderr||String(r.error||""));
});

test("K8b6: correlated completion retains gateway custody and reports actual outcome",()=>{
    const classify=new Function(fn("limitResult")+"\nreturn limitResult;")();
    const req={serial:7,pid:123,startTicks:456,name:"test",key:"target"};
    assert.equal(classify(req,{ok:true,mode:"managed",observedSoft:"1024"}).state,"applied");
    assert.equal(classify(req,{ok:true,mode:"released",observedSoft:"2048"}).state,"restored");
    assert.equal(classify(req,{ok:true,mode:"noop",observedSoft:"-1"}).state,"unchanged");
    assert.equal(classify(req,{ok:false,attempted:false,conflict:false}).state,"refused");
    assert.equal(classify(req,{ok:false,attempted:false,conflict:true}).state,"unknown");
    assert.equal(classify(req,null).state,"unknown");
    const gate=fs.readFileSync(path.resolve(__dirname,"../../services/kill/AppControlHubActionGate.qml"),"utf8");
    const a=gate.indexOf("    function finishLimit("),b=gate.indexOf("\n    }",a);
    assert.ok(a>=0&&b>a);
    const run=new Function("let busy=true,limitDispatchSerial=7,pending={pid:123,startTicks:456,name:'test',action:'limit'},message='',refreshes=0;\n"+gate.slice(a,b+6)+"\nfunction finishRequest(s){message=s;busy=false;pending=null} const refreshOwner={restart:()=>refreshes++}; return {finishLimit,state:()=>({busy,limitDispatchSerial,pending,message,refreshes})};")();
    assert.equal(run.finishLimit({...req,serial:8,message:"wrong"}),false);
    assert.equal(run.finishLimit({...req,startTicks:457,message:"wrong"}),false);
    assert.equal(run.finishLimit({...req,name:"other",message:"wrong"}),false);
    assert.equal(run.state().busy,true);
    assert.equal(run.finishLimit(classify(req,{ok:true,mode:"managed",observedSoft:"1024"})),true);
    assert.equal(run.state().busy,false);
    assert.equal(run.state().limitDispatchSerial,0);
    assert.equal(run.state().refreshes,1);
    assert.equal(run.finishLimit({...req,message:"late"}),false);
    assert.ok(gate.includes("limitDispatchSerial = limitsOwner.requestSerial + 1"));
    assert.ok(gate.includes("function onLimitCompleted(result) { gate.finishLimit(result); }"));
    assert.match(source,/activeRequest = null;\s*applyLoading = false;\s*publishCompletion\(request,result\)/);
    const presentation=fs.readFileSync(path.resolve(__dirname,"../../services/system/ProcessPresentationController.qml"),"utf8");
    assert.match(presentation,/owner\.prepareLimitMiB/);
    assert.match(presentation,/gateway === owner && owner.busy/);
});
