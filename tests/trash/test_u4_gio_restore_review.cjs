"use strict";
// U4: execute actual QML review method in a sandbox, never touch real GIO.
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const assert=require("node:assert/strict"),test=require("node:test");
const qml=fs.readFileSync(path.resolve(__dirname,"../../modules/Trash.qml"),"utf8");
const deck=fs.readFileSync(
    path.resolve(__dirname,"../../components/TrashLifecycleActionDeck.qml"),"utf8");

function method(name){
    const i=qml.indexOf("    function "+name+"(");
    assert.ok(i>=0,"Missing function "+name);
    const start=qml.indexOf("{",i);
    let depth=0;
    for(let j=start;j<qml.length;j++){
        if(qml[j]==="{")depth++;
        if(qml[j]==="}")depth--;
        if(depth===0)return qml.slice(i,j+1);
    }
    throw Error("Invalid QML method "+name);
}
const methods=["restoreItem","reviewGioFileRestore"].map(method).join("\n");
const uri="trash:///camera%201.png";
const original="/home/user/Pictures/camera 1.png";
const key="a".repeat(64),rev="b".repeat(64);
function row(overrides={}){
    return {uri,original,name:"camera 1.png",reviewId:key,...overrides};
}
function harness(overrides={}){
    const ctx={
        menuOpen:true,activeMode:"trash",indexReady:true,lastError:false,
        busy:false,researchBusy:false,archiveBusy:false,archiveV2Busy:false,
        snapshotBusy:false,researchBurnId:"",confirmMode:"",burnUiStage:"",
        revision:rev,items:[row()],calls:[],cleared:0,
        clearConfirmation(){ctx.cleared++},
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
function review(ctx,owner="filesystem-gio",id=key,revision=rev){
    return vm.runInContext("reviewGioFileRestore("
        +JSON.stringify(owner)+","+JSON.stringify(id)+","
        +JSON.stringify(revision)+")",ctx);
}

test("GIO restore from exact indexed key delegates once to old backend",()=>{
    const ctx=harness();
    assert.equal(review(ctx),true);
    assert.deepEqual(ctx.calls,[{action:"restore",args:["restore",uri,original]}]);
    assert.equal(ctx.cleared,1);
    assert.equal(ctx.busy,true);
    assert.equal(review(ctx),false);
    assert.equal(ctx.calls.length,1);
});
test("malformed token, wrong owner, stale index and forged revision all refuse",()=>{
    for(const args of [
        ["hospital",key,rev],
        ["trashpp-managed-copy",key,rev],
        ["filesystem-gio","not-a-hash",rev],
        ["filesystem-gio","c".repeat(64),rev],
        ["filesystem-gio",key,"old"],
        ["filesystem-gio",key,"c".repeat(64)],
    ]){
        const ctx=harness();
        assert.equal(review(ctx,...args),false,args.join("|"));
        assert.equal(ctx.calls.length,0);
    }
});
test("fail closed on stale, mismatched, duplicate or source-owned row",()=>{
    const bad=[
        [row({reviewId:"c".repeat(64)})],
        [row({uri:"file:///untrusted"})],
        [row({original:"relative/path"})],
        [row(),row()],
        [],
    ];
    for(const items of bad){
        const ctx=harness({items});
        assert.equal(review(ctx),false,JSON.stringify(items));
        assert.equal(ctx.calls.length,0);
    }
});
test("no restore request while closed, wrong screen, busy or Burn confirmation",()=>{
    const flags=[
        ["menuOpen",false],["activeMode","archive"],["activeMode","burn"],
        ["indexReady",false],["lastError",true],["busy",true],
        ["researchBusy",true],["archiveBusy",true],["archiveV2Busy",true],
        ["snapshotBusy",true],["researchBurnId","pending"],
        ["confirmMode","item"],["burnUiStage","clicked"]
    ];
    for(const [name,value] of flags){
        const ctx=harness({[name]:value});
        assert.equal(review(ctx),false,name);
        assert.equal(ctx.calls.length,0);
    }
});
test("UI review deck is file-only, uses SHA token and never requests Burn",()=>{
    assert.match(qml,/id: gioRestoreReviewDeck/);
    assert.match(qml,/visible: isGioFile/);
    assert.match(qml,/ownerId: "filesystem-gio"/);
    assert.match(qml,/resourceId: String\(trashEntry.modelData.reviewId \|\| ""\)/);
    assert.match(qml,/resourceRevision: String\(trashLauncher.revision\)/);
    assert.match(qml,/showRestore: isGioFile/);
    assert.match(qml,/showTrash: false/);
    assert.match(qml,/showBurn: false/);
    assert.match(qml,/onRestoreReviewRequested:/);
    assert.match(deck,/property string resourceRevisionKind: "sha256"/);
    assert.doesNotMatch(qml,/onBurnReviewRequested:/);
});
test("managed bin Restore and all final Burn flows remain separate",()=>{
    assert.match(qml,/visible: trashEntry.modelData.entryType === "record"/);
    assert.match(qml,/trashLauncher.restoreResearchCopy\(/);
    assert.match(qml,/trashLauncher.armResearchBurn\(/);
    assert.match(qml,/trashLauncher.armBurn\(/);
    assert.match(qml,/onLeftClicked: trashLauncher.advanceResearchBurn\(\)/);
    assert.match(qml,/"BURN_ALL_CONFIRMED"/);
    assert.match(qml,/"BURN_SAVED_COPY_CONFIRMED"/);
});

