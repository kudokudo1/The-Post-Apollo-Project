"use strict";
// U3 tests QML's real review adapter with disposable records, no live GIO.
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
const code=["trashResearchCopy","restoreResearchCopy",
            "reviewManagedCopyAction"].map(method).join("\n");
const copyId="0123456789abcdef0123456789abcdef";
function makeRow(state="archived", kind="SAVED EVENT"){
    return {id:copyId,kind,state,title:"Synthetic copy"};
}
function harness(overrides={}){
    const ctx={
        menuOpen:true,activeMode:"archive",busy:false,researchBusy:false,
        archiveBusy:false,archiveV2Busy:false,snapshotBusy:false,
        researchBurnId:"",confirmMode:"",burnUiStage:"",
        researchRevision:8,researchRows:[makeRow()],calls:[],
        runResearch(action,args){
            ctx.calls.push({action,args:Array.from(args)});
            ctx.researchBusy=true;
            return true;
        },
        ...overrides,
    };
    vm.createContext(ctx);
    vm.runInContext(code,ctx);
    return ctx;
}
function request(ctx,action,id=copyId,revision="8",owner="trashpp-managed-copy"){
    return vm.runInContext("reviewManagedCopyAction("
        +JSON.stringify(action)+","+JSON.stringify(owner)+","
        +JSON.stringify(id)+","+JSON.stringify(revision)+")",ctx);
}

test("archived owned copy routes one review request to existing revision-checked trash",()=>{
    const ctx=harness();
    assert.equal(request(ctx,"trash"),true);
    assert.deepEqual(ctx.calls,[{action:"trash",args:[copyId,"8"]}]);
    assert.equal(ctx.researchBusy,true);
    assert.equal(request(ctx,"trash"),false);
    assert.equal(ctx.calls.length,1);
});
test("trashed managed copy restores only through original owned backend",()=>{
    const ctx=harness({researchRows:[makeRow("trashed")]});
    assert.equal(request(ctx,"restore"),true);
    assert.deepEqual(ctx.calls,[{action:"restore",args:[copyId,"8"]}]);
});
test("stale revision or malformed counter does not execute",()=>{
    for(const revision of ["7","9","-1","08","8 ","8.0","a".repeat(64),""]){
        const ctx=harness();
        assert.equal(request(ctx,"trash",copyId,revision),false,revision);
        assert.equal(ctx.calls.length,0);
    }
});
test("cannot spoof another owner, an unknown ID or a source record",()=>{
    for(const overrides of [
        {owner:"weather-events"},
        {owner:"hospital"},
        {id:"../../private"},
        {id:"a".repeat(32)},
    ]){
        const ctx=harness();
        assert.equal(request(ctx,"trash",
            overrides.id??copyId,"8",overrides.owner??"trashpp-managed-copy"),
            false);
        assert.equal(ctx.calls.length,0);
    }
    for(const kind of ["EVENT HISTORY","HUB TASK","V2 SNAPSHOT"]){
        const ctx=harness({researchRows:[makeRow("archived",kind)]});
        assert.equal(request(ctx,"trash"),false,kind);
        assert.equal(ctx.calls.length,0);
    }
});
test("refuse wrong record state, operation and any Burn request",()=>{
    const ctx=harness();
    for(const action of ["restore","burn","delete","archive",""]){
        assert.equal(request(ctx,action),false,action);
    }
    ctx.researchRows=[makeRow("trashed")];
    assert.equal(request(ctx,"trash"),false);
    assert.equal(ctx.calls.length,0);
});
test("state transitions, busy operations and confirmation overlays deny",()=>{
    const flags=[
        ["menuOpen",false],["activeMode","trash"],["activeMode","burn"],
        ["busy",true],["researchBusy",true],["archiveBusy",true],
        ["archiveV2Busy",true],["snapshotBusy",true],
        ["researchBurnId",copyId],["confirmMode","item"],
        ["burnUiStage","clicked"],
    ];
    for(const [key,value] of flags){
        const ctx=harness({[key]:value});
        assert.equal(request(ctx,"trash"),false,key);
        assert.equal(ctx.calls.length,0);
    }
});
test("shared deck keeps default SHA witness and accepts explicit safe decimal opt-in",()=>{
    assert.match(deck,/property string resourceRevisionKind: "sha256"/);
    assert.match(deck,/resourceRevisionKind === "store-counter"/);
    assert.match(deck,/\^\(0\|\[1-9\]\[0-9\]\{0,9\}\)\$/);
    assert.match(deck,/&& revisionReady/);
    assert.match(qml,/id: managedCopyLifecycleActions/);
    assert.match(qml,/resourceRevisionKind: "store-counter"/);
    assert.match(qml,/showBurn: false/);
    assert.match(qml,/onTrashReviewRequested:/);
    assert.match(qml,/onRestoreReviewRequested:/);
    assert.match(qml,/function reviewManagedCopyAction\(/);
    assert.doesNotMatch(qml,/onBurnReviewRequested:/);
});
test("U3 does not change source SAVE COPY or existing final Burn gates",()=>{
    assert.match(qml,/label: "SAVE COPY"/);
    assert.match(qml,/trashLauncher.saveWeatherEventCopy\(modelData\)/);
    assert.match(qml,/trashLauncher.saveDemoCopy\(modelData\)/);
    assert.match(qml,/label: "BURN COPY"/);
    assert.match(qml,/onLeftClicked: trashLauncher.armResearchBurn\(modelData\)/);
    assert.match(qml,/onLeftClicked: trashLauncher.advanceResearchBurn\(\)/);
});
