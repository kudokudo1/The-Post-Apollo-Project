"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const source=fs.readFileSync(path.resolve(__dirname,"../../widgets/cpuplus/CpuPlusKillResourceDraft.js"),"utf8");
const draft=new Function(source+"\nreturn {cards,find,identity,stageMode,stageValue,mode,value,summary,priorityPresets,stagePriorityPreset,hasValue,cpuIds,stageAffinity,affinitySelection,dropAffinity,ioPriority,stageIoPriority,swapChoice,stageSwap,quotaChoice,quotaRange,stageQuota,bandwidthChoice,stageBandwidth,taskChoice,stageTasks,stepTasks};")();
test("K8d seven distinct resource categories without imaginary GPU/network actuators",()=>{
    const rows=draft.cards();
    assert.deepEqual(rows.map(x=>x.key),["cpu","memory","swap","disk","threads","gpu","network"]);
    assert.deepEqual(rows.find(x=>x.key==="gpu").controls,[]);
    assert.deepEqual(rows.find(x=>x.key==="network").controls,[]);
    assert.match(rows.find(x=>x.key==="memory").scope,/RLIMIT_AS/);
    assert.match(rows.find(x=>x.key==="cpu").note,/CURRENT LEADER MASK/);
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
    assert.equal(draft.stageValue(values,"cpu","quota",999),values);
    values=draft.stageValue(values,"cpu","quota",100);
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
    assert.ok(ui.includes("anchors.top: resourceHeaderSection.bottom"));
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
    assert.ok(ui.includes('model: resourcePanel.key==="memory" || resourcePanel.key==="swap" || resourcePanel.key==="threads" ? [] : resourcePanel.spec.controls'));
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
    assert.ok(ui.includes("y: headerContent.y + resourceInfoStrip.y + resourceInfoStrip.height + 3"));
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

test("K8d5 header uses two rules, no enclosing box, and no status before resource tabs",()=>{
    const ui=fs.readFileSync(path.resolve(__dirname,"../../widgets/cpuplus/CpuPlusKillResourceConsole.qml"),"utf8");
    const start=ui.indexOf('id: resourceHeaderSection');
    const end=ui.indexOf('id: bodyScroll',start);
    assert.ok(start>0 && end>start);
    const header=ui.slice(start,end);
    const intro=header.slice(0,header.indexOf('id: headerContent'));
    assert.ok(ui.includes('Item {\n        id: resourceHeaderSection'));
    assert.ok(!intro.includes('border.width'));
    assert.ok(!intro.includes('border.color'));
    assert.ok(!intro.includes('color: Colors.dark'));
    const title=header.indexOf('objectName: "cpuPlusResourceHeaderTitle"');
    const titleRule=header.indexOf('objectName: "cpuPlusResourceTitleDivider"');
    const tabs=header.indexOf('id: resourceFilters');
    const info=header.indexOf('id: resourceInfoStrip');
    const status=header.indexOf('objectName: "cpuPlusResourceIdentityStatus"');
    const capability=header.indexOf('objectName: "cpuPlusResourceCapabilityStatus"');
    const sectionRule=header.indexOf('objectName: "cpuPlusResourceHeaderDivider"');
    assert.ok(title>=0 && title<titleRule && titleRule<tabs && tabs<info
        && info<status && status<capability && capability<sectionRule);
    assert.equal((header.match(/objectName: "cpuPlusResourceTitleDivider"/g)||[]).length,1);
    assert.equal((header.match(/objectName: "cpuPlusResourceHeaderDivider"/g)||[]).length,1);
    assert.match(header.slice(titleRule,tabs),/height: 2\s*color: Colors.red/);
    assert.match(header.slice(sectionRule),/height: 2\s*color: Colors.red/);
    assert.ok(!header.slice(titleRule,tabs).includes('SELECT VERIFIED PROCESS'));
    assert.match(ui,/anchors.top: resourceHeaderSection.bottom/);
    assert.ok(ui.includes('objectName: "cpuPlusResourceInformationButton"'));
    assert.ok(ui.includes('label: "APPLY LOCKED // UNVERIFIED"'));
});

test("K8e1a priority presets stage only explicit priority; quota is not implied",()=>{
    assert.deepEqual(draft.priorityPresets().map(x=>x.nice),[0,10,19]);
    const empty={};
    assert.equal(draft.stagePriorityPreset(empty,"invalid"),empty);
    let v=draft.stagePriorityPreset(empty,"background");
    assert.equal(draft.value(v,"cpu","nice"),10);
    assert.equal(draft.mode(v,"cpu"),"manual");
    assert.equal(draft.hasValue(v,"cpu","quota"),false);
    assert.ok(draft.summary(v)[0].includes("NICE 10"));
    assert.ok(!draft.summary(v)[0].includes("QUOTA DRAFT"));
    v=draft.stageValue(v,"cpu","quota",60);
    v=draft.stagePriorityPreset(v,"lowest");
    assert.equal(draft.value(v,"cpu","nice"),19);
    assert.equal(draft.value(v,"cpu","quota"),60);
    assert.ok(draft.summary(v)[0].includes("QUOTA DRAFT 60"));
    assert.ok(draft.summary(draft.stageMode({},"cpu","manual"))[0].includes("NO CPU VALUES SELECTED"));
    const ui=fs.readFileSync(path.resolve(__dirname,"../../widgets/cpuplus/CpuPlusKillResourceConsole.qml"),"utf8");
    assert.ok(ui.includes('objectName: "cpuPlusPriorityDial"'));
    assert.ok(ui.includes('objectName: "cpuPlusPriorityPresets"'));
    assert.ok(ui.includes('selectorMode: "continuous"'));
    assert.ok(ui.includes('snapContinuousToStep: true'));
    assert.ok(ui.includes('onLeftClicked: root.choosePriorityPreset(modelData.key)'));
    assert.ok(ui.includes('root.stageNumber("cpu","nice",Math.round(value))'));
    assert.ok(ui.includes('showInstrumentChassis: false'));
});

test("K8e2a CPU editor defaults to editable without creating a draft",()=>{
    assert.equal(draft.mode({},"cpu"),"manual");
    assert.equal(draft.mode({},"memory"),"hold");
    assert.equal(draft.summary({}).length,0);
    assert.equal(draft.hasValue({},"cpu","nice"),false);
    const ui=fs.readFileSync(path.resolve(__dirname,"../../widgets/cpuplus/CpuPlusKillResourceConsole.qml"),"utf8");
    assert.ok(ui.includes("currentValue: root.priorityValue()"));
    assert.ok(ui.includes("NORMAL // PREVIEW"));
});
test("K8e2a sparse observed CPU masks only; never empty or out-of-mask",()=>{
    const allowed=draft.cpuIds("0-2,8,11-12");
    assert.deepEqual(allowed,[0,1,2,8,11,12]);
    for(const invalid of ["","-","2-1","0,0","1-999999","abc","1,,2"])
        assert.deepEqual(draft.cpuIds(invalid),[]);
    assert.deepEqual(draft.affinitySelection({},allowed),allowed);
    const previous=draft.stagePriorityPreset({},"background");
    assert.equal(draft.stageAffinity(previous,allowed,[]),previous);
    assert.equal(draft.stageAffinity(previous,allowed,[3]),previous);
    assert.equal(draft.stageAffinity(previous,allowed,[8,8]),previous);
    const next=draft.stageAffinity(previous,allowed,[12,8]);
    assert.deepEqual(draft.affinitySelection(next,allowed),[8,12]);
    assert.ok(draft.summary(next)[0].includes("AFFINITY 8,12"));
    assert.equal(draft.value(draft.dropAffinity(next),"cpu","nice"),10);
    assert.equal(draft.hasValue(draft.dropAffinity(next),"cpu","affinity"),false);
    assert.equal(draft.summary(draft.dropAffinity(draft.stageAffinity({},allowed,[8]))).length,0);
});

test("K8e3a disk class and level are explicit; no bandwidth defaults",()=>{
    assert.equal(draft.mode({},"disk"),"manual");
    assert.equal(draft.summary({}).length,0);
    assert.deepEqual(draft.ioPriority({}),{kind:"best_effort",level:4});
    const empty={};
    for(const [kind,level] of [["realtime",0],["best_effort",-1],["best_effort",8],["best_effort",2.5]])
        assert.equal(draft.stageIoPriority(empty,kind,level),empty);
    const best=draft.stageIoPriority(empty,"best_effort",2);
    assert.ok(draft.summary(best)[0].includes("BEST EFFORT 2"));
    assert.ok(!draft.summary(best)[0].includes("READ DRAFT"));
    assert.ok(!draft.summary(best)[0].includes("WRITE DRAFT"));
    const idle=draft.stageIoPriority(best,"idle",2);
    assert.deepEqual(draft.ioPriority(idle),{kind:"idle"});
    assert.ok(draft.summary(idle)[0].endsWith("IDLE"));
    const both=draft.stageIoPriority(draft.stageValue({},"disk","read",50),"idle");
    assert.ok(draft.summary(both)[0].includes("READ DRAFT 50"));
    assert.ok(!draft.summary(both)[0].includes("WRITE DRAFT"));
    const ui=fs.readFileSync(path.resolve(__dirname,"../../widgets/cpuplus/CpuPlusKillResourceConsole.qml"),"utf8");
    assert.ok(ui.includes('objectName: "cpuPlusIoPriorityDial"'));
    assert.ok(ui.includes('objectName: "cpuPlusIoClass-"'));
    assert.ok(ui.includes('root.modeFor("disk")==="manual" && ioRow.bestEffort'));
    assert.ok(ui.includes('PREVIEW // NOT OBSERVED'));
    assert.ok(ui.includes('objectName: "cpuPlusIoRealtimeLocked"'));
});

test("K8e4 memory editor shares existing owner draft, explicit restore and guarded review",()=>{
    const ui=fs.readFileSync(path.resolve(__dirname,"../../widgets/cpuplus/CpuPlusKillResourceConsole.qml"),"utf8");
    const parent=fs.readFileSync(path.resolve(__dirname,"../../widgets/cpuplus/CpuPlusKillWorkspace.qml"),"utf8");
    assert.ok(ui.includes('objectName: "cpuPlusSharedMemorySlider"'));
    assert.ok(ui.includes('maximumValue: 97'));
    assert.ok(ui.includes('label: "RESTORE ORIGINAL"'));
    assert.ok(ui.includes('available: root.memoryEditable && root.memoryManaged'));
    assert.ok(ui.includes('Draft.summary(staged).length===0'));
    assert.ok(ui.includes('root.memoryReviewRequested(root.memoryDraftPercent)'));
    assert.ok(parent.includes('memoryDraftPercent: workspace.stagedLimitPercent'));
    assert.ok(parent.includes('processView.presentation.limitResultFor(workspace.currentTask).message'));
    assert.ok(parent.includes('return prepareAction("limit",percent);'));
    assert.ok(parent.includes('percent!==stagedLimitPercent'));
    assert.ok(parent.includes('percent>=0 && percent<=97'));
    assert.ok(parent.includes('percent===100 && processView.hasSoftLimit()'));
    assert.ok(parent.includes('RESTORE ORIGINAL LIMIT'));
    assert.ok(parent.includes('processView.dangerActionUnlocked(currentTask,"limit")'));
    // Existing percentage conversion plus maximum>=4*minimum guarantees
    // a finite 97% request stays below the legacy 99.5% release threshold.
    for (const ratio of [0,0.01,0.1,0.25])
        assert.ok(ratio+(1-ratio)*97/98.5<0.995);
});

test("K8e5 swap finite zero, max and restoration have separate semantics",()=>{
    const empty={};
    assert.equal(draft.mode(empty,"swap"),"manual");
    assert.deepEqual(draft.swapChoice(empty),{kind:"preview",mib:1024});
    assert.equal(draft.summary(empty).length,0);
    for(const value of [-1,8193,1.5,NaN,"512"])
        assert.equal(draft.stageSwap(empty,"budget",value),empty);
    assert.equal(draft.stageSwap(empty,"restore",0),empty);
    const exact=draft.stageSwap(empty,"budget",513);
    assert.deepEqual(draft.swapChoice(exact),{kind:"budget",mib:513});
    assert.ok(draft.summary(exact)[0].includes("513 MiB"));
    const zero=draft.stageSwap(exact,"budget",0);
    assert.deepEqual(draft.swapChoice(zero),{kind:"budget",mib:0});
    assert.ok(draft.summary(zero)[0].includes("0 MiB"));
    const max=draft.stageSwap(zero,"uncapped",0);
    assert.deepEqual(draft.swapChoice(max),{kind:"uncapped"});
    assert.equal(draft.hasValue(max,"swap","budget"),false);
    assert.ok(draft.summary(max)[0].includes("memory.swap.max=max"));
    assert.ok(!draft.summary(max)[0].includes("0 MiB"));
    assert.deepEqual(draft.swapChoice(draft.stageValue(max,"swap","budget",517)),{kind:"budget",mib:517});
    const ui=fs.readFileSync(path.resolve(__dirname,"../../widgets/cpuplus/CpuPlusKillResourceConsole.qml"),"utf8");
    assert.ok(ui.includes('objectName: "cpuPlusSwapBudgetSlider"'));
    assert.ok(ui.includes('objectName: "cpuPlusSwapExactInput"'));
    assert.ok(ui.includes('modelData.key!=="restore"'));
    assert.ok(ui.includes('editIdentity===root.targetIdentity'));
    assert.ok(ui.includes('NO CAP IS NOT RESTORE'));
});

test("K8e6 CPU quota is explicit multi-CPU time, never implicit affinity or priority",()=>{
    const empty={};
    assert.deepEqual(draft.quotaChoice(empty),{kind:"preview",percent:75});
    assert.equal(draft.quotaRange(empty,[]),100);
    assert.equal(draft.quotaRange(empty,[0,2,8]),300);
    assert.equal(draft.summary(empty).length,0);
    for(const value of [0,-1,301,1.5,NaN,"150"])
        assert.equal(draft.stageQuota(empty,"budget",value,300),empty);
    assert.equal(draft.stageQuota(empty,"restore",100,300),empty);
    const q=draft.stageQuota(empty,"budget",237,300);
    assert.deepEqual(draft.quotaChoice(q),{kind:"budget",percent:237});
    assert.ok(draft.summary(q)[0].includes("237 % OF ONE CPU"));
    assert.ok(!draft.hasValue(q,"cpu","nice"));
    assert.ok(!draft.hasValue(q,"cpu","affinity"));
    assert.equal(draft.quotaRange(q,[0]),237);
    const priority=draft.stagePriorityPreset(q,"background");
    const max=draft.stageQuota(priority,"uncapped",0,300);
    assert.deepEqual(draft.quotaChoice(max),{kind:"uncapped"});
    assert.equal(draft.hasValue(max,"cpu","quota"),false);
    assert.equal(draft.value(max,"cpu","nice"),10);
    assert.ok(draft.summary(max)[0].includes("cpu.max=max"));
    assert.ok(!draft.summary(max)[0].includes("QUOTA DRAFT 75"));
    const again=draft.stageQuota(max,"budget",100,300);
    assert.deepEqual(draft.quotaChoice(again),{kind:"budget",percent:100});
    const ui=fs.readFileSync(path.resolve(__dirname,"../../widgets/cpuplus/CpuPlusKillResourceConsole.qml"),"utf8");
    assert.ok(ui.includes("Draft.quotaRange(staged,allowedCpuIds)"));
    assert.ok(ui.includes('objectName: "cpuPlusQuotaChoice-"'));
    assert.ok(ui.includes('GROUP CAPACITY UNVERIFIED // RESTORE LOCKED'));
    assert.ok(ui.includes('maximumValue: field.quotaField ? root.quotaMaximum'));
});

test("K8e7 read/write cap intents are independent of each other and I/O priority",()=>{
    const empty={};
    assert.equal(draft.summary(empty).length,0);
    assert.deepEqual(draft.bandwidthChoice(empty,"read"),{kind:"preview",mib:64});
    assert.deepEqual(draft.bandwidthChoice(empty,"write"),{kind:"preview",mib:64});
    for (const v of [0,-1,513,1.5,NaN,"32"])
        assert.equal(draft.stageBandwidth(empty,"read","budget",v),empty);
    assert.equal(draft.stageBandwidth(empty,"read","restore",64),empty);
    assert.equal(draft.stageBandwidth(empty,"wrong","budget",64),empty);
    const read=draft.stageBandwidth(empty,"read","budget",73);
    assert.ok(draft.summary(read)[0].includes("READ DRAFT 73 MiB/s"));
    assert.ok(!draft.summary(read)[0].includes("WRITE DRAFT"));
    assert.ok(!draft.summary(read)[0].includes("I/O PRIORITY"));
    const write=draft.stageBandwidth(read,"write","budget",27);
    const priority=draft.stageIoPriority(write,"idle",0);
    const max=draft.stageBandwidth(priority,"read","uncapped",0);
    assert.deepEqual(draft.bandwidthChoice(max,"read"),{kind:"uncapped"});
    assert.equal(draft.hasValue(max,"disk","read"),false);
    assert.deepEqual(draft.bandwidthChoice(max,"write"),{kind:"budget",mib:27});
    assert.deepEqual(draft.ioPriority(max),{kind:"idle"});
    assert.ok(draft.summary(max)[0].includes("READ NO CAP // rbps=max"));
    assert.ok(draft.summary(max)[0].includes("WRITE DRAFT 27"));
    assert.ok(!draft.summary(max)[0].includes("READ DRAFT"));
    const both=draft.stageBandwidth(max,"write","uncapped",0);
    assert.ok(draft.summary(both)[0].includes("WRITE NO CAP // wbps=max"));
    const again=draft.stageBandwidth(both,"read","budget",11);
    assert.deepEqual(draft.bandwidthChoice(again,"read"),{kind:"budget",mib:11});
    assert.deepEqual(draft.bandwidthChoice(again,"write"),{kind:"uncapped"});
    const ui=fs.readFileSync(path.resolve(__dirname,"../../widgets/cpuplus/CpuPlusKillResourceConsole.qml"),"utf8");
    assert.ok(ui.includes('objectName: "cpuPlusBandwidth-"+field.modelData.key+"-"+modelData.key'));
    assert.ok(ui.includes('root.stageBandwidth(field.modelData.key,"budget",Number(text))'));
    assert.ok(ui.includes('if (field.quotaField || field.bandwidthField) return;'));
    assert.ok(ui.includes('64 MiB/s // PREVIEW, NOT OBSERVED'));
});

test("K8e8 task cap, numeric steps and uncapped intent are explicit",()=>{
    const empty={};
    assert.equal(draft.mode(empty,"threads"),"manual");
    assert.deepEqual(draft.taskChoice(empty),{kind:"preview",count:64});
    assert.equal(draft.summary(empty).length,0);
    for(const count of [0,-1,513,1.5,NaN,"64"])
        assert.equal(draft.stageTasks(empty,"budget",count),empty);
    assert.equal(draft.stageTasks(empty,"restore",64),empty);
    assert.equal(draft.stepTasks(empty,2),empty);
    const lower=draft.stepTasks(empty,-1);
    assert.deepEqual(draft.taskChoice(lower),{kind:"budget",count:63});
    assert.ok(draft.summary(lower)[0].includes("TASK COUNT 63 TASKS"));
    assert.deepEqual(draft.taskChoice(draft.stepTasks(lower,1)),{kind:"budget",count:64});
    const min=draft.stageTasks(empty,"budget",1);
    const max=draft.stageTasks(empty,"budget",512);
    assert.equal(draft.stepTasks(min,-1),min);
    assert.equal(draft.stepTasks(max,1),max);
    const uncapped=draft.stageTasks(max,"uncapped",0);
    assert.deepEqual(draft.taskChoice(uncapped),{kind:"uncapped"});
    assert.equal(draft.hasValue(uncapped,"threads","tasks"),false);
    assert.ok(draft.summary(uncapped)[0].includes("pids.max=max"));
    assert.ok(!draft.summary(uncapped)[0].includes("TASK COUNT"));
    assert.deepEqual(draft.taskChoice(draft.stepTasks(uncapped,1)),{kind:"budget",count:65});
    assert.deepEqual(draft.taskChoice(draft.stageValue(empty,"threads","tasks",137)),{kind:"budget",count:137});
    const other=draft.stagePriorityPreset(empty,"background");
    assert.equal(draft.value(draft.stageTasks(other,"budget",32),"cpu","nice"),10);
    const ui=fs.readFileSync(path.resolve(__dirname,"../../widgets/cpuplus/CpuPlusKillResourceConsole.qml"),"utf8");
    assert.ok(ui.includes('objectName: "cpuPlusTaskMinus"'));
    assert.ok(ui.includes('objectName: "cpuPlusTaskPlus"'));
    assert.ok(ui.includes('objectName: "cpuPlusTaskExactInput"'));
    assert.ok(ui.includes('64 TASKS // PREVIEW, NOT OBSERVED'));
    assert.ok(ui.includes('editIdentity===root.targetIdentity'));
    assert.ok(ui.includes('CAP RESTRICTS NEW TASK CREATION, NOT EXISTING THREADS'));
});
