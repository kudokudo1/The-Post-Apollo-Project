// Actual DOC 2 consumer + projector, actual DOC 4 owner/runtime/delivery.
// A disposable stdin/stdout fixture is NOT the chosen production transport.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const readline = require("node:readline");
const {spawn} = require("node:child_process");
const {randomUUID} = require("node:crypto");
const [memoryDir, consumerFile, projectorFile] = process.argv.slice(2);
function load(file) {
    const ctx = vm.createContext({});
    vm.runInContext(fs.readFileSync(file,"utf8"),ctx);
    return ctx;
}
const c = load(consumerFile), p = load(projectorFile);
const child = spawn("python3", ["-B",path.join(__dirname,"queue_r2_composed_fixture.py"),memoryDir],
    {stdio:["pipe","pipe","inherit"]});
const lines = readline.createInterface({input:child.stdout})[Symbol.asyncIterator]();
const exited = new Promise((resolve,reject)=>{
    child.on("error",reject);
    child.on("exit",code=>code===0?resolve():reject(new Error("fixture exit "+code)));
});
async function call(kind, args={}, expectError=null) {
    child.stdin.write(JSON.stringify({kind,...args})+"\n");
    const line=await lines.next();
    assert.equal(line.done,false,"fixture reply missing");
    const reply=JSON.parse(line.value);
    if (expectError!==null) {
        assert.equal(reply.ok,false); assert.equal(reply.code,expectError); return;
    }
    assert.equal(reply.ok,true,JSON.stringify(reply));
    return reply.value;
}
let s=c.initial();
async function publish() {
    const packet=await call("publish");
    s=c.acceptStatus(s,packet,p.project);
    assert.ok(s.status,"actual projector/consumer refused publication "+JSON.stringify(packet));
    assert.equal(s.status.canExecute,false);
    assert.equal(s.status.outcome,"UNVERIFIED");
    return packet;
}
async function action(kind,target=null,expiry=null,lose=false) {
    s=c.prepare(s,kind,target,expiry);
    assert.ok(s.prepared,"prepare refused "+kind);
    const sent=c.submit(s,randomUUID()); s=sent.state;
    assert.ok(sent.message);
    assert.equal(s.status,null);
    const reply=await call("action",{message:sent.message});
    assert.equal(await call("passive"),null);
    assert.equal(JSON.stringify(reply).includes("inode"),false);
    assert.equal(JSON.stringify(reply).includes("device"),false);
    if (lose) s=c.timeout(s);
    else s=c.acceptAction(s,reply);
    assert.equal(s.status,null);
    return {message:sent.message,reply};
}
(async()=>{
    try {
        s=c.connect(s,await call("connect"));
        assert.equal(await call("passive"),null);
        const idle=await publish();
        assert.equal(s.status.state,"IDLE REPORTED");
        assert.equal(idle.projection.status.next_check_monotonic_ms,null);
        for(let i=0;i<50;i++) assert.deepEqual(await call("passive"),idle);
        assert.deepEqual(await call("counts"),{captures:0,samples:0,offers:0});
        console.log("PASS idle/passive reads: zero source or observation calls, no new revision");

        const queued=await action("QUEUE",16,200);
        assert.equal(queued.reply.disposition,"REPORTED");
        await call("action",{message:queued.message},"STALE_ACTION_SEQUENCE");
        const original=queued.reply.result.request.id;
        await call("mode",{mode:"OCCUPIED"});
        const waiting=await publish();
        assert.equal(s.status.requestId,original);
        assert.equal(s.status.state,"WAITING REPORTED");
        assert.equal(s.status.code,"EXTENSION_OCCUPIED");
        const event=waiting.projection.notification_candidate.event;
        assert.equal(await call("offer",{event_id:event.event_id}),"HISTORY_OBSERVED");
        assert.equal(await call("offer",{event_id:event.event_id}),"ALREADY_RESERVED");
        for(let i=0;i<50;i++) await call("passive");
        assert.deepEqual(await call("counts"),{captures:1,samples:1,offers:1});
        console.log("PASS actual queue/consumer/deferred delivery and passive reuse");

        await call("mode",{mode:"READY"});
        for(let i=0;i<4;i++) {
            await call("advance",{ms:1000});
            await publish();
        }
        assert.equal(s.status.state,"READY REPORTED // RECHECK REQUIRED");
        const recheck=await action("RECHECK");
        assert.equal(recheck.reply.disposition,"REPORTED");
        await publish();
        assert.equal(s.status.code,"STABILITY_INTERVAL");
        await call("advance",{ms:1000});
        assert.equal(await call("passive"),null);
        s=c.timeout(s);
        assert.equal(s.status,null);
        await call("mode",{mode:"UNAVAILABLE"});
        await publish();
        assert.equal(s.status.state,"UNKNOWN");
        assert.equal(s.status.code,"OBSERVATION_UNAVAILABLE");
        console.log("PASS advisory readiness, recheck stability, deadline and provider loss");

        await call("mode",{mode:"READY"});
        const replaced=await action("REPLACE",16,201,true);
        const replacement=replaced.reply.result.request.id;
        assert.notEqual(replacement,original);
        assert.ok(s.unresolved);
        assert.equal(c.submit(s,randomUUID()).message,null);
        const oldOwner=s.ownerId;
        s=c.disconnect(s);
        s=c.connect(s,await call("restart"));
        assert.notEqual(s.ownerId,oldOwner);
        assert.equal(c.acceptAction(s,replaced.reply),s);
        await publish();
        assert.equal(s.status.requestId,replacement);
        assert.ok(s.unresolved);
        assert.equal(c.prepare(s,"CANCEL",null,null),s);
        const history=await call("history_summary",{request_id:original});
        assert.equal(history.state,"REPLACED");
        assert.equal(history.outcome,"UNVERIFIED");
        assert.ok(history.events>=2);
        s=c.acknowledgeReconciliation(s);
        assert.equal(s.unresolved,null);
        console.log("PASS lost replacement reply, old epoch refusal, durable history, no replay");

        const cancelled=await action("CANCEL");
        assert.equal(cancelled.reply.result.request.state,"CANCELLED");
        await publish();
        assert.equal(s.status.state,"IDLE REPORTED");
        const counts=await call("counts");
        for(let i=0;i<50;i++) await call("passive");
        assert.deepEqual(await call("counts"),counts);
        await call("invalidate");
        assert.equal(await call("passive"),null);
        s=c.timeout(s); assert.equal(s.status,null);
        console.log("PASS cancellation returns to idle and host invalidation");
        console.log("R2 composed fixture PASS (no native observation, no real Hub, no deployment)");
    } finally {
        child.stdin.end();
        await exited;
    }
})().catch(error=>{console.error(error);child.kill();process.exitCode=1;});
