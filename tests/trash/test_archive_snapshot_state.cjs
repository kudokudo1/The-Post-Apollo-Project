"use strict";
// Synthetic QML method execution only. No desktop, GIO or user files.
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const test = require("node:test");
const qml = fs.readFileSync(
    path.join(__dirname,"../../modules/Trash.qml"),"utf8");

function sourceMethod(name) {
    const start = qml.indexOf("    function "+name+"(");
    assert.notEqual(start,-1,"missing "+name);
    const open = qml.indexOf("{",start);
    let depth=0;
    for(let i=open;i<qml.length;i++) {
        if(qml[i]==="{")depth++;
        if(qml[i]==="}")depth--;
        if(depth===0)return qml.slice(start,i+1);
    }
    throw new Error("bad QML method: "+name);
}
const methods=["snapshotSource","clearSnapshotArm",
               "requestSnapshot","consumeSnapshot"]
    .map(sourceMethod).join("\n");

function row() {
    return {
        id:"demo-1",kind:"WEB SCRAPE",ownerId:"demo-scrape",
        sourceUrl:"https://quotes.toscrape.com/page/1/",
        sourceObservedAt:"2026-10-12T10:30:00Z",
        capabilities:{saveCopy:true}
    };
}
function context(override={}) {
    const r=row(),calls=[];
    const ctx={
        menuOpen:true,activeMode:"archive",
        snapshotBusy:false,snapshotPendingAction:"",
        snapshotRecordId:"",snapshotSourceKind:"",
        snapshotIdentifier:"",snapshotTimestamp:"",
        snapshotWitness:"",snapshotStatus:"IDLE",
        researchBusy:false,archiveBusy:false,busy:false,
        confirmMode:"",researchBurnId:"",burnUiStage:"",
        archiveRows:[r],
        archiveSearchText:"",
        calls,refreshes:0,
        Quickshell:{dataDir:"/synthetic/private",
            shellPath(name){return "/trusted/"+name;}},
        snapshotCaptureProcess:{exec(args){calls.push(args);}},
        refreshArchiveV2(page,cursor,query){
            assert.equal(page,0);
            assert.equal(cursor,"");
            assert.equal(query,ctx.archiveSearchText.trim());
            ctx.refreshes++;
            return true;
        },
        Qt:{callLater(cb){cb();}},
        ...override
    };
    ctx.trashLauncher=ctx;
    vm.createContext(ctx);
    vm.runInContext(methods,ctx);
    return {ctx,r};
}
const witness="a".repeat(64);
const sid="b".repeat(32);
const digest="c".repeat(64);
function deliver(ctx,payload) {
    ctx.response=JSON.stringify(payload);
    vm.runInContext("consumeSnapshot(response)",ctx);
}
const preview={
    ok:true,kind:"snapshot-preview-v2",readOnly:true,sourceKind:"demo",
    preview:{ownerId:"demo-scrape",sourceRevision:witness}
};
const receipt={
    ok:true,kind:"snapshot-captured-v2",copyOnly:true,sourceKind:"demo",
    receipt:{id:sid,sha256:digest,size:32,
             sourceRevision:witness,ownerId:"demo-scrape"}
};

test("single click previews only, never captures or burns",()=>{
    const {ctx}=context();
    assert.equal(vm.runInContext("requestSnapshot(archiveRows[0])",ctx),true);
    assert.equal(ctx.calls.length,1);
    assert.equal(ctx.calls[0][4],"preview");
    assert.equal(ctx.calls[0][6],"demo");
    assert.equal(ctx.snapshotWitness,"");
    assert.equal(ctx.snapshotPendingAction,"preview");
    assert.equal(ctx.calls[0].some(x=>/burn|restore|trash-all/.test(String(x))),false);
});

test("matching witness arms second click and stores only independent copy",()=>{
    const {ctx}=context();
    vm.runInContext("requestSnapshot(archiveRows[0])",ctx);
    deliver(ctx,preview);
    assert.equal(ctx.snapshotBusy,false);
    assert.equal(ctx.snapshotWitness,witness);
    assert.match(ctx.snapshotStatus,/CLICK CONFIRM COPY/);
    assert.equal(vm.runInContext("requestSnapshot(archiveRows[0])",ctx),true);
    assert.equal(ctx.calls.length,2);
    assert.equal(ctx.calls[1][4],"capture");
    assert.equal(ctx.calls[1].at(-1),witness);
    assert.equal(ctx.snapshotPendingAction,"capture");
    deliver(ctx,receipt);
    assert.equal(ctx.snapshotBusy,false);
    assert.equal(ctx.snapshotWitness,"");
    assert.match(ctx.snapshotStatus,/SAVED \/\/ INDEPENDENT/);
    assert.equal(ctx.refreshes,1);
});

test("only original Weather and disposable demo rows have snapshot permission",()=>{
    const {ctx}=context();
    for(const kind of ["HUB NOTE","HUB TASK","SAVED DOSSIER",
                       "V2 SNAPSHOT","SAVED EVENT","SAVED RESEARCH"]) {
        ctx.archiveRows=[{...row(),kind,ownerId:"hospital",
                          capabilities:{saveCopy:true}}];
        assert.equal(vm.runInContext("requestSnapshot(archiveRows[0])",ctx),false);
    }
    ctx.archiveRows=[{...row(),capabilities:{saveCopy:false}}];
    assert.equal(vm.runInContext("requestSnapshot(archiveRows[0])",ctx),false);
    assert.equal(ctx.calls.length,0);
    const w={
        id:"event-1",kind:"EVENT HISTORY",ownerId:"weather-events",
        sourceEventKey:"usgs|demo-quake",sourceLastCapturedAtMs:1760001000000,
        capabilities:{saveCopy:true}
    };
    ctx.archiveRows=[w];
    assert.equal(vm.runInContext("requestSnapshot(archiveRows[0])",ctx),true);
    assert.equal(ctx.calls[0][6],"weather");
    assert.equal(ctx.calls[0].at(-1),"1760001000000");
});

test("stale source or malformed preview never arms capture",()=>{
    const {ctx}=context();
    vm.runInContext("requestSnapshot(archiveRows[0])",ctx);
    deliver(ctx,{ok:false,error:"STALE_SOURCE_REFRESH_REQUIRED"});
    assert.equal(ctx.snapshotWitness,"");
    assert.equal(ctx.snapshotRecordId,"");
    assert.match(ctx.snapshotStatus,/REFUSED/);
    vm.runInContext("requestSnapshot(archiveRows[0])",ctx);
    deliver(ctx,{...preview,sourceKind:"weather"});
    assert.equal(ctx.snapshotWitness,"");
    assert.equal(ctx.calls.length,2);
    assert.ok(ctx.calls.every(x=>x[4]==="preview"));
});

test("closing during preview cancels arming; closing during commit preserves receipt",()=>{
    const {ctx}=context();
    vm.runInContext("requestSnapshot(archiveRows[0])",ctx);
    ctx.menuOpen=false;
    deliver(ctx,preview);
    assert.equal(ctx.snapshotWitness,"");
    assert.equal(ctx.calls.length,1);
    ctx.menuOpen=true;
    vm.runInContext("requestSnapshot(archiveRows[0])",ctx);
    deliver(ctx,preview);
    vm.runInContext("requestSnapshot(archiveRows[0])",ctx);
    ctx.menuOpen=false;
    deliver(ctx,receipt);
    assert.match(ctx.snapshotStatus,/SAVED/);
    assert.equal(ctx.refreshes,0);
});
