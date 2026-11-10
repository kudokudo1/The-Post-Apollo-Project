"use strict";
// Synthetic Trash++ UI safety: managed-bin-only bulk burn, no GIO or real files.
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const test = require("node:test");
const qml = fs.readFileSync(path.resolve(__dirname,"../../modules/Trash.qml"),"utf8");

function method(name) {
    const i=qml.indexOf("    function "+name+"(");
    assert.ok(i>=0,"missing "+name);
    const start=qml.indexOf("{",i);
    let depth=0;
    for(let j=start;j<qml.length;j++){
        if(qml[j]==="{")depth++;
        if(qml[j]==="}")depth--;
        if(depth===0)return qml.slice(i,j+1);
    }
    throw new Error("unbalanced QML function "+name);
}
const funcs=["armResearchBurnAll","advanceResearchBurn",
             "confirmResearchBurn","clearResearchBurn"].map(method).join("\n");
const rows=[
    {id:"a".repeat(32),kind:"SAVED EVENT",title:"Saved storm",state:"trashed"},
    {id:"b".repeat(32),kind:"SAVED RESEARCH",title:"Saved demo scrape",state:"trashed"},
    {id:"c".repeat(32),kind:"SAVED EVENT",title:"Still archived",state:"archived"}
];
function harness(overrides={}){
    const ctx={
        menuOpen:true,activeMode:"burn",
        researchBusy:false,busy:false,confirmMode:"",
        researchRows:rows,
        researchBinRows:rows.filter(r=>r.state==="trashed"),
        researchBinCount:2,
        researchBinDigest:"d".repeat(64),
        researchRevision:12,
        researchBurnId:"",researchBurnScope:"",
        researchBurnTitle:"",researchBurnRevision:-1,
        researchBurnCount:0,researchBurnDigest:"",
        researchBurnPointerRelocated:false,researchBurnClickArmed:false,
        researchBurnLoadComplete:false,researchBurnLoadProgress:0,
        calls:[],started:0,stopped:0,
        researchBurnArmAnimation:{
            restart(){ctx.started++},
            stop(){ctx.stopped++}
        },
        runResearch(action,args){ctx.calls.push({action,args:Array.from(args)});return true;},
        ...overrides
    };
    vm.createContext(ctx);
    vm.runInContext(funcs,ctx);
    return ctx;
}

test("Burn All arms only known managed bin, never GIO system Trash",()=>{
    const ctx=harness();
    assert.equal(vm.runInContext("armResearchBurnAll()",ctx),true);
    assert.equal(ctx.researchBurnScope,"all");
    assert.equal(ctx.researchBurnId,"__managed_bin_all__");
    assert.equal(ctx.researchBurnCount,2);
    assert.equal(ctx.researchBurnDigest,"d".repeat(64));
    assert.equal(ctx.researchBurnRevision,12);
    assert.equal(ctx.calls.length,0);
    assert.match(qml,/onLeftClicked: trashLauncher.armBurnAll\(\)/);
    assert.match(qml,/onLeftClicked: trashLauncher.armResearchBurnAll\(\)/);
    assert.match(qml,/MANAGED BIN ONLY/);
    assert.match(qml,/GIO system Trash/);
});

test("pointer travel, first click, load and second click required for bulk burn",()=>{
    const ctx=harness();
    vm.runInContext("armResearchBurnAll()",ctx);
    assert.equal(vm.runInContext("advanceResearchBurn()",ctx),false);
    assert.equal(ctx.calls.length,0);
    ctx.researchBurnPointerRelocated=true;
    assert.equal(vm.runInContext("advanceResearchBurn()",ctx),true);
    assert.equal(ctx.researchBurnClickArmed,true);
    assert.equal(ctx.started,1);
    assert.equal(ctx.calls.length,0);
    assert.equal(vm.runInContext("advanceResearchBurn()",ctx),false);
    ctx.researchBurnLoadProgress=1;
    ctx.researchBurnLoadComplete=true;
    assert.equal(vm.runInContext("advanceResearchBurn()",ctx),true);
    assert.deepEqual(Array.from(ctx.calls),[{
        action:"burn-all",
        args:["12","2","d".repeat(64),"BURN_ALL_MANAGED_COPIES_CONFIRMED"]
    }]);
    assert.equal(ctx.researchBurnId,"");
    assert.equal(ctx.researchBurnScope,"");
    assert.equal(ctx.researchBurnClickArmed,false);
});

