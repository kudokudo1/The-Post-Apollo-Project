"use strict";
// Synthetic QML controller test. No Quickshell host, local Trash, or files.
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const test = require("node:test");

const qml = fs.readFileSync(
    path.resolve(__dirname, "../../modules/Trash.qml"), "utf8");

function fnSource(name) {
    const start = qml.indexOf("    function " + name + "(");
    assert.notEqual(start, -1, "missing QML function: " + name);
    const brace = qml.indexOf("{", start);
    let nesting = 0;
    for (let i = brace; i < qml.length; i++) {
        if (qml[i] === "{") nesting++;
        if (qml[i] === "}") nesting--;
        if (nesting === 0) return qml.slice(start, i + 1);
    }
    throw new Error("unterminated method " + name);
}

const methods = [
    "armResearchBurn", "advanceResearchBurn", "confirmResearchBurn",
    "clearResearchBurn"
].map(fnSource).join("\n");
const sample = {
    id: "0123456789abcdef0123456789abcdef",
    kind: "SAVED EVENT", title: "Earthquake saved copy",
    state: "trashed"
};
function harness(overrides={}) {
    const context = {
        menuOpen: true,
        researchBusy: false,
        busy: false,
        confirmMode: "",
        researchRows: [{...sample}],
        researchRevision: 8,
        researchBurnId: "",
        researchBurnTitle: "",
        researchBurnRevision: -1,
        researchBurnPointerRelocated: false,
        researchBurnClickArmed: false,
        researchBurnLoadComplete: false,
        researchBurnLoadProgress: 0,
        operations: [],
        animationRestarted: 0,
        animationStopped: 0,
        researchBurnArmAnimation: {
            restart(){ context.animationRestarted++ },
            stop(){ context.animationStopped++ }
        },
        runResearch(action,args) {
            context.operations.push({action,args: Array.from(args)});
            return true;
        },
        ...overrides
    };
    vm.createContext(context);
    vm.runInContext(methods, context);
    return context;
}

test("first Burn button click only arms, second before load cannot delete", ()=>{
    const ctx = harness();
    assert.equal(vm.runInContext("armResearchBurn(researchRows[0])",ctx),true);
    assert.equal(vm.runInContext("advanceResearchBurn()",ctx),false);
    assert.deepEqual(Array.from(ctx.operations),[]);
    ctx.researchBurnPointerRelocated = true;
    assert.equal(vm.runInContext("advanceResearchBurn()",ctx),true);
    assert.equal(ctx.researchBurnClickArmed,true);
    assert.equal(ctx.researchBurnLoadComplete,false);
    assert.equal(ctx.animationRestarted,1);
    assert.equal(vm.runInContext("advanceResearchBurn()",ctx),false);
    assert.deepEqual(Array.from(ctx.operations),[]);
});

test("click after loading burns exactly one trashed managed copy", ()=>{
    const ctx = harness();
    vm.runInContext("armResearchBurn(researchRows[0])",ctx);
    ctx.researchBurnPointerRelocated = true;
    vm.runInContext("advanceResearchBurn()",ctx);
    ctx.researchBurnLoadProgress = 1;
    ctx.researchBurnLoadComplete = true;
    assert.equal(vm.runInContext("advanceResearchBurn()",ctx),true);
    assert.deepEqual(Array.from(ctx.operations), [{
        action: "burn",
        args: [sample.id, "8", "BURN_SAVED_COPY_CONFIRMED"]
    }]);
    assert.equal(ctx.researchBurnId,"");
    assert.equal(ctx.researchBurnClickArmed,false);
    assert.equal(ctx.researchBurnLoadComplete,false);
});

test("stale revision and removed target refuse even fully armed confirmation", ()=>{
    const ctx = harness();
    vm.runInContext("armResearchBurn(researchRows[0])",ctx);
    ctx.researchBurnPointerRelocated = true;
    vm.runInContext("advanceResearchBurn()",ctx);
    ctx.researchBurnLoadComplete = true;
    ctx.researchRevision = 9;
    assert.equal(vm.runInContext("advanceResearchBurn()",ctx),false);
    assert.equal(ctx.operations.length,0);
    ctx.researchRevision = 8;
    ctx.researchRows = [];
    assert.equal(vm.runInContext("advanceResearchBurn()",ctx),false);
    assert.equal(ctx.operations.length,0);
});

test("cancel resets both click and loading state without submitting Burn", ()=>{
    const ctx = harness();
    vm.runInContext("armResearchBurn(researchRows[0])",ctx);
    ctx.researchBurnPointerRelocated = true;
    vm.runInContext("advanceResearchBurn()",ctx);
    assert.equal(vm.runInContext("clearResearchBurn()",ctx),undefined);
    assert.equal(ctx.researchBurnId,"");
    assert.equal(ctx.researchBurnClickArmed,false);
    assert.equal(ctx.researchBurnLoadComplete,false);
    assert.equal(ctx.researchBurnLoadProgress,0);
    assert.equal(ctx.animationStopped,1);
    assert.equal(ctx.operations.length,0);
});

test("weather and research copies have identical scoped Burn safety", ()=>{
    for (const kind of ["SAVED EVENT", "SAVED RESEARCH"]) {
        const ctx=harness({researchRows:[{...sample,kind}]});
        assert.equal(vm.runInContext("armResearchBurn(researchRows[0])",ctx),true);
        assert.equal(ctx.researchBurnTitle,sample.title);
    }
    const ctx=harness({researchRows:[{...sample,state:"archived"}]});
    assert.equal(vm.runInContext("armResearchBurn(researchRows[0])",ctx),false);
    assert.equal(ctx.operations.length,0);
});

test("normal bordered button stays available before pointer relocation", ()=>{
    const start=qml.indexOf("id: confirmManagedResearchBurn");
    assert.notEqual(start,-1);
    const end=qml.indexOf("id: researchBurnLoadBar",start);
    const surface=qml.slice(start,end);
    assert.match(surface,/idleBorderWidth: 2/);
    assert.match(surface,/idleBorderColor: Colors.red/);
    assert.match(surface,/available: !trashLauncher.researchBusy/);
    const enabled=surface.slice(surface.indexOf("available:"),surface.indexOf("onLeftClicked:"));
    assert.doesNotMatch(enabled,/researchBurnPointerRelocated/);
    assert.match(surface,/onLeftClicked: trashLauncher.advanceResearchBurn\(\)/);
    assert.match(surface,/CLICK TO ARM/);
    assert.match(surface,/CLICK AGAIN \/\/ BURN/);
    assert.match(qml,/id: researchBurnArmAnimation/);
    assert.match(qml,/duration: 850/);
    assert.match(qml,/onFinished:/);
});
