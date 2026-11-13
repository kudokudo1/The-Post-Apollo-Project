"use strict";
// Trash++ U6: execute existing Camera queue GIO method + new strict reviewer
// with synthetic selections. No user files, host GIO, or live Quickshell.
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const assert=require("node:assert/strict"),test=require("node:test");
const root=path.resolve(__dirname,"../..");
const camera=fs.readFileSync(path.join(root,"widgets/CameraW.qml"),"utf8");
const cleanup=fs.readFileSync(path.join(root,"widgets/CameraCleanupView.qml"),"utf8");
const deck=fs.readFileSync(path.join(root,"components/TrashLifecycleActionDeck.qml"),"utf8");

function method(name) {
    const pos=camera.indexOf("    function "+name+"(");
    assert.ok(pos>=0,"Missing Camera method "+name);
    const start=camera.indexOf("{",pos);
    let depth=0;
    for(let i=start;i<camera.length;i++) {
        if(camera[i]==="{")depth++;
        if(camera[i]==="}")depth--;
        if(depth===0)return camera.slice(pos,i+1);
    }
    throw Error("Unbalanced Camera method "+name);
}
const code=["trashQueuedNow","reviewQueuedCameraTrash"].map(method).join("\n");
const A="/home/synthetic/Pictures/example.png";
const B="/home/synthetic/Videos/movie.mp4";
const owner="camera-gio",resource="camera-cleanup-queue";
function fixture(overrides={}) {
    const ctx={
        busy:false,menuOpen:false,hostedCleanupActive:true,
        cleanupQueueOpen:true,batchMode:true,activeView:"cleanup",
        cleanupTechnique:"swipe",nativeRegionSelecting:false,
        zoomWebBusy:false,cleanupQueueRevision:7,batchPaths:[A,B],
        cleanupCustomFolder:"",cleanupLoadedFolder:"",
        galleryRequestedFolder:"",galleryRequestedView:"cleanup",
        batchPreview:{old:"snapshot"},batchReviewKey:"old",batchReceipt:"old",
        feedback:"",calls:[],
        run(action,args){
            ctx.calls.push({action,args:Array.from(args)});
            ctx.busy=true;
            return true;
        },
        ...overrides
    };
    vm.createContext(ctx);
    vm.runInContext(code,ctx);
    return ctx;
}
function review(ctx,o=owner,r=resource,v="7") {
    return vm.runInContext("reviewQueuedCameraTrash("
        +JSON.stringify(o)+","+JSON.stringify(r)+","
        +JSON.stringify(v)+")",ctx);
}
test("one explicit current queue click uses old Camera-owned one-click GIO backend",()=>{
    const ctx=fixture();
    assert.equal(review(ctx),true);
    assert.deepEqual(ctx.calls,[{
        action:"trashBatchNow",
        args:["trash-batch-now",JSON.stringify([A,B]),"MOVE_TO_TRASH",
              "--folder",""]
    }]);
    assert.equal(ctx.busy,true);
    assert.equal(ctx.batchPreview,null);
    assert.equal(ctx.batchReviewKey,"");
    assert.equal(ctx.batchReceipt,"");
    assert.deepEqual(ctx.batchPaths,[A,B]); // UI must await backend receipt
    assert.equal(review(ctx),false);
    assert.equal(ctx.calls.length,1);
});
test("wrong owner/queue, old revision, bad number and overflow refuse",()=>{
    for(const [ownerId,resourceId,v] of [
        ["hospital",resource,"7"],["social",resource,"7"],
        ["filesystem-gio",resource,"7"],[owner,"../queue","7"],
        [owner,"camera-gallery-selection","7"],
        [owner,resource,"6"],[owner,resource,"8"],
        [owner,resource,"07"],[owner,resource,"-1"],
        [owner,resource,"7.0"],[owner,resource,"a".repeat(64)],
        [owner,resource,""]
    ]) {
        const ctx=fixture();
        assert.equal(review(ctx,ownerId,resourceId,v),false);
        assert.equal(ctx.calls.length,0);
    }
    const exhausted=fixture({cleanupQueueRevision:2147483647});
    assert.equal(review(exhausted,owner,resource,"2147483647"),false);
    assert.equal(exhausted.calls.length,0);
});
test("stale source folder or absent Cleanup scan cannot move queue",()=>{
    for(const opts of [
        {cleanupCustomFolder:"/tmp/other"},
        {cleanupLoadedFolder:"/tmp/changed"},
        {galleryRequestedFolder:"/tmp/changed"},
        {galleryRequestedView:"gallery"}
    ]) {
        const ctx=fixture(opts);
        assert.equal(review(ctx),false,JSON.stringify(opts));
        assert.equal(ctx.calls.length,0);
    }
});
test("closed queue, inactive host, other modes and busy operations refuse",()=>{
    for(const [k,v] of [
        ["hostedCleanupActive",false],["cleanupQueueOpen",false],
        ["batchMode",false],["activeView","gallery"],
        ["cleanupTechnique","desktop"],["busy",true],
        ["nativeRegionSelecting",true],["zoomWebBusy",true]
    ]) {
        const ctx=fixture({[k]:v});
        assert.equal(review(ctx),false,k);
        assert.equal(ctx.calls.length,0);
    }
});
test("empty, duplicate, relative, malformed, oversized queues refuse",()=>{
    for(const rows of [
        [],[A,A],["relative/file.png"],[A,""],[A,1],
        Array.from({length:501},(_,i)=>"/home/synthetic/f"+i+".png")
    ]) {
        const ctx=fixture({batchPaths:rows});
        assert.equal(review(ctx),false,"rows "+rows.length);
        assert.equal(ctx.calls.length,0);
    }
});
test("counter increments on every immutable queue replacement and never wraps",()=>{
    assert.match(camera,/property int cleanupQueueRevision: 0/);
    assert.match(camera,/onBatchPathsChanged:/);
    assert.match(camera,/cleanupQueueRevision < 2147483647/);
    assert.match(camera,/cleanupQueueRevision \+= 1/);
    const assignments=camera.match(/batchPaths\s*=\s*/g)||[];
    assert.ok(assignments.length>=8,"must track queue transitions");
    // Selection modes copy arrays and reassign the property; no in-place
    // mutations of the QML-owned batchPaths array may bypass the counter.
    assert.doesNotMatch(camera,/\bbatchPaths\.(?:push|pop|splice|shift|unshift|sort|reverse)\s*\(/);
    const mutators=["batchToggle","batchSelectLoaded","batchClear",
        "batchRemovePath","swipeDecide","swipeUndo","huntFire","huntUndo"];
    for(const action of mutators)
        assert.match(camera,new RegExp("function "+action+"\\("));
});
test("Swipe and Hunt remain selection-only; no gesture can call GIO",()=>{
    for(const name of ["swipeDecide","huntFire","swipeUndo","huntUndo"]) {
        const body=method(name);
        assert.doesNotMatch(body,/\b(?:run|trashQueuedNow|reviewQueuedCameraTrash)\s*\(/,name);
        assert.doesNotMatch(body,/gio|subprocess|remove\(/i,name);
    }
});
test("U1 shared queue control only offers TRASH, not Restore/Burn",()=>{
    assert.match(deck,/resourceRevisionKind === "queue-counter"/);
    assert.match(deck,/property string resourceRevisionKind: "sha256"/);
    assert.match(cleanup,/id: cleanupQueueTrashReviewDeck/);
    assert.match(cleanup,/ownerId: "camera-gio"/);
    assert.match(cleanup,/resourceId: "camera-cleanup-queue"/);
    assert.match(cleanup,/resourceRevisionKind: "queue-counter"/);
    assert.match(cleanup,/resourceRevision: String\(camera\.cleanupQueueRevision\)/);
    assert.match(cleanup,/showRestore: false/);
    assert.match(cleanup,/showBurn: false/);
    assert.match(cleanup,/onTrashReviewRequested:/);
    assert.match(cleanup,/camera\.reviewQueuedCameraTrash\(/);
    assert.doesNotMatch(cleanup,/onBurnReviewRequested:/);
});
test("the single-file Gallery confirmation and desktop screenshot plan are independent",()=>{
    assert.match(camera,/function confirmSelectedTrash\(\)/);
    assert.match(camera,/function reviewSelectedCameraTrash\(/); // stacked U5
    assert.match(camera,/function confirmCleanup\(\)/);
    assert.match(cleanup,/onLeftClicked: camera\.confirmCleanup\(\)/);
    assert.match(cleanup,/label: "PREVIEW MATCHES"/);
    assert.match(camera,/"trash-batch-now", JSON\.stringify\(batchPaths\)/);
});
