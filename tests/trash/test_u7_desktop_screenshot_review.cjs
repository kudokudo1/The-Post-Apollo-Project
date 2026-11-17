"use strict";
// U7: invoke the exact Camera desktop review + existing confirmation
// against synthetic preview metadata. No GIO, files or live Quickshell.
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const assert=require("node:assert/strict"),test=require("node:test");
const root=path.resolve(__dirname,"../..");
const qml=fs.readFileSync(path.join(root,"widgets/CameraW.qml"),"utf8");
const view=fs.readFileSync(path.join(root,"widgets/CameraCleanupView.qml"),"utf8");
const deck=fs.readFileSync(path.join(root,"components/TrashLifecycleActionDeck.qml"),"utf8");

function method(name){
    const begin=qml.indexOf("    function "+name+"(");
    assert.ok(begin>=0,"Missing Camera method "+name);
    const brace=qml.indexOf("{",begin);
    let n=0;
    for(let i=brace;i<qml.length;i++){
        if(qml[i]==="{") n++;
        if(qml[i]==="}") n--;
        if(n===0) return qml.slice(begin,i+1);
    }
    throw Error("Unbalanced Camera QML method "+name);
}
const code=["confirmCleanup","reviewDesktopCameraTrash"].map(method).join("\n");
const owner="camera-gio",scope="camera-desktop-screenshots";
const token="0123456789abcdef0123456789abcdef";
const preview={
    planId:token,count:3,bytes:1033,
    source:"Desktop screenshot-like PNG/JPEG/WEBP",
    sample:["Screenshot1.png","Screenshot2.webp"]
};
function fixture(overrides={}){
    const ctx={
        hostedCleanupActive:true,activeView:"cleanup",
        cleanupTechnique:"desktop",cleanupQueueOpen:false,
        busy:false,nativeRegionSelecting:false,zoomWebBusy:false,
        trashPreview:{...preview},calls:[],
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
function request(ctx,o=owner,id=scope,rev=token) {
    return vm.runInContext("reviewDesktopCameraTrash("
        +JSON.stringify(o)+","+JSON.stringify(id)+","
        +JSON.stringify(rev)+")",ctx);
}

test("previewed Desktop screenshot plan delegates once to old Camera GIO plan backend",()=>{
    const ctx=fixture();
    assert.equal(request(ctx),true);
    assert.deepEqual(ctx.calls,[{
        action:"trash",args:["trash",token,"MOVE_TO_TRASH"]
    }]);
    assert.equal(ctx.trashPreview,null);
    assert.equal(ctx.busy,true);
    assert.equal(request(ctx),false);
    assert.equal(ctx.calls.length,1);
});
test("preview is required and no empty or no-match plan can move files",()=>{
    for(const p of [null,undefined,{},{
        ...preview,planId:""
    },{...preview,count:0},{...preview,count:-1}]){
        const ctx=fixture({trashPreview:p});
        assert.equal(request(ctx),false,String(p?.count));
        assert.equal(ctx.calls.length,0);
    }
});
test("wrong owner, scope, plan token or stale preview is denied",()=>{
    for(const args of [
        ["hospital",scope,token],["social",scope,token],
        ["filesystem-gio",scope,token],
        [owner,"camera-cleanup-queue",token],
        [owner,"../Documents",token],
        [owner,scope,"f".repeat(32)],
        [owner,scope,token.toUpperCase()],
        [owner,scope,"a".repeat(64)],
        [owner,scope,""]
    ]){
        const ctx=fixture();
        assert.equal(request(ctx,...args),false,args.join("|"));
        assert.equal(ctx.calls.length,0);
        assert.equal(ctx.trashPreview.planId,token);
    }
});
test("wrong mode, inactive host and concurrently busy Camera fail closed",()=>{
    for(const [name,value] of [
        ["hostedCleanupActive",false],
        ["activeView","gallery"],["activeView","capture"],
        ["cleanupTechnique","batch"],["cleanupTechnique","swipe"],
        ["cleanupTechnique","hunt"],["cleanupQueueOpen",true],
        ["busy",true],["nativeRegionSelecting",true],
        ["zoomWebBusy",true]
    ]){
        const ctx=fixture({[name]:value});
        assert.equal(request(ctx),false,name);
        assert.equal(ctx.calls.length,0);
    }
});
test("malformed source scope, preview count and bytes never go to backend",()=>{
    for(const plan of [
        {...preview,source:"HOME all files"},
        {...preview,source:"Desktop screenshot-like PNG/JPEG/WEBP "},
        {...preview,count:"3"}, {...preview,count:1.5},
        {...preview,count:20001},{...preview,bytes:-1},
        {...preview,bytes:"1033"},{...preview,bytes:Infinity},
        {...preview,bytes:NaN}
    ]){
        const ctx=fixture({trashPreview:plan});
        assert.equal(request(ctx),false,JSON.stringify(plan));
        assert.equal(ctx.calls.length,0);
    }
    const ceiling=fixture({trashPreview:{...preview,count:20000}});
    assert.equal(request(ceiling),true); // backend's own MAX_TRASH
    assert.equal(ceiling.calls.length,1);
});
test("control remains second click after preview and never grants Burn/Restore",()=>{
    assert.match(view,/label: "PREVIEW MATCHES"/);
    assert.match(view,/onLeftClicked: camera\.previewCleanup\(\)/);
    assert.match(view,/id: desktopScreenshotTrashReviewDeck/);
    assert.match(view,/ownerId: "camera-gio"/);
    assert.match(view,/resourceId: "camera-desktop-screenshots"/);
    assert.match(view,/resourceRevisionKind: "camera-plan"/);
    assert.match(view,/resourceRevision: camera\.trashPreview/);
    assert.match(view,/onTrashReviewRequested:/);
    assert.match(view,/camera\.reviewDesktopCameraTrash\(/);
    assert.match(view,/showRestore: false/);
    assert.match(view,/showBurn: false/);
    assert.doesNotMatch(view,/onBurnReviewRequested:/);
    assert.match(deck,/resourceRevisionKind === "camera-plan"/);
    assert.match(qml,/function previewCleanup\(\)/);
    assert.match(qml,/return run\("preview", \["preview-trash"\]\)/);
    assert.match(qml,/function confirmCleanup\(\)/);
    assert.match(qml,/function reviewDesktopCameraTrash\(/);
    assert.match(qml,/return confirmCleanup\(\);/);
});
test("Gallery selected, shared Cleanup queue, Swipe and Hunt are unchanged",()=>{
    for(const name of [
        "reviewSelectedCameraTrash","reviewQueuedCameraTrash",
        "trashQueuedNow","swipeDecide","huntFire"
    ])assert.match(qml,new RegExp("function "+name+"\\("));
    assert.match(view,/id: cleanupQueueTrashReviewDeck/);
    assert.match(view,/camera\.reviewQueuedCameraTrash\(/);
    assert.match(view,/onLeftClicked: camera\.batchRemovePath\(modelData\)/);
    assert.doesNotMatch(view,/onLeftClicked: camera\.confirmCleanup\(\)/); // no direct bypass
});
