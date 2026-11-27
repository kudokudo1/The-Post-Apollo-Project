// Disposable local interaction acceptance, not a room/authority producer.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const source = path.resolve(__dirname,"../../widgets/forest/ui2/InteractionTargetLatch.js");
const ctx = vm.createContext({});
vm.runInContext(fs.readFileSync(source,"utf8"),ctx);
const make = () => ctx.createTargetLatch();
const treeA = "local-tree-a:r1", treeB = "local-tree-b:r1";
const recipient = "local-room-a:recipient-a:r1";
let count=0;
function check(label, fn) { fn(); count++; console.log("PASS",label); }

check("no observed target cannot begin",()=>{
    const c=make();
    assert.equal(c.begin(treeA),null);
    assert.equal(c.finish(null,treeA),false);
});
check("unchanged target completes once",()=>{
    const c=make(); c.observe(treeA);
    const t=c.begin(treeA); assert.ok(t);
    c.observe(treeA);
    assert.equal(c.finish(t,treeA),true);
    assert.equal(c.finish(t,treeA),false);
});
check("browsing another Tree invalidates equipment gesture",()=>{
    const c=make(); c.observe(treeA);
    const t=c.begin(treeA); c.observe(treeB);
    assert.equal(c.finish(t,treeB),false);
    assert.equal(c.finish(t,treeA),false);
});
check("A-B-A cannot revive a prior gesture",()=>{
    const c=make(); c.observe(treeA);
    const t=c.begin(treeA); c.observe(treeB); c.observe(treeA);
    assert.equal(c.finish(t,treeA),false);
});
check("revision change invalidates same labeled target",()=>{
    const c=make(); c.observe(treeA);
    const t=c.begin(treeA); c.observe("local-tree-a:r2");
    assert.equal(c.finish(t,"local-tree-a:r2"),false);
});
check("independent composer latch survives Tree browsing",()=>{
    const equipment=make(), composer=make();
    equipment.observe(treeA); composer.observe(recipient);
    const e=equipment.begin(treeA), d=composer.begin(recipient);
    equipment.observe(treeB);
    assert.equal(equipment.finish(e,treeB),false);
    assert.equal(composer.finish(d,recipient),true);
});
check("recipient replacement does not retarget equipment",()=>{
    const equipment=make(), composer=make();
    equipment.observe(treeA); composer.observe(recipient);
    const e=equipment.begin(treeA), d=composer.begin(recipient);
    composer.observe("local-room-a:recipient-b:r1");
    assert.equal(composer.finish(d,recipient),false);
    assert.equal(equipment.finish(e,treeA),true);
});
check("hidden or withdrawn target cannot complete or restore",()=>{
    const c=make(); c.observe(recipient);
    const t=c.begin(recipient); c.observe(null);
    assert.equal(c.finish(t,recipient),false);
    assert.equal(c.begin(recipient),null);
    c.observe(recipient);
    assert.equal(c.finish(t,recipient),false);
});
check("current mismatch consumes original gesture without retarget",()=>{
    const c=make(); c.observe(treeA);
    const t=c.begin(treeA);
    assert.equal(c.finish(t,treeB),false);
    assert.equal(c.finish(t,treeA),false);
});
check("stale release and cancel cannot clear replacement gesture",()=>{
    const c=make(); c.observe(treeA);
    const old=c.begin(treeA), fresh=c.begin(treeA);
    assert.equal(c.finish(old,treeA),false);
    assert.equal(c.cancel(old),false);
    assert.equal(c.finish(fresh,treeA),true);
});
check("foreign controller and reconstructed handles rejected",()=>{
    const a=make(), b=make(); a.observe(treeA); b.observe(treeA);
    const x=a.begin(treeA), y=b.begin(treeA);
    assert.equal(a.finish(y,treeA),false);
    assert.equal(a.finish({},treeA),false);
    assert.equal(a.finish(x,treeA),true);
    assert.equal(b.finish(y,treeA),true);
});
check("invalid correlation withdraws and blocks",()=>{
    const c=make();
    for(const invalid of ["", "x\n", "with space", "a".repeat(129), {}, 1, null]) {
        c.observe(treeA); const t=c.begin(treeA); c.observe(invalid);
        assert.equal(c.finish(t,treeA),false);
        assert.equal(c.begin(invalid),null);
    }
});
check("explicit cancellation and close retire local gesture",()=>{
    const c=make(); c.observe(treeA);
    const t=c.begin(treeA);
    assert.equal(c.cancel(t),true);
    assert.equal(c.finish(t,treeA),false);
    const u=c.begin(treeA); c.clear();
    assert.equal(c.finish(u,treeA),false);
    assert.equal(c.begin(treeA),null);
});
check("begin cannot silently change observed target",()=>{
    const c=make(); c.observe(treeA);
    assert.equal(c.begin(treeB),null);
    const t=c.begin(treeA);
    assert.equal(c.finish(t,treeA),true);
});
check("live gesture checks every immediate request and finishes once",()=>{
    const c=make(); c.observe(treeA);
    const t=c.begin(treeA);
    let writes=0;
    for (let i=0;i<3;i++) if(c.checkCurrent(t,treeA)) writes++;
    assert.equal(writes,3);
    assert.equal(c.finish(t,treeA),true);
    assert.equal(c.checkCurrent(t,treeA),false);
});
check("live gesture cannot mutate replacement even with same label after ABA",()=>{
    const c=make(); c.observe(treeA); const t=c.begin(treeA);
    assert.equal(c.checkCurrent(t,treeA),true);
    c.observe(treeB); c.observe(treeA);
    assert.equal(c.checkCurrent(t,treeA),false);
    assert.equal(c.finish(t,treeA),false);
});
check("live request mismatch retires original ticket",()=>{
    const c=make(); c.observe(treeA); const t=c.begin(treeA);
    assert.equal(c.checkCurrent(t,treeB),false);
    assert.equal(c.checkCurrent(t,treeA),false);
});
check("live stale or foreign ticket cannot retire current gesture",()=>{
    const c=make(), foreign=make(); c.observe(treeA); foreign.observe(treeA);
    const old=c.begin(treeA), fresh=c.begin(treeA);
    assert.equal(c.checkCurrent(old,treeB),false);
    assert.equal(c.checkCurrent(foreign.begin(treeA),treeA),false);
    assert.equal(c.checkCurrent(fresh,treeA),true);
});
check("live gestures retire on revision, withdrawal and cancel",()=>{
    const c=make();
    for(const next of ["local-tree-a:r2",null]) {
        c.observe(treeA); const t=c.begin(treeA);
        c.observe(next); c.observe(treeA);
        assert.equal(c.checkCurrent(t,treeA),false);
    }
    c.observe(treeA); const t=c.begin(treeA); c.cancel(t);
    assert.equal(c.checkCurrent(t,treeA),false);
});
console.log("UI2_S6A_LOCAL_TARGET_LATCH_PASS",count);
