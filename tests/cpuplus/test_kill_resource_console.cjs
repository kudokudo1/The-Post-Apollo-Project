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

test("K8d3 places modes beside the primary instrument and actions above divider",()=>{
    const ui=fs.readFileSync(path.resolve(__dirname,"../../widgets/cpuplus/CpuPlusKillResourceConsole.qml"),"utf8");
    // The mode cluster must be a child of the FIRST instrument row; the
    // selected editor is frameless rather than another boxed filter card.
    assert.match(ui,/Item \{\s*id: resourcePanel/);
    assert.ok(!ui.includes("id: modeRow"));
    assert.ok(ui.includes("id: instrumentRow"));
    assert.ok(ui.includes("id: modeCluster"));
    const instrument=ui.indexOf('id: instrumentRow');
    const slider=ui.indexOf('CpuPlusDiagnosticSlider {',instrument);
    const modes=ui.indexOf('id: modeCluster',slider);
    const number=ui.indexOf('EXACT DRAFT // ',modes);
    assert.ok(instrument < slider && slider < modes && modes < number);
    assert.match(ui,/visible: field.index === 0/);
    assert.match(ui,/columns: 2/);
    assert.match(ui,/model: \["off","manual","auto","hold"\]/);
    assert.match(ui,/adjustable: root.selectionReady && root.modeFor\(resourcePanel.key\) === "manual"/);
    assert.ok(ui.includes('objectName: "cpuPlusResourceWorkspaceActions"'));
    const actions=ui.indexOf('objectName: "cpuPlusResourceWorkspaceActions"');
    const divider=ui.indexOf('objectName: "cpuPlusResourceFooterDivider"');
    const apply=ui.indexOf('objectName: "cpuPlusResourceApplyLocked"');
    assert.ok(actions>number && actions<divider && divider<apply);
    const clear=ui.indexOf('objectName: "cpuPlusResourceClearDraft"',actions);
    const review=ui.indexOf('objectName: "cpuPlusResourceReviewDraft"',actions);
    assert.match(ui.slice(clear,review),/accentColor: Colors.red/);
    assert.match(ui.slice(review,divider),/accentColor: Colors.yellow/);
    assert.match(ui.slice(apply),/accentColor: Colors.green/);
    assert.match(ui.slice(apply),/available: false/);
    assert.match(ui,/objectName: "cpuPlusResourceFooterDivider"[\s\S]*?color: Colors.red/);
    assert.ok(ui.includes('objectName: "cpuPlusResourceDraftActionsStrip"'));
    assert.ok(ui.includes('anchors.bottom: draftActionsStrip.top'));
    assert.match(ui,/id: draftActionsStrip[\s\S]*?anchors.bottom: footer.top/);
    assert.match(ui,/objectName: "cpuPlusResourceWorkspaceActions"/);
    assert.match(ui,/text: "RESOURCE CONTROL \/\/ DRAFT"[\s\S]*?color: Colors.orange[\s\S]*?color: Colors.red/);
});

test("K8d3 has a functional right-aligned information button directly below filters",()=>{
    const ui=fs.readFileSync(path.resolve(__dirname,"../../widgets/cpuplus/CpuPlusKillResourceConsole.qml"),"utf8");
    assert.match(ui,/import "\.\.\/appcontrol"/);
    assert.match(ui,/id: headerContent[\s\S]*?id: resourceFilters[\s\S]*?id: resourceInfoStrip/);
    assert.match(ui,/id: resourceInformationButton[\s\S]*?anchors.right: parent.right/);
    assert.match(ui,/objectName: "cpuPlusResourceInformationButton"/);
    assert.match(ui,/onLeftClicked: root.informationOpen = !root.informationOpen/);
    assert.match(ui,/objectName: "cpuPlusResourceInformationPopup"/);
    assert.match(ui,/visible: root.informationOpen/);
    assert.match(ui,/anchors.top: resourceInfoStrip.bottom/);
    assert.match(ui,/APPLY REMAINS LOCKED UNTIL THE RESOURCE BACKEND IS VERIFIED/);
});

test("K8d4 fixed Favorites-style header separates metadata from control workspace",()=>{
    const ui=fs.readFileSync(path.resolve(__dirname,"../../widgets/cpuplus/CpuPlusKillResourceConsole.qml"),"utf8");
    const header=ui.indexOf('id: resourceHeaderSection');
    const filters=ui.indexOf('id: resourceFilters');
    const info=ui.indexOf('id: resourceInfoStrip');
    const body=ui.indexOf('id: bodyScroll');
    const actions=ui.indexOf('id: draftActionsStrip');
    const footer=ui.indexOf('id: footer');
    assert.ok(header>0 && filters>header && info>filters && body>info
        && actions>body && footer>actions);
    const top=ui.slice(header,body);
    assert.ok(top.includes('objectName: "cpuPlusResourceHeaderTitle"'));
    assert.ok(top.includes('objectName: "cpuPlusResourceIdentityStatus"'));
    assert.ok(top.includes('objectName: "cpuPlusResourceCategoryFilters"'));
    assert.ok(top.includes('objectName: "cpuPlusResourceSelectedTitle"'));
    assert.ok(top.includes('objectName: "cpuPlusResourceCapabilityStatus"'));
    assert.ok(top.includes('objectName: "cpuPlusResourceInformationButton"'));
    assert.ok(top.includes('objectName: "cpuPlusResourceHeaderDivider"'));
    assert.ok(top.includes('height: headerContent.implicitHeight + 16'));
    assert.ok(top.includes('color: Colors.red'));
    const middle=ui.slice(body,actions);
    assert.ok(middle.includes('anchors.top: resourceHeaderSection.bottom'));
    assert.ok(middle.includes('id: resourcePanel'));
    assert.ok(middle.includes('id: modeCluster'));
    assert.ok(middle.includes('CpuPlusDiagnosticSlider {'));
    assert.ok(!middle.includes('text: resourcePanel.spec.scope'));
    assert.ok(!middle.includes('CAPABILITY AND WRITE PERMISSION // NOT VERIFIED'));
    assert.ok(ui.slice(actions,footer).includes('objectName: "cpuPlusResourceWorkspaceActions"'));
    assert.ok(ui.slice(footer).includes('APPLY LOCKED // UNVERIFIED'));
});
