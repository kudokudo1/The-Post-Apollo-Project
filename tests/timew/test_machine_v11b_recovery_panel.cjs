// Exercise the actual QML handler bodies in a JS VM. Not native Qt rendering.
const fs = require("fs"), path = require("path"), vm = require("vm"), assert = require("assert");
const root = path.resolve(__dirname, "../..");
const panel = fs.readFileSync(path.join(root,"widgets/MachineSaveRecoveryPanel.qml"),"utf8");
const widget = fs.readFileSync(path.join(root,"widgets/TimeW.qml"),"utf8");
const policy = fs.readFileSync(path.join(root,"services/time/MachineV3LocalSaveRecoveryPolicy.js"),"utf8");
const pctx = vm.createContext({});
vm.runInContext(policy.replace(/^\.pragma library\s*/, ""), pctx);
let checks=0;
function check(ok, msg) { assert(ok, msg); checks++; }
function body(anchor) {
    const start = panel.indexOf(anchor);
    check(start>=0,"source handler "+anchor);
    const open=panel.indexOf("{", start+anchor.length);
    let depth=1, i=open+1, quote="", line=false, block=false;
    for (;i<panel.length && depth;i++) {
        const c=panel[i], n=panel[i+1];
        if(line){if(c==="\n")line=false;continue;}
        if(block){if(c==="*"&&n==="/"){block=false;i++;}continue;}
        if(quote){if(c==="\\")i++;else if(c===quote)quote="";continue;}
        if(c==="/"&&n==="/"){line=true;i++;continue;}
        if(c==="/"&&n==="*"){block=true;i++;continue;}
        if(c==="\""||c==="'"){quote=c;continue;}
        if(c==="{")depth++;
        if(c==="}")depth--;
    }
    check(depth===0,"balanced source handler");
    return panel.slice(open,i);
}
const ids=["11111111-1111-4111-8111-111111111111","22222222-2222-4222-8222-222222222222"];
const aid="33333333-3333-4333-8333-333333333333";
let launched=[], restarts=0, stops=0;
const ctx=vm.createContext({
    contextActive:true,blocked:false,expanded:false,busy:false,
    requestSequence:0,requestToken:"",requestMode:"",requestIdentity:"",
    intentIds:[],selectedIndex:0,displayResult:null,statusText:"NOT INSPECTED // READ ONLY",
    streamDone:false,exitDone:false,exitOk:false,timedOut:false,responseText:"",
    RecoveryPolicy:pctx,Quickshell:{shellPath:p=>p},
    activeRead:null,activeWatchdog:null,
    Qt:{callLater:fn=>fn()},
    recoveryProcessFactory:{createObject:(_parent, props)=>({
        ...props, running:false, processId:null, kills:0,
        exec(args){this.running=true;this.processId=123;launched.push(Array.from(args));},
        signal(n){assert(n===9);this.kills++;},
        destroy(){this.destroyed=true;}
    })},
    recoveryWatchdogFactory:{createObject:(_parent,props)=>({
        ...props,start(){restarts++;},stop(){stops++;},destroy(){this.destroyed=true;}
    })},
    panel:{}
});
Object.defineProperty(ctx,"selectedIdentity",{get(){return ctx.intentIds[ctx.selectedIndex]||"";}});
for(const [name,args] of [
    ["invalidate","clearList"],["toggle",""],["step","delta"],["nextToken",""],
    ["begin","mode"],["isCurrent","process, generation"],
    ["deadlineReached","process, generation"],["streamFinished","process, generation, text"],
    ["processExited","process, generation, exitCode, exitStatus"],
    ["processStateChanged","process, generation"],["finishIfReady","process, generation"]
]) vm.runInContext("function "+name+"("+args+")"+body("function "+name+"(" + args + ")"),ctx);
function handler(name){vm.runInContext(body(name+":"),ctx);}
function packet(mode, token=ctx.requestToken, identity=ctx.selectedIdentity) {
    const list=mode==="list";
    const data={kind:pctx.KIND,request_id:token,mode,
        checkpoint_id:list?null:identity,
        status:list?"LOCAL_INTENTS_OBSERVED":"ORDINARY_OBSERVED_FRACTIONAL_UNLINKED_HOLD",
        ordinary_status:list?null:pctx.MATCH,fractional_status:null,fractional_attempt_id:null,
        count:list?2:0,intent_ids:list?ids:[],read_only:true,local_data_only:true,
        manual_review_required:true,safe_actions:[]};
    for(const k of pctx.DENIALS)data[k]=false;
    return JSON.stringify(data);
}
function complete(raw, reverse=false, code=0, status=0){
    const p=ctx.activeRead,g=p.generation; p.running=false;p.processId=null;
    if(reverse){
        ctx.processExited(p,g,code,status);
        check(ctx.busy,"exit alone cannot release");
        ctx.streamFinished(p,g,raw);
    }else{
        ctx.streamFinished(p,g,raw);
        check(ctx.busy,"stream alone cannot release");
        ctx.processExited(p,g,code,status);
    }
    check(!ctx.busy,"both signals release");
}
ctx.begin("list");
check(launched.length===0,"closed refuses");
ctx.toggle();
check(ctx.expanded && launched.length===0,"opening does not read");
ctx.begin("inspect");
check(launched.length===0,"no selection");
ctx.begin("list");
const first=ctx.requestToken;
check(ctx.busy && launched.length===1 && restarts===1,"explicit list");
check(launched[0].slice(0,5).join("|")==="python3|-B|-I|services/time/MachineV3LocalSaveRecoveryUiRead.py|list","fixed read bridge");
ctx.begin("list");
check(launched.length===1,"no concurrent launch");
complete(packet("list"));
check(ctx.intentIds.join()===ids.join() && ctx.displayResult.valid,"list observed");
ctx.begin("inspect");
check(ctx.requestToken!==first && ctx.requestIdentity===ids[0],"fresh token and original id");
check(launched[1][6]===ids[0],"explicit inspect only");
complete(packet("inspect"),true);
check(ctx.statusText==="PARTIAL // HOLD" && ctx.displayResult.fractional==="UNLINKED","partial honest");
ctx.step(1);handler("onSelectedIdentityChanged");
check(ctx.selectedIdentity===ids[1]&&ctx.displayResult===null&&launched.length===2,"step clears, no read");
ctx.begin("inspect");
complete(packet("inspect",first));
check(ctx.displayResult.valid===false,"old token refused");
ctx.begin("inspect");
complete(packet("inspect",ctx.requestToken,ids[0]));
check(ctx.displayResult.valid===false,"wrong identity refused");
ctx.begin("inspect");
complete(packet("inspect"),false,1,0);
check(ctx.displayResult.valid===false,"nonzero process refused");
ctx.begin("inspect");
complete(packet("inspect"),true,0,1);
check(ctx.displayResult.valid===false,"abnormal exit refused");
ctx.begin("inspect");complete("x".repeat(8194));
check(ctx.displayResult.valid===false,"oversized response refused");
ctx.begin("inspect");complete("{");
check(ctx.displayResult.valid===false,"malformed response refused");
ctx.begin("inspect");
let old=packet("inspect");
ctx.expanded=false;handler("onExpandedChanged");
ctx.expanded=true;
check(ctx.busy&&ctx.requestToken===""&&ctx.intentIds.length===0,"close invalidates without releasing");
const n=launched.length;
ctx.begin("list");check(launched.length===n,"reopen cannot overlap old request");
complete(old,true);
check(ctx.displayResult===null,"late closed response ignored");
ctx.begin("list");complete(packet("list"),true);
ctx.begin("inspect");old=packet("inspect");
ctx.contextActive=false;handler("onContextActiveChanged");
ctx.contextActive=true;ctx.toggle();
complete(old);
check(ctx.displayResult===null&&ctx.intentIds.length===0,"mode/Stored/menu departure clears");
ctx.begin("list");complete(packet("list"));
ctx.begin("inspect");old=packet("inspect");
ctx.blocked=true;handler("onBlockedChanged");
ctx.blocked=false;complete(old);
check(ctx.displayResult===null&&ctx.intentIds.length===0,"other operation invalidates");
ctx.begin("list");old=packet("list");
const retired=ctx.activeRead, retiredGeneration=retired.generation;
ctx.deadlineReached(retired,retiredGeneration);
check(ctx.timedOut&&ctx.busy&&ctx.requestToken===""&&ctx.statusText.includes("TIMED OUT"),"deadline fail closed");
check(retired.kills===1,"only owned child cancelled");
ctx.begin("list");check(ctx.busy,"no unsafe Process reuse");
ctx.streamFinished(retired,retiredGeneration,old);
check(ctx.busy,"stdout closure is not termination");
retired.running=false;retired.processId=null;
ctx.processStateChanged(retired,retiredGeneration);
check(!ctx.busy&&retired.destroyed,"stopped child retired without exit signal");
check(ctx.displayResult===null&&ctx.intentIds.length===0,"late timeout data ignored");
ctx.begin("list");
const fresh=ctx.activeRead;
ctx.streamFinished(retired,retiredGeneration,old);
ctx.processExited(retired,retiredGeneration,0,0);
ctx.deadlineReached(retired,retiredGeneration);
check(ctx.activeRead===fresh&&ctx.busy&&!ctx.streamDone&&!ctx.exitDone&&fresh.kills===0,"old callbacks cannot mutate or kill current child");
complete(packet("list"));
ctx.begin("list");
const failed=ctx.activeRead;
failed.running=false;failed.processId=null;
ctx.deadlineReached(failed,failed.generation);
check(!ctx.busy&&failed.kills===0&&failed.destroyed&&ctx.displayResult===null,"missing launch / no signals releases only when no child");
ctx.begin("list");complete(packet("list"));
ctx.begin("inspect");old=packet("inspect");
ctx.selectedIndex=1;handler("onSelectedIdentityChanged");
complete(old);
check(ctx.displayResult===null,"selection change invalidates in-flight");
check(restarts===stops,"one deadline per completed request");
for(const marker of ['MachineSaveRecoveryPanel {','contextActive: timew.menuOpen && timew.selectedMode === "machine"',
    '&& !timew.machineStoredViewOpen','blocked: timew.machineSaveBridgeBusy || timew.machineStoreBusy'])
    check(widget.includes(marker),"real widget mount "+marker);
check((panel.match(/process\.exec\(/g)||[]).length===1,"only one launch site");
check(!/save_once|dispatch_once|admit_checkpoint|MachineSaveBridgeV2|MachineRestoreCheckpoint|startDetached|Component\.onCompleted/.test(panel),"no write/auto start/restore");
for(const marker of ['onLeftClicked: panel.begin("list")','onLeftClicked: panel.begin("inspect")',
    'onStreamFinished: panel.streamFinished(reader, reader.generation, this.text)','panel.processExited(reader, reader.generation, exitCode, exitStatus)',
    'repeat: false','running: false','panel.deadlineReached(ownerProcess, generation)'])
    check(panel.includes(marker),"explicit actual source "+marker);
console.log("TIMEW M11B RECOVERY PANEL // "+checks+" lifecycle and source checks PASS");
