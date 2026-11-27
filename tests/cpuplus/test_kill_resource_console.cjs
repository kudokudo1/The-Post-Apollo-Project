"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const source=fs.readFileSync(path.resolve(__dirname,"../../widgets/cpuplus/CpuPlusKillResourceDraft.js"),"utf8");
const draft=new Function(source+"\nreturn {cards,find,identity,stageMode,stageValue,mode,value,summary};")();
test("K8d seven distinct resource categories without imaginary GPU/network actuators",()=>{
    const rows=draft.cards();
    assert.deepEqual(rows.map(x=>x.key),["cpu","memory","swap","disk","threads","gpu","network"]);
    assert.deepEqual(rows.find(x=>x.key==="gpu").controls,[]);
    assert.deepEqual(rows.find(x=>x.key==="network").controls,[]);
    assert.match(rows.find(x=>x.key==="memory").scope,/RLIMIT_AS/);
    assert.match(rows.find(x=>x.key==="cpu").note,/NOT ENUMERATED/);
});
test("K8d exact process identity and draft-only mode/value validation",()=>{
    assert.equal(draft.identity({pid:1,startTicks:8,comm:"x"}),"");
    assert.equal(draft.identity({pid:123,startTicks:0,comm:"x"}),"");
    assert.notEqual(draft.identity({pid:123,startTicks:100,comm:"x"}),draft.identity({pid:123,startTicks:101,comm:"x"}));
    let values={};
    assert.equal(draft.stageMode(values,"gpu","manual"),values);
    assert.equal(draft.stageMode(values,"cpu","nonsense"),values);
    values=draft.stageMode(values,"cpu","manual");
    assert.equal(draft.mode(values,"cpu"),"manual");
    values=draft.stageValue(values,"cpu","quota",999);
    assert.equal(draft.value(values,"cpu","quota"),100);
    values=draft.stageValue(values,"cpu","nice",-999);
    assert.equal(draft.value(values,"cpu","nice"),-20);
    values=draft.stageValue(values,"disk","read",67.9);
    assert.equal(draft.value(values,"disk","read"),68);
    assert.equal(draft.stageValue(values,"gpu","write",100),values);
    assert.equal(draft.stageValue(values,"cpu","nice",NaN),values);
    values=draft.stageMode(values,"memory","auto");
    assert.ok(draft.summary(values).some(x=>x.includes("POLICY NOT DEFINED")));
    assert.ok(draft.summary(values).some(x=>x.includes("PRIORITY / NICE -20")));
    assert.equal(draft.summary({}).length,0);
});
test("K8d QML is a contained presentation, no process mutator or helper",()=>{
    const ui=fs.readFileSync(path.resolve(__dirname,"../../widgets/cpuplus/CpuPlusKillResourceConsole.qml"),"utf8");
    const parent=fs.readFileSync(path.resolve(__dirname,"../../widgets/cpuplus/CpuPlusKillWorkspace.qml"),"utf8");
    assert.match(parent,/id: resourceBay[\s\S]*?CpuPlusKillResourceConsole \{/);
    assert.match(parent,/visible: !reviewPanel.visible/);
    assert.match(ui,/onTargetIdentityChanged:\s*root.clearDraft\(\)/);
    assert.ok(ui.includes("CpuPlusDiagnosticSlider {"));
    assert.ok(ui.includes("id: resourceFilters"));
    assert.ok(ui.includes("model: root.categories"));
    assert.ok(ui.includes('objectName: "cpuPlusResourceFilter-"'));
    assert.ok(ui.includes("id: resourcePanel"));
    assert.ok(ui.includes("readonly property var spec: root.selectedResource"));
    assert.ok(ui.includes("anchors.top: resourceFilters.bottom"));
    assert.ok(!ui.includes("id: resourceCard"));
    assert.ok(ui.includes("onLeftClicked: root.selectResource(modelData.key)"));
    assert.match(ui,/label: "REVIEW"/);
    assert.match(ui,/label: "CLEAR DRAFT"/);
    assert.match(ui,/APPLY LOCKED/);
    assert.match(ui,/onValueRequested: function\(value\)/);
    for(const forbidden of ["Quickshell.execDetached","Process {","setLimitMiB(","setLimitPercent(","signalDispatch.exec(","prlimit(","onLeftClicked: workspace.gate.confirm"])
        assert.equal(ui.includes(forbidden),false,"forbidden actuator "+forbidden);
});

test("K8d2 top filters select one editor while retaining drafts",()=>{
    const ui=fs.readFileSync(path.resolve(__dirname,"../../widgets/cpuplus/CpuPlusKillResourceConsole.qml"),"utf8");
    for (const name of ["CPU","MEM","SWAP","DISK","THR","GPU","NET"])
        assert.ok(ui.includes(':"'+name+'"') || ui.includes(':"'+name+'",'));
    assert.ok(ui.includes('property string selectedKey: "cpu"'));
    assert.ok(ui.includes("selected: root.selectedKey === modelData.key"));
    assert.ok(ui.includes("function selectResource(key)"));
    assert.ok(ui.includes("bodyScroll.contentY = 0"));
    assert.ok(ui.includes("model: resourcePanel.spec.controls"));
    assert.ok(ui.includes('model: ["off","manual","auto","hold"]'));
    assert.ok(ui.includes('visible: root.modeFor(resourcePanel.key) === "manual"'));
    const updated=draft.stageValue({}, "cpu", "nice", 8);
    assert.equal(draft.value(updated,"cpu","nice"),8);
    assert.equal(draft.value(updated,"memory","virtual"),2048);
    assert.equal(draft.summary(updated).length,1);
});
