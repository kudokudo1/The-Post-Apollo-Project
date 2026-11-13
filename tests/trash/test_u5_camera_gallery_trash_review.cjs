"use strict";
// Trash++ U5 // Synthetic Camera Gallery one-use plan review, no GIO/files.
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const assert=require("node:assert/strict"),test=require("node:test");
const root=path.resolve(__dirname,"../..");
const camera=fs.readFileSync(path.join(root,"widgets/CameraW.qml"),"utf8");
const deck=fs.readFileSync(path.join(root,"components/TrashLifecycleActionDeck.qml"),"utf8");
const cleanup=fs.readFileSync(path.join(root,"widgets/CameraCleanupView.qml"),"utf8");

function method(name){
    const start=camera.indexOf("    function "+name+"(");
    assert.notEqual(start,-1,"Missing Camera method "+name);
    const open=camera.indexOf("{",start);
    let depth=0;
    for(let i=open;i<camera.length;i++){
        if(camera[i]==="{")depth++;
        if(camera[i]==="}")depth--;
        if(depth===0)return camera.slice(start,i+1);
    }
    throw Error("Malformed QML function "+name);
}
const methods=["confirmSelectedTrash","reviewSelectedCameraTrash"].map(method).join("\n");
const media="/home/synthetic/Pictures/Screenshots/example.png";
const plan="0123456789abcdef0123456789abcdef";
const owner="camera-gio", id="camera-gallery-selection";
function fixture(overrides={}){
    const ctx={
        menuOpen:true,activeView:"gallery",busy:false,
        nativeRegionSelecting:false,zoomWebBusy:false,
        selectedPath:media,selectedRecord:{path:media,name:"example.png"},
        selectedTrashPreview:{path:media,planId:plan,name:"example.png"},
        galleryFiles:[{path:media,name:"example.png"}],calls:[],
        run(action,args){
            ctx.calls.push({action,args:Array.from(args)});
            ctx.busy=true;
            return true;
        },
        ...overrides
    };
    vm.createContext(ctx);
    vm.runInContext(methods,ctx);
    return ctx;
}
function review(ctx,o=owner,i=id,r=plan){
    return vm.runInContext("reviewSelectedCameraTrash("
        +JSON.stringify(o)+","+JSON.stringify(i)+","
        +JSON.stringify(r)+")",ctx);
}

test("one reviewed Camera item delegates once to existing one-use plan backend",()=>{
    const ctx=fixture();
    assert.equal(review(ctx),true);
    assert.deepEqual(ctx.calls,[{
        action:"trashSelected",
        args:["trash-selected",plan,"MOVE_TO_TRASH"]
    }]);
    assert.equal(ctx.selectedTrashPreview,null);
    assert.equal(ctx.busy,true);
    assert.equal(review(ctx),false);
    assert.equal(ctx.calls.length,1);
});
test("preview is required; no first-click move or arbitrary file path",()=>{
    for(const options of [
        {selectedTrashPreview:null},
        {selectedTrashPreview:{}},
        {selectedPath:""},
        {selectedRecord:null},
        {galleryFiles:[]}
    ]){
        const ctx=fixture(options);
        assert.equal(review(ctx),false,JSON.stringify(options));
        assert.equal(ctx.calls.length,0);
    }
});
test("selection change after preview rejects request and preserves preview",()=>{
    const different="/home/synthetic/Pictures/changed.png";
    for(const options of [
        {selectedPath:different},
        {selectedRecord:{path:different}},
        {selectedTrashPreview:{path:different,planId:plan}},
        {galleryFiles:[{path:different}]},
    ]){
        const ctx=fixture(options);
        assert.equal(review(ctx),false,JSON.stringify(options));
        assert.equal(ctx.calls.length,0);
        assert.deepEqual(ctx.selectedTrashPreview,options.selectedTrashPreview ?? {
            path:media,planId:plan,name:"example.png"});
    }
});
test("wrong owner, fake item ID and stale/invalid one-use plan fail closed",()=>{
    const requests=[
        ["hospital",id,plan],
        ["finance",id,plan],
        ["filesystem-gio",id,plan],
        [owner,"../selected",plan],
        [owner,"some-other-file",plan],
        [owner,id,"f".repeat(32)],
        [owner,id,"a".repeat(64)],
        [owner,id,""],
        [owner,id,plan.toUpperCase()]
    ];
    for(const args of requests){
        const ctx=fixture();
        assert.equal(review(ctx,...args),false,args.join("|"));
        assert.equal(ctx.calls.length,0);
    }
});
test("hidden/closed Camera or other operation cannot commit",()=>{
    const flags=[
        ["menuOpen",false],["activeView","cleanup"],
        ["activeView","capture"],["activeView","zoom"],
        ["busy",true],["nativeRegionSelecting",true],
        ["zoomWebBusy",true]
    ];
    for(const [k,v] of flags){
        const ctx=fixture({[k]:v});
        assert.equal(review(ctx),false,k);
        assert.equal(ctx.calls.length,0);
    }
});
test("shared deck uses exact camera plan type, never grants Restore or Burn",()=>{
    assert.match(deck,/property string resourceRevisionKind: "sha256"/);
    assert.match(deck,/resourceRevisionKind === "store-counter"/);
    assert.match(deck,/resourceRevisionKind === "camera-plan"/);
    assert.match(deck,/\^\[0-9a-f\]\{32\}\$/);
    assert.match(camera,/id: cameraSelectedTrashReviewDeck/);
    assert.match(camera,/ownerId: "camera-gio"/);
    assert.match(camera,/resourceId: "camera-gallery-selection"/);
    assert.match(camera,/resourceRevisionKind: "camera-plan"/);
    assert.match(camera,/onTrashReviewRequested:/);
    assert.match(camera,/showRestore: false/);
    assert.match(camera,/showBurn: false/);
    assert.doesNotMatch(camera,/onBurnReviewRequested:/);
});
test("Camera preview and independent Cleanup/queue pathways are preserved",()=>{
    assert.match(camera,/function previewSelectedTrash\(\)/);
    assert.match(camera,/return run\("previewSelected", \["preview-selected", selectedPath\]\)/);
    assert.match(camera,/function confirmSelectedTrash\(\)/);
    assert.match(camera,/plan\.path !== selectedPath/);
    assert.match(camera,/return run\("trashSelected", \["trash-selected", plan\.planId, "MOVE_TO_TRASH"\]\)/);
    assert.match(camera,/function trashQueuedNow\(\)/);
    assert.match(camera,/"trash-batch-now", JSON\.stringify\(batchPaths\)/);
    assert.match(cleanup,/onLeftClicked: camera\.trashQueuedNow\(\)/);
    assert.match(cleanup,/onLeftClicked: camera\.confirmCleanup\(\)/);
    assert.match(camera,/function confirmCleanup\(\)/);
    assert.doesNotMatch(camera,/onLeftClicked: camera\.confirmSelectedTrash\(\)/);
});