test("bulk burn detects count, digest, revision changes before submission",()=>{
    for(const override of [
        {researchBinCount:3},
        {researchBinDigest:"a".repeat(64)},
        {researchRevision:13},
        {researchBinRows:[]}
    ]){
        const ctx=harness();
        vm.runInContext("armResearchBurnAll()",ctx);
        ctx.researchBurnPointerRelocated=true;
        vm.runInContext("advanceResearchBurn()",ctx);
        ctx.researchBurnLoadComplete=true;
        Object.assign(ctx,override);
        assert.equal(vm.runInContext("advanceResearchBurn()",ctx),false);
        assert.equal(ctx.calls.length,0);
    }
});

test("bulk Burn All refuses empty or outside its Burn tab",()=>{
    for(const override of [
        {researchBinCount:0,researchBinRows:[]},
        {researchBinDigest:""},
        {activeMode:"trash"},
        {activeMode:"archive"},
        {researchBusy:true},
        {confirmMode:"all"},
        {researchBurnId:"a".repeat(32)}
    ]){
        const ctx=harness(override);
        assert.equal(vm.runInContext("armResearchBurnAll()",ctx),false);
        assert.equal(ctx.calls.length,0);
    }
});

test("Cancel does not delete or retain any armed bulk identity",()=>{
    const ctx=harness();
    vm.runInContext("armResearchBurnAll()",ctx);
    ctx.researchBurnPointerRelocated=true;
    vm.runInContext("advanceResearchBurn()",ctx);
    vm.runInContext("clearResearchBurn()",ctx);
    assert.equal(ctx.researchBurnId,"");
    assert.equal(ctx.researchBurnScope,"");
    assert.equal(ctx.researchBurnDigest,"");
    assert.equal(ctx.researchBurnCount,0);
    assert.equal(ctx.researchBurnClickArmed,false);
    assert.equal(ctx.researchBurnLoadProgress,0);
    assert.equal(ctx.calls.length,0);
});

test("combined Trash list has file/record filters and owner-specific actions",()=>{
    assert.match(qml,/readonly property var trashDisplayRows:/);
    assert.match(qml,/fileRows\.concat\(copyRows\)/);
    assert.match(qml,/model: trashLauncher.trashDisplayRows/);
    assert.match(qml,/id: trashSourceFilters/);
    for(const id of ["all","files","records","events","research"]){
        assert.ok(qml.includes('{id:"'+id+'", label:'),id);
    }
    assert.match(qml,/trashEntry\.modelData\.entryType === "record"/);
    assert.match(qml,/trashLauncher\.restoreResearchCopy\(/);
    assert.match(qml,/trashLauncher\.restoreItem\(/);
    assert.match(qml,/trashLauncher\.armResearchBurn\(/);
    assert.match(qml,/trashLauncher\.armBurn\(/);
});

test("loading fill covers full button face with black clipped label and no wash",()=>{
    const start=qml.indexOf("id: confirmManagedResearchBurn");
    const end=qml.indexOf("id: cancelManagedResearchBurn",start);
    const button=qml.slice(start,end);
    assert.match(button,/label: ""/);
    assert.match(button,/id: researchBurnFace/);
    assert.match(button,/id: researchBurnLoadFill/);
    assert.match(button,/height: Math\.max\(0, parent\.height - 4\)/);
    assert.match(button,/\* trashLauncher\.researchBurnLoadProgress/);
    assert.match(button,/id: researchBurnLabelWhite/);
    assert.match(button,/id: researchBurnLabelClip/);
    assert.match(button,/clip: true/);
    assert.match(button,/color: Colors\.black\s+text: researchBurnFace\.displayedLabel/);
    assert.match(button,/color: Colors\.white\s+text: researchBurnFace\.displayedLabel/);
    assert.match(button,/visible: researchBurnFace\.loading/);
    assert.match(button,/&& !trashLauncher\.researchBurnLoadComplete/);
    // A black fill in every visual button state. Arming is a reversible
    // visual animation; after loading, the opaque black face returns.
    for (const state of ["idle", "hover", "pressed", "selected", "keyboardSelected"]) {
        assert.ok(button.includes(state+"FillColor: Colors.black"),state);
    }
    for (const glow of ["contentGlowEnabled","softGlowEnabled","wideGlowEnabled"]) {
        assert.ok(button.includes(glow+": false"),glow);
    }
    assert.doesNotMatch(button,/FillColor: "transparent"/);
    assert.doesNotMatch(button,/id: researchBurnLoadBar/);
});
