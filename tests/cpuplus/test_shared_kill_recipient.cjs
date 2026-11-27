"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const read = p => fs.readFileSync(path.resolve(__dirname, "../..", p), "utf8");
const recipient = read("widgets/cpuplus/CpuPlusKillWorkspace.qml");
const host = read("widgets/CpuPlusW.qml");
const donorView = read("widgets/appcontrol/TaskManagerView.qml");
const gate = read("services/kill/AppControlHubActionGate.qml");

test("CPU++ PROCESS mounts the existing Kill detail only while active", () => {
    assert.match(host, /id: sharedKillWorkspaceLoader/);
    assert.match(host, /selectedModeIndex === 1[\s\S]*?sourceComponent: CpuPlusKillWorkspace/);
    assert.match(recipient, /TaskManagerView\s*\{[\s\S]*?host: taskHost[\s\S]*?processController: processView/);
    for (const prop of ["presentationState", "graphGeometry", "hunterGraph",
                        "searchInputTarget", "safetyLockComponent"])
        assert.match(recipient, new RegExp(prop + ":\\s*[A-Za-z]+"));
    assert.match(donorView, /text: "KILLING ACTIONS"/);
    assert.match(donorView, /processController\.requestTerminate\(\)/);
    assert.match(donorView, /processController\.requestRestart\(\)/);
});

test("recipient uses live owner rows and never historical diagnostic census", () => {
    assert.match(recipient, /collectionSource\.rows/);
    assert.match(recipient, /collectionSource\.refreshSnapshot\(\)/);
    assert.match(host,/collectionSource: KillBackend\.KillStore/);
    assert.doesNotMatch(recipient,/appControlWindow\.(taskRows|refreshTaskManager)/);
    assert.match(recipient, /row\._taskRecord === true/);
    assert.match(recipient, /Number\(row\.startTicks\) === selectedStartTicks/);
    assert.match(recipient, /String\(row\.comm \|\| ""\) === selectedComm/);
    for (const forbidden of ["CpuPlusDiagnostics", "CpuPlusProcessPane",
                             "Quickshell.execDetached", "ProcessTelemetry {",
                             "ProcessControl {", "ProcessLimits {", "TaskSafety {"])
        assert.ok(!recipient.includes(forbidden), "unexpected extra owner: " + forbidden);
});

test("all mutation requests use shared action gateway and explicit confirmation", () => {
    assert.match(recipient, /collectionSource\.actionGate/);
    assert.doesNotMatch(recipient, /appControlWindow\.hubProcessActionGate/);
    assert.match(recipient, /gate\.exactRow\(selectedPid, selectedStartTicks, selectedComm\)/);
    assert.match(recipient, /gate\.prepare\(/);
    assert.match(recipient, /workspace\.gate\.confirm\(\)/);
    assert.match(recipient, /gate\.cancel\(\)/);
    assert.match(recipient, /gate\.toggleOneShotUnlock\(/);
    assert.match(recipient, /ownedPendingRef && gate\.pending === ownedPendingRef/);
    assert.match(recipient, /workspace\.gate\.pending !== workspace\.ownedPendingRef/);
    assert.match(recipient, /function setLimitPercent\(percent\)[\s\S]*?workspace\.stagedLimitPercent/);
    assert.match(recipient, /Preview only\. Existing actuator review requires APPLY then CONFIRM/);
    for (const backendMethod of [".sendSignal(", ".sendSignalMany(", ".restart(",
                                 ".setLimitPercent(currentTask", ".setLimitMiB(currentTask"])
        assert.equal(recipient.includes(backendMethod), false,
                     "unapproved process mutation: " + backendMethod);
});

test("shared gate verifies process birth identity on commit, not only UI selection", () => {
    assert.match(gate, /function exactRow\(pid, startTicks, name\)/);
    assert.match(gate, /row\.startTicks === startTicks/);
    assert.match(gate, /function confirm\(\)/);
    assert.match(gate, /identityProbe\.exec\(/);
    assert.match(gate, /print\('MATCH' if actual==comm and int\(fields\[19\]\)==born else 'STALE'\)/);
    assert.match(gate, /PROCESS IDENTITY NOT VERIFIED \/\/ NO ACTION/);
});

test("recipient mounts actual donor Hunter controls, all filter rails, search and scrollbars", () => {
    assert.match(recipient, /HunterControls\s*\{[\s\S]*?controller: workspace/);
    assert.match(recipient, /id: processSearch/);
    assert.match(recipient, /\[row\.comm,row\.args,row\.user,row\.pid,row\.ppid,row\.state\]/);
    for(const key of ["hunterMetricCombined","hunterMetricCpu","hunterMetricMemory","hunterMetricIo","hunterMetricAge",
        "hunterVisibilityTargets","hunterVisibilityProtected","hunterVisibilityAll"])
        assert.ok(recipient.includes(key));
    assert.match(recipient,/model: liveTargetModel/);
    assert.match(recipient,/ScriptModel\s*\{[\s\S]*?objectProp: "id"/);
    assert.match(recipient,/modelBlank=true;[\s\S]*?modelBlank=false;/);
    assert.match(recipient,/acceptedButtons: Qt.NoButton[\s\S]*?targets.indexAt/);
    assert.match(recipient,/if \(sameTarget\(row\)\) return true/);
    for(const name of ["cpuPlusKillTargetScroll","cpuPlusKillInstrumentViewport","cpuPlusQuickControlFooter"])
        assert.ok(recipient.includes(name));
    assert.match(recipient,/function killAllEligibleTasks\(\) \{ return bulkCandidates\("kill-all"\); \}/);
    assert.match(recipient,/collectionSource\.prepareCpuBulkReview\(kind,hunterMetricMode,hunterVisibilityMode\)/);
    assert.match(recipient,/collectionSource\.confirmCpuBulkReview\(bulkReview\)/);
    assert.match(recipient,/objectName: "cpuPlusBulkReview"/);
    const owner=read("widgets/AppControlW.qml");
    const bulkStore=read("services/kill/KillStore.qml");
    assert.match(bulkStore,/cpuBulkReview !== review/);
    assert.match(bulkStore,/hunterOperation\.start\(review\.kind, review\.targets, true\)/);
    assert.match(bulkStore,/hunterHogCandidates\(metric\)/);
    assert.match(bulkStore,/onCpuVisibleChanged:\s*\{\s*if \(!cpuVisible\) cancelCpuBulkReview\(cpuBulkReview\)/);
    assert.match(owner,/readonly property var cpuBulkReview: KillBackend\.KillStore\.cpuBulkReview/);
    assert.match(bulkStore,/captureCpuBulkReview\(kind, metric, visibility, captures\)/);
    assert.match(bulkStore,/if \(!releaseCpuBulkReview\(review\)\) return false;\s*hunterOperation\.start/);
});

test("recipient restores existing owner graph and favorite semantics", () => {
    const row = read("widgets/appcontrol/ProcessTargetRow.qml");
    assert.match(recipient,/readonly property var detailGraph: graphController/);
    assert.match(recipient,/details\.cpuCanvas\.requestPaint\(true\)/);
    assert.match(recipient,/details\.combiScoreCanvas\.requestPaint\(true\)/);
    assert.doesNotMatch(recipient,/detailGraph\.appendSelectedTaskHunterHistories/);
    assert.match(host,/graphSource: KillBackend\.KillStore\.cpuGraphState/);
    assert.match(recipient,/readonly property var history: graphSource/);
    assert.match(host,/graphController: KillBackend\.KillStore\.cpuGraphController/);
    assert.match(host,/graphSession: KillBackend\.KillStore\.cpuDetailSession/);
    assert.doesNotMatch(recipient,/appControlWindow\.taskMini(?:CpuHistories|HunterMetricHistories|DisplayRevision)/);
    assert.match(row,/width: 82/);
    assert.match(row,/mini\.combi/);
    assert.match(row,/root\.controller\.miniHistory/);
    assert.match(row,/root\.favorite \? "✦" : "✧"/);
    assert.match(recipient,/FavoriteIdentity\.taskKey\(row\)/);
    assert.match(recipient,/FavoritesService\.isFavoriteKey\(taskFavoriteKey\(row\)\)/);
    assert.match(recipient,/FavoritesService\.toggleFavoriteKey\(key\)/);
    assert.match(recipient,/FavoritesService\.isTaskMetricKey\(FavoriteIdentity\.taskMetricKey\(entry, metricId\)\)/);
    assert.match(recipient,/FavoritesService\.toggleTaskMetricKey\(key\)/);
    assert.doesNotMatch(recipient,/appControlWindow\.(?:favoriteStore|taskFavoriteKey|isTaskMetricFavorite|toggleTaskMetricFavorite)|ownerFavoriteStore/);
    assert.doesNotMatch(recipient,/new ProcessTelemetry/);
});


// K5b: execute actual workspace adapters against the shared identity and
// Favorites service functions; no donor widget or persistence is required.
test("K5b: direct favorite adapters retain key formats and toggle semantics", () => {
    const identitySource=read("services/favorites/FavoritesAppControlIdentityPolicy.js").replace(/^\.pragma library\s*/,"");
    const identity=new Function(identitySource+"\nreturn {taskKey,taskMetricKey};")();
    const service=read("services/favorites/FavoritesService.qml");
    const start=service.indexOf("    function keyString(");
    const end=service.indexOf("    // Preferred detail actions",start);
    assert.ok(start>=0 && end>start);
    const saved={favoriteKeys:["app|existing"],favoriteMonitorBoxKeys:[],favoriteTaskMetricKeys:[]};
    const api=new Function("store",service.slice(start,end)+"\nreturn {isFavoriteKey,toggleFavoriteKey,isTaskMetricKey,toggleTaskMetricKey};")(saved);
    const a=recipient.indexOf("    function taskFavoriteKey(");
    const b=recipient.indexOf("    readonly property var miniGeometry:",a);
    const c=recipient.indexOf("        function isTaskMetricFavorite(");
    const d=recipient.indexOf("\n    }\n\n    Component {",c);
    assert.ok(a>=0 && b>a && c>b && d>c);
    const workspace={active:true};
    const adapters=new Function("FavoriteIdentity","FavoritesService","workspace","active",recipient.slice(a,b)+recipient.slice(c,d)+"\nreturn {taskFavoriteKey,isTaskFavorite,toggleTaskFavorite,isTaskMetricFavorite,toggleTaskMetricFavorite};")(identity,api,workspace,true);
    const row={comm:"With Space",pid:123};
    assert.equal(adapters.taskFavoriteKey(row),"task|with%20space");
    adapters.toggleTaskFavorite(row);
    assert.deepEqual(saved.favoriteKeys,["task|with%20space","app|existing"]);
    assert.equal(adapters.isTaskFavorite({comm:"WITH SPACE",pid:456}),true);
    adapters.toggleTaskFavorite(row);
    assert.deepEqual(saved.favoriteKeys,["app|existing"]);
    adapters.toggleTaskMetricFavorite(row," CPU ");
    assert.deepEqual(saved.favoriteTaskMetricKeys,["taskmetric|with%20space|cpu"]);
    assert.equal(adapters.isTaskMetricFavorite(row,"cpu"),true);
    workspace.active=false;
    adapters.toggleTaskMetricFavorite(row,"cpu");
    assert.equal(adapters.isTaskMetricFavorite(row,"cpu"),true);
    workspace.active=true;
    adapters.toggleTaskMetricFavorite(row,"cpu");
    adapters.toggleTaskMetricFavorite(null,"cpu");
    assert.deepEqual(saved.favoriteTaskMetricKeys,[]);
});

test("master and per-action lock state is rendered with donor glyphs and exact-owner gating", () => {
    const lock = read("widgets/appcontrol/ProcessSafetyLock.qml");
    assert.match(lock,/root\.stickyUnlocked \? "" : root\.unlocked \? "☍" : ""/);
    assert.match(lock,/acceptedButtons: Qt.LeftButton \| Qt.RightButton/);
    assert.doesNotMatch(lock,/enabled: root.isProtected && !root.masterUnlocked/);
    assert.match(lock,/enabled: root.isProtected\s+&& root.controller.canChangeLock/);
    assert.match(recipient,/objectName: "cpuPlusProcessMasterLock"/);
    assert.match(recipient,/function canChangeLock\(row\)[\s\S]*?exactTargetAvailable[\s\S]*?!gate\.pending && !gate\.busy/);
    assert.match(recipient,/collectionSource\.lockModeForIdentity/);
    assert.match(recipient,/collectionSource\.toggleLockForIdentity/);
    assert.doesNotMatch(recipient,/appControlWindow\.(taskDanger(?:Action(?:Local)?)?UnlockMode|toggleTaskDanger(?:Action)?StickyUnlock|toggleTaskDangerActionUnlock)/);
    assert.match(donorView,/property Item actionTarget: null/);
    assert.match(recipient,/actionTarget: leftActions/);
    assert.equal((donorView.match(/parent: taskManagerBody\.actionTarget \|\| taskManagerBody/g)||[]).length,1);
    assert.match(donorView,/property alias actionSection: actionColumn/);
});

test("PROCESS visibility increases only the existing owner sampling cadence", () => {
    const owner=read("widgets/AppControlW.qml");
    const shell=read("shell.qml");
    assert.doesNotMatch(shell+owner,/cpuPlusProcessVisible/);
    assert.match(owner,/property: "donorGraphVisible"\s*value: appControlWindow\.menuOpen/);
    assert.match(owner,/function taskMiniProbeNeeded\(\) \{\s*return KillBackend\.KillStore\.miniProbeNeeded/);
    assert.match(shell,/property: "cpuVisible"\s*value: cpuPlusWindow\.menuOpen && cpuPlusWindow\.selectedModeIndex === 1/);
    assert.match(shell,/KillBackend\.KillStore\.collectionEnabled = true/);
    assert.doesNotMatch(owner,/id: taskManagerRefreshTimer|id: taskMiniDisplayTimer|id: taskRefreshAfterKillTimer/);
    const store=read("services/kill/KillStore.qml");
    assert.match(store,/readonly property bool graphVisible: cpuVisible \|\| donorGraphVisible/);
    assert.match(store,/readonly property bool hasTaskFavorites: FavoriteIdentity\.hasTaskFavorites\(/);
    assert.doesNotMatch(owner,/property: "hasTaskFavorites"/);
    assert.match(store,/id: taskManagerRefreshTimer[\s\S]*?interval: root.snapshotInterval[\s\S]*?running: root.collectionEnabled/);
    assert.match(store,/id: taskMiniDisplayTimer[\s\S]*?interval: 1200[\s\S]*?running: root.collectionEnabled && root.miniProbeNeeded/);
    assert.match(store,/id: afterAction[\s\S]*?interval: 320/);
    assert.match(store,/^pragma Singleton/m);
    assert.equal((store.match(/^\s*ProcessTelemetry\s*\{/gm)||[]).length,2);
    assert.match(store,/ProcessTelemetry\s*\{\s*id: cpuDetailSampler\s*detailOnly: true/);
    assert.doesNotMatch(owner,/^\s*ProcessTelemetry\s*\{/m);
    assert.match(owner,/readonly property var processTelemetry: KillBackend\.KillStore\.telemetry/);
    assert.match(owner,/readonly property var taskRows: KillBackend\.KillStore\.rows/);
    assert.match(owner,/Connections\s*\{\s*target: KillBackend\.KillStore/);
    assert.match(store,/onSnapshotReady: function\(rows\) \{ root.publishSnapshot\(rows\); \}/);
    assert.match(store,/onMiniProbeReady: function\(rows\) \{ root.publishMiniSamples\(rows\); \}/);
    assert.doesNotMatch(owner,/KillBackend\.KillStore\.publishSnapshot\(|function applyTaskMiniProbeRows\(/);
    assert.match(read("services/kill/qmldir"),/singleton KillStore 1\.0 KillStore\.qml/);
    assert.doesNotMatch(recipient,/^\s*(Timer|ProcessTelemetry)\s*\{/m);
    assert.doesNotMatch(recipient,/appendCurrentHistory|lastDetailSampleMs/);
    const session=read("services/kill/KillDetailSession.qml");
    assert.match(session,/interval: 1000/);
    assert.match(session,/graph\.refreshDetailProbe\(currentEntry\)/);
    assert.doesNotMatch(owner,/id: taskGraphProbeTimer/);
});

test("both process hosts share the compact information document and action section", () => {
    const app=read("widgets/AppControlW.qml");
    const info=read("widgets/appcontrol/ProcessInformationPanel.qml");
    for (const host of [app,recipient]) {
        assert.match(host,/ProcessInformationButton\s*\{/);
        assert.match(host,/ProcessInformationPanel\s*\{/);
        assert.match(host,/scopeText: open && contextActive && task \?/);
        assert.match(host,/maximumHeight: Math.max\(0,/);
    }
    assert.match(info,/onTargetIdentityChanged: open = false/);
    assert.match(info,/onContextActiveChanged: if \(!contextActive\) open = false/);
    assert.match(info,/text: "PROCESS PURPOSE"[\s\S]*semanticText\("PROCESS SCOPE \/\/"[\s\S]*text: "TECHNICAL INFORMATION"[\s\S]*text: "COMMAND LINE"/);
    assert.match(info,/textFormat: Text.PlainText/);
    assert.match(app,/anchors.bottom: pinnedTaskActions.visible \? pinnedTaskActions.top : detailBottomBar.top/);
    assert.match(app,/actionTarget: pinnedTaskActions/);
    assert.match(donorView,/height: taskManagerBody.graphHeight/);
    assert.doesNotMatch(donorView,/id: taskProcessScopeInfo/);
});

test("P4b: three real size steps and only scope/command bodies scroll", () => {
    const info=read("widgets/appcontrol/ProcessInformationPanel.qml");
    const button=read("widgets/appcontrol/ProcessInformationButton.qml");
    const app=read("widgets/AppControlW.qml");
    assert.match(button,/hoverForegroundColor: Colors.orange/);
    assert.equal((info.match(/^\s*Flickable\s*\{/gm)||[]).length,2);
    assert.equal((info.match(/^\s*ResizeButton\s*\{/gm)||[]).length,2);
    assert.match(info,/sizeLevel === 2 \? availableHeight/);
    assert.match(info,/availableHeight \* 0\.78/);
    assert.match(info,/availableHeight \* 0\.55/);
    assert.match(info,/Math\.max\(0, Math\.min\(2, sizeLevel \+ delta\)\)/);
    assert.match(info,/scopeMinimum \* baseFraction/);
    assert.match(info,/argumentsMinimum \* baseFraction/);
    assert.match(info,/geometryHost: scopeFrame/);
    assert.match(info,/geometryHost: argumentsFrame/);
    assert.doesNotMatch(info,/processInformationScroll"/);
    assert.match(info,/text: root.task \? String\(root.task.args \|\| ""\) : ""\s+textFormat: Text.PlainText/);
    assert.match(app,/maximumHeight: Math.max\(0, detailBottomBar.y - fullTop\)/);
    assert.match(recipient,/maximumHeight: Math.max\(0, instrumentBay.height - fullTop - 6\)/);
});

test("P4c: expansion crosses state header and moves controls without duplicating actions", () => {
    const info=read("widgets/appcontrol/ProcessInformationPanel.qml");
    const app=read("widgets/AppControlW.qml");
    assert.match(info,/y: sizeLevel === 2 \? fullTop : sizeLevel === 1 \? expandedTop : compactTop/);
    assert.match(info,/maximumHeight - Math.max\(0, y - fullTop\)/);
    assert.match(app,/expandedTop: detailStaticHeader.y \+ runningStateSection.y/);
    assert.match(recipient,/expandedTop: processStateHeader.y/);
    assert.match(recipient,/fullTop: 6/);
    assert.match(recipient,/contextActive: workspace.active && !!workspace.currentTask\s+&& !workspace.locallyPending && !workspace.hasBulkReview && !workspace.bulkOperation/);
    const left=recipient.slice(recipient.indexOf("id: instrumentBay"),recipient.indexOf("id: targetBay"));
    const right=recipient.slice(recipient.indexOf("id: resourceBay"));
    assert.match(left,/id: actuatorScroll/);
    assert.match(left,/id: leftActions/);
    assert.doesNotMatch(left,/cpuPlusBulkConfirm|cpuPlusProcessReviewWarning/);
    assert.match(right,/cpuPlusBulkConfirm/);
    assert.match(left,/id: cpuProcessInformation/);
    assert.match(left,/id: details/);
    assert.match(left,/actionTarget: leftActions/);
    assert.doesNotMatch(right,/id: actuatorScroll|id: leftActions|TaskManagerView|ProcessInformationPanel/);
    assert.equal((recipient.match(/id: leftActions/g)||[]).length,1);
});

test("P4d: both hosts mount the same process row and mini renderer", () => {
    const app=read("widgets/AppControlW.qml");
    const row=read("widgets/appcontrol/ProcessTargetRow.qml");
    const mini=read("widgets/appcontrol/ProcessMiniGraph.qml");
    assert.match(app,/sourceComponent: ProcessTargetRow/);
    assert.match(recipient,/delegate: ProcessTargetRow/);
    assert.match(row,/ProcessMiniGraph\s*\{/);
    assert.match(mini,/historyFrame = \{values:Array.isArray\(next\)\?next.slice\(\):\[\],combi:combi\}/);
    assert.match(mini,/transform: Translate\s*\{\s*x: root.graphScrollOffset/);
    assert.match(mini,/onHistoryRevisionChanged: refreshHistory\(true\)/);
    assert.match(recipient,/id: identityContent[\s\S]*?cpuPlusProcessExactIdentity[\s\S]*?cpuPlusProcessLiveOwner[\s\S]*?ProcessInformationButton/);
    assert.match(recipient,/objectName: "cpuPlusProcessReservedBay"/);
});

test("P4e: CPU++ mounts the same three action instances in its floating identity header", () => {
    assert.match(recipient,/Item\s*\{\s*id: processIdentity/);
    assert.doesNotMatch(recipient,/text: "PROCESS \/\/ INSTRUMENTS"/);
    assert.match(recipient,/quickActionTarget: headerActions/);
    assert.match(recipient,/lockTarget: limitLockSlot/);
    assert.match(recipient,/item.parent === headerActions/);
    assert.equal((donorView.match(/parent: taskManagerBody\.(?:(?:killActionTarget|freezeActionTarget) \|\| taskManagerBody\.)?quickActionTarget \|\| actionColumn/g)||[]).length,3);
    assert.match(donorView,/parent: taskManagerBody.lockTarget \|\| taskTerminationHeaderBox/);
    assert.match(donorView,/id: taskRestartAction[\s\S]*?accentColor: taskManagerBody.headerActions \? Colors.yellow/);
    assert.match(donorView,/processController.isFrozen\(\) \? "♨" : "❆"/);
    assert.match(recipient,/ProcessInformationButton\s*\{\s*id: lockHelpButton/);
    assert.match(recipient,/id: lockHelp[\s\S]*?open: lockHelpButton.hovered && lockHelpButton.available && workspace.active[\s\S]*?Left click lock: one-shot/);
    assert.equal((recipient.match(/Left click lock: one-shot/g)||[]).length,1);
    for (const action of ["requestRestart", "toggleFreeze", "requestTerminate"])
        assert.equal((donorView.match(new RegExp("processController\\."+action+"\\(\\)","g"))||[]).length,1);
});

test("P4f: aligned safety slots and semantic information", () => {
    const info=read("widgets/appcontrol/ProcessInformationPanel.qml");
    assert.match(recipient,/id: headerLocks[\s\S]*?cpuPlusProcessMasterLock[\s\S]*?id: killSlot[\s\S]*?id: headerActions[\s\S]*?id: freezeSlot[\s\S]*?id: lockHelpButton/);
    assert.match(recipient,/killLockTarget: killLockSlot/);
    assert.match(recipient,/freezeLockTarget: freezeLockSlot/);
    assert.match(recipient,/visible: !workspace.exactTargetAvailable/);
    assert.match(donorView,/ReloadButton\s*\{\s*id: taskRestartAction/);
    assert.match(donorView,/label: taskManagerBody.headerActions \? "⟳"/);
    assert.match(info,/PID \+ START TICKS \+ NAME verify process identity/);
    assert.match(info,/case "CPU": return Colors.orange/);
    assert.match(info,/case "MEM": case "MEMORY": return Colors.magenta/);
    assert.match(info,/case "I\/O": case "FREEZE"/);
    assert.match(info,/GaussianBlur \{ anchors.fill: purposeText; source: purposeText/);
});

test("P4g: real owner grants isolate restart, kill, freeze and limit; master grants all", () => {
    const safety=read("services/system/TaskSafety.qml");
    const start=safety.indexOf("    function dangerKey(");
    const end=safety.lastIndexOf("}");
    assert.ok(start>=0&&end>start);
    const owner=new Function("let unlockedKeys={},actionUnlockedKeys={};"+safety.slice(start,end)+
        "\nreturn {dangerActionUnlocked,dangerActionLocalUnlockMode,toggleDangerActionUnlock,toggleDangerActionStickyUnlock,toggleDangerUnlock,relockDangerAction};")();
    const row={pid:3442,startTicks:967833,comm:"quickshell",user:"ci"};
    const other={...row,startTicks:967834};
    const actions=["kill","restart","freeze","limit"];
    for(const kind of actions) assert.equal(owner.dangerActionUnlocked(row,kind),false);
    for(const kind of actions) {
        owner.toggleDangerActionUnlock(row,kind);
        for(const otherKind of actions) assert.equal(owner.dangerActionUnlocked(row,otherKind),kind===otherKind);
        assert.equal(owner.dangerActionUnlocked(other,kind),false);
        owner.relockDangerAction(row,kind);
        assert.equal(owner.dangerActionUnlocked(row,kind),false);
    }
    owner.toggleDangerActionStickyUnlock(row,"restart");
    owner.relockDangerAction(row,"restart");
    assert.equal(owner.dangerActionUnlocked(row,"restart"),true);
    assert.equal(owner.dangerActionUnlocked(row,"kill"),false);
    owner.toggleDangerActionUnlock(row,"restart");
    owner.toggleDangerUnlock(row);
    for(const kind of actions) assert.equal(owner.dangerActionUnlocked(row,kind),true);
    owner.toggleDangerActionUnlock(row,"freeze");
    assert.equal(owner.dangerActionLocalUnlockMode(row,"freeze"),"once");
    owner.relockDangerAction(row,"kill");
    assert.equal(owner.dangerActionUnlocked(row,"kill"),false);
    assert.equal(owner.dangerActionUnlocked(row,"freeze"),true);
    owner.toggleDangerUnlock(row);
    owner.toggleDangerUnlock(row);
    for(const kind of actions) assert.equal(owner.dangerActionUnlocked(row,kind),false);
    owner.toggleDangerUnlock(row);
    assert.equal(owner.dangerActionUnlocked(row,"invalid"),false);
});
test("P4g: restart lock is checked and consumed at all existing authorization seams",()=>{
    const controller=read("services/system/ProcessPresentationController.qml");
    const global=read("widgets/appcontrol/GlobalTaskActionController.qml");
    const app=read("widgets/AppControlW.qml");
    const begin=gate.indexOf("    function actionLockKind(");
    const end=gate.indexOf("    function isUnlocked(",begin);
    const map=new Function(gate.slice(begin,end)+"\nreturn actionLockKind;")();
    assert.equal(map("restart"),"restart");
    assert.equal(map("end"),"kill");
    assert.equal(map("freeze"),"freeze");
    assert.equal(map("resume"),"freeze");
    assert.equal(map("limit"),"limit");
    assert.equal(map("invalid"),"");
    assert.equal((gate.match(/actionLockKind\(req.action\)/g)||[]).length,2);
    assert.match(gate,/actionLockKind\(pending.action\)/);
    assert.match(gate,/const key = actionLockKind\(action\)/);
    assert.match(controller,/function requestRestart\([\s\S]*?dangerActionUnlocked\(target, "restart"\)/);
    assert.match(global,/function executeTaskRestart\([\s\S]*?taskDangerActionUnlocked\(entry, "restart"\)[\s\S]*?relockTaskDangerAction\(entry, "restart"\)/);
    assert.match(app,/cancelKind.indexOf\("restart"\) !== -1 \? "restart"/);
    assert.match(recipient,/id: lockRail[\s\S]*?id: killLockSlot[\s\S]*?id: restartLockSlot[\s\S]*?id: freezeLockSlot[\s\S]*?id: lockHelpButton/);
    assert.match(recipient,/restartLockTarget: restartLockSlot/);
    assert.match(donorView,/item.actionKind = "restart"/);
});

test("P4h: stable instrument reserves and protected review guidance",()=>{
    assert.match(host,/name: "PROCESS", displayName: "KILL"/);
    assert.match(host,/text: modelData.displayName \|\| modelData.name/);
    assert.match(recipient,/id: instrumentTitle[\s\S]*?text: "KILL \/\/ TASK MANAGER"/);
    assert.match(recipient,/id: instrumentHeaderLine[\s\S]*?height: 2\s+color: Colors.red/);
    assert.match(recipient,/height: Math.max\(56, lockRail.reservedHeight/);
    assert.match(recipient,/reservedHeight: 3 \* 23 \+ 3 \* spacing \+ 22/);
    assert.doesNotMatch(recipient,/visible: lockRail.protectedTarget/);
    assert.match(recipient,/id: limitLockSlot[\s\S]*?height: 26\s+visible: !!workspace.currentTask/);
    assert.match(recipient,/name: "MASTER", ink: Colors.magenta/);
    assert.match(recipient,/name: "KILL", ink: Colors.red/);
    assert.match(recipient,/name: "RESTART", ink: Colors.yellow/);
    assert.match(recipient,/name: "FREEZE \/ THAW", ink: Colors.cyan/);
    assert.match(recipient,/name: "LIMIT", ink: Colors.yellow/);
    assert.match(recipient,/WARNING \/\/ PROTECTED PROCESS/);
    assert.match(recipient,/workspace.protectedProcessRisk\(workspace.currentTask\)/);
    assert.match(recipient,/NO COMMAND HAS BEEN SENT/);
    assert.match(recipient,/workspace.gate.confirm\(\)/);
});

test("KILL startup: RectangularShadow has its required QtQuick.Effects import", () => {
    assert.match(recipient, /^import QtQuick\.Effects$/m);
    assert.match(recipient, /RectangularShadow\s*\{/);
});

test("P4i: same animated writing cursor, donor search geometry and star list rail", () => {
    const app=read("widgets/AppControlW.qml");
    const cursor=read("components/AnimatedTextCursor.qml");
    assert.match(app,/AnimatedTextCursor\s*\{\s*id: searchCursorOverlay\s*input: searchInput/);
    assert.match(recipient,/AnimatedTextCursor\s*\{[\s\S]*?input: processSearch/);
    assert.match(cursor,/cursor.input.x \+ cursor.input.cursorRectangle.x - 1/);
    for (const interval of [500,420,360]) assert.match(cursor,new RegExp("interval: "+interval));
    assert.match(cursor,/text: "✍︎"/);
    assert.match(cursor,/onTextChanged\(\)/);
    assert.match(recipient,/id: searchHeader[\s\S]*?height: 70[\s\S]*?font.pixelSize: 19[\s\S]*?id: processSearch[\s\S]*?font.pixelSize: 18/);
    assert.match(recipient,/id: processSearch[\s\S]*?cursorDelegate: Item \{ width: 0; height: 0; visible: false/);
    assert.match(recipient,/objectName: "cpuPlusKillTargetScroll"[\s\S]*?handleStyle: "star"[\s\S]*?y: searchHeader.height \+ hunterControls.topSelectorHeight[\s\S]*?height: Math.max\(0, targetBay.height - y - hunterControls.bottomSelectorHeight\)/);
    assert.match(recipient,/readonly property int displayedTargetCount: filteredRows.length/);
    assert.doesNotMatch(recipient,/String\(workspace.filteredRows.length\)\+" TARGETS"/);
    assert.match(host,/selectedModeIndex === 1\s*\? "KILL \/\/ ".*displayedTargetCount/);
    assert.match(host,/cpuHeaderColor: selectedModeIndex === 1 \? Colors.red/);
    assert.match(donorView,/id: taskEndAction[\s\S]*?idleForegroundColor: taskManagerBody.headerActions \? Colors.red/);
    assert.equal((donorView.match(/contentGlowIdleOpacity: taskManagerBody.headerActions \? 0\.82 : 0/g)||[]).length,3);
    assert.match(recipient,/layer.effect: DropShadow \{ radius: 6; samples: 7; opacity: 0.60; color: lockRiskText.color/);
});

test("P4i startup: animated cursor is registered in the shared QML module", () => {
    assert.match(read("components/qmldir"), /^AnimatedTextCursor 1\.0 AnimatedTextCursor\.qml$/m);
    assert.match(read("components/AnimatedTextCursor.qml"), /required property TextInput input/);
});

test("P4j: single and captured review live on the right, with bounded body and independent footer", () => {
    const left=recipient.slice(recipient.indexOf("id: instrumentBay"),recipient.indexOf("id: targetBay"));
    const right=recipient.slice(recipient.indexOf("id: resourceBay"));
    assert.doesNotMatch(left,/cpuPlusBulkReview|cpuPlusBulkConfirm|cpuPlusProcessReviewWarning/);
    assert.match(right,/id: reviewPanel[\s\S]*?anchors.top: parent.top/);
    assert.match(right,/height: visible \? Math.min\(reviewPanel.bodyRoom, count \* 36\) : 0/);
    assert.match(right,/id: reviewFooter[\s\S]*?ActionButton \{\s*id: reviewConfirm[\s\S]*?ActionButton \{\s*id: reviewCancel/);
    assert.match(right,/model: reviewPanel.capture \? workspace.bulkReview.targets : \[\]/);
    assert.match(right,/id: capturedCount[\s\S]*?color: Colors.magenta/);
    assert.match(right,/id: capturedLabel[\s\S]*?text: "CAPTURED TARGETS"\s+color: Colors.red/);
    assert.match(right,/id: reviewCancel[\s\S]*?normalFace: true[\s\S]*?idleForegroundColor: Colors.white[\s\S]*?hoverForegroundColor: reviewPanel.reportReady \? Colors.white : Colors.black/);
    assert.match(right,/id: reviewCancel[\s\S]*?hoverFillColor: reviewPanel.reportReady \? Colors.red : Colors.yellow/);
    assert.match(right,/workspace.gate.confirm\(\)/);
    assert.match(right,/workspace.confirmBulk\(\)/);
    assert.match(right,/workspace.cancelOwned\(\)/);
    assert.match(right,/workspace.cancelBulk\(\)/);
    const prep=recipient.slice(recipient.indexOf("function requestBulk("),recipient.indexOf("function requestKillAllEligibleTasks("));
    const single=recipient.slice(recipient.indexOf("function prepareAction("),recipient.indexOf("function lockMode("));
    assert.doesNotMatch(prep+single,/actuatorScroll.contentY/);
});
test("P4j: presentation classification and escaped rich-text identity preserve semantic colors", () => {
    const start=recipient.indexOf("    function reviewProcessColor(");
    const stop=recipient.indexOf("    function protectedProcessRisk(",start);
    assert.ok(start>=0&&stop>start);
    const Colors={omnitrix:"#00F782",cyan:"#55CFCA",green:"#9ECE6A",white:"#DCF3FA"};
    const policy=new Function("Colors",recipient.slice(start,stop)+"\nreturn {reviewProcessColor, reviewTargetText};")(Colors);
    for(const name of ["sway","kitty","quickshell","zsh","tmux"]) assert.equal(policy.reviewProcessColor(name),Colors.omnitrix);
    for(const name of ["brave","firefox","code-oss","vesktop"]) assert.equal(policy.reviewProcessColor(name),Colors.cyan);
    for(const name of ["systemd","pipewire","dbus-daemon","unknown-worker"]) assert.equal(policy.reviewProcessColor(name),Colors.green);
    const text=policy.reviewTargetText({name:"dbus-daemon<&",pid:314},Colors.green);
    assert.ok(text.includes('<font color="#DCF3FA">-</font>'));
    assert.ok(text.includes('&lt;&amp;'));
    assert.ok(text.includes('<font color="#9ECE6A">314</font>'));
    assert.ok(text.includes('<font color="#DCF3FA"> [PID </font>'));
    assert.ok(!text.includes("<&"));
});

test("K2a: service owns donor graph controller and history; views consume the same store", () => {
    const owner=read("widgets/AppControlW.qml");
    const store=read("services/kill/KillStore.qml");
    const legacy=read("widgets/appcontrol/TaskGraphController.qml");
    assert.equal((store.match(/^\s*ProcessPresentationState\s*\{/gm)||[]).length,2);
    assert.equal((store.match(/^\s*TaskGraphController\s*\{/gm)||[]).length,2);
    assert.match(store,/taskMiniHistoryKeepImmutable: root\.graphVisible/);
    assert.match(owner,/readonly property var processPresentationState: KillBackend\.KillStore\.graphState/);
    assert.match(owner,/readonly property var taskGraphController: KillBackend\.KillStore\.graphController/);
    assert.doesNotMatch(owner,/^\s*(ProcessPresentationState|TaskGraphController)\s*\{/m);
    assert.match(owner,/target: appControlWindow\.taskGraphController/);
    assert.match(legacy,/KillBackend\.TaskGraphController \{\}/);
    assert.doesNotMatch(legacy,/function updateMiniCpuHistories/);
    assert.doesNotMatch(recipient,/TaskGraphController\s*\{/);
    assert.match(recipient,/required property var graphSource/);
    assert.match(recipient,/Number\(graphSource\.taskMiniDisplayRevision/);
});

test("K2b: exact detail identity, one probe, shared state and donor masking", () => {
    const session=read("services/kill/KillDetailSession.qml");
    const store=read("services/kill/KillStore.qml");
    const telemetry=read("services/system/ProcessTelemetry.qml");
    assert.match(session,/cpuActive \? cpuTarget : donorActive \? donorTarget/);
    assert.match(session,/JSON.stringify\(\[pid,birth,comm\]\)/);
    assert.match(session,/graph.clearDetailHistory\(\)/);
    assert.match(session,/Number\(sample.startTicks\)!==Number\(currentEntry.startTicks\)/);
    assert.match(store,/onDetailProbeReady: function\(sample\) \{ selectedDetail.accept\(sample\); \}/);
    assert.match(telemetry,/startTicks !== Number\(request.startTicks\)/);
    assert.match(donorView,/property bool graphDataAvailable: true/);
    assert.match(recipient,/graphDataAvailable: workspace.graphSession.matches\(workspace.currentTask\)/);
    assert.doesNotMatch(recipient,/ProcessPresentationState\s*\{|appendCurrentHistory|telemetry: null/);
});

test("detail parser refuses wrong birth and generation before advancing counters", () => {
    const source=read("services/system/ProcessTelemetry.qml");
    const begin=source.indexOf("    function parseDetailProbe(output) {");
    const end=source.indexOf("\n    Process {",begin);
    assert.ok(begin>=0 && end>begin);
    const make=new Function("Date",`
        let detailProbeGeneration=2, detailProbeActiveGeneration=2;
        let detailProbePid=4321, detailProbeLastTicks=-1, detailProbeLastIoBytes=-1, detailProbeLastMs=0;
        let detailProbeRequest={pid:4321,startTicks:98765,fallbackCpu:11,fallbackIoRate:4};
        `+source.slice(begin,end)+`
        return {parseDetailProbe, stale:()=>detailProbeActiveGeneration=1,
            counters:()=>[detailProbeLastTicks,detailProbeLastIoBytes,detailProbeLastMs]};
    `);
    const p=make({now:()=>1000});
    assert.equal(p.parseDetailProbe("4321 100 2048 100000 100 4 1000 98764 1000"),null);
    assert.deepEqual(p.counters(),[-1,-1,0]);
    const sample=p.parseDetailProbe("4321 100 2048 100000 100 4 1000 98765 1000");
    assert.equal(sample.startTicks,98765);
    assert.equal(sample.cpuPercent,11);
    assert.deepEqual(p.counters(),[100,1000,1000]);
    p.stale();
    assert.equal(p.parseDetailProbe("4321 200 2048 100000 100 4 2000 98765 1001"),null);
    assert.deepEqual(p.counters(),[100,1000,1000]);
});

test("K2c preserves all snapshot cadence priorities and mini request data", () => {
    const source=read("services/kill/KillStore.qml");
    const extract=(name,next)=>source.slice(source.indexOf("    function "+name+"("),source.indexOf("    function "+next+"("));
    const cadence=new Function(extract("snapshotCadence","refreshSnapshot")+"\nreturn snapshotCadence;")();
    const mini=new Function(extract("miniRequestForRows","refreshMiniProbe")+"\nreturn miniRequestForRows;")();
    for(const [args,want] of [
        [[true,true,true,true,true,0,48,true],600],
        [[false,true,true,true,true,0,48,true],900],
        [[false,false,true,false,true,0,48,true],600],
        [[false,false,false,true,true,0,48,true],600],
        [[false,false,false,false,true,0,48,true],1800],
        [[false,false,false,false,false,47,48,true],700],
        [[false,false,false,false,false,48,48,true],1400],
        [[false,false,false,false,false,48,48,false],3200]
    ]) assert.equal(cadence(...args),want);
    assert.deepEqual(mini([null,{pid:1},{pid:4321,comm:"synthetic",cpu:5,cpuInstant:31},
        {pid:4322,name:"fallback",cpu:4}]),[
        {pid:4321,comm:"synthetic",fallbackCpu:31},{pid:4322,comm:"fallback",fallbackCpu:4}]);
    assert.match(source,/property bool collectionEnabled: false/);
    assert.match(source,/if \(collectionEnabled\) sampler.refreshSnapshot\(\)/);
});

test("K2d: sampler publishes without donor and retains ordering and immutable revision semantics", () => {
    const source=read("services/kill/KillStore.qml");
    const start=source.indexOf("    function publishSnapshot(");
    const end=source.indexOf("\n    ProcessTelemetry {",start);
    assert.ok(start>=0 && end>start);
    const state={taskMiniHistoryRevision:0,taskMiniDisplayRevision:0,taskMiniPreloadSnapshots:0,taskMiniPreloadTarget:2};
    const sampler={rows:[]}, events=[];
    const graph={updateMiniCpuHistories:rows=>events.push("cpu"),updateMiniHunterMetricHistories:rows=>events.push("hunter")};
    const make=new Function("histories","sampler","graph","events",`
        let snapshotTraceEnabled=true, snapshotTraceSequence=0, miniTraceEnabled=true, miniProbeNeeded=false;
        const snapshotStarted=rows=>events.push("start");
        const snapshotOrdering=rows=>events.push("order");
        const snapshotStage=(stage,seq,start,count)=>events.push(stage);
        const snapshotPublished=(rows,seq)=>events.push("published");
        const miniStage=(stage,start)=>events.push(stage);
        `+source.slice(start,end)+`
        return {publishSnapshot,publishMiniSamples,dedicated:()=>miniProbeNeeded=true};
    `);
    const owner=make(state,sampler,graph,events);
    const rows=[{pid:4321}];
    owner.publishSnapshot(rows);
    assert.deepEqual(events,["start","cpu","cpu-history","hunter","hunter-history","history-revisions","order","task-order","task-rows","published"]);
    assert.equal(sampler.rows,rows);
    assert.equal(state.taskMiniDisplayRevision,1);
    owner.dedicated();
    events.length=0;
    owner.publishSnapshot([{pid:4322}]);
    assert.deepEqual(events,["start","order","task-order","task-rows","published"]);
    assert.equal(state.taskMiniDisplayRevision,1);
    assert.equal(state.taskMiniPreloadSnapshots,2);
    owner.publishMiniSamples([]);
    assert.equal(state.taskMiniDisplayRevision,1);
    events.length=0;
    owner.publishMiniSamples(rows);
    assert.deepEqual(events,["cpu","mini-cpu-history","hunter","mini-hunter-history","mini-history-revisions"]);
    assert.equal(state.taskMiniDisplayRevision,2);
    assert.equal(sampler.rows[0].pid,4322);
    owner.publishSnapshot(null);
    assert.equal(state.taskMiniPreloadSnapshots,2);
    assert.deepEqual(sampler.rows,[]);
});

test("K3a: one shared runtime safety, mutation primitive and limit queue", () => {
    const store=read("services/kill/KillStore.qml");
    const owner=read("widgets/AppControlW.qml");
    for(const [type,prop,id] of [
        ["TaskSafety","safety","safetyState"],
        ["ProcessControl","control","controlBackend"],
        ["ProcessLimits","limits","limitBackend"]
    ]) {
        assert.equal((store.match(new RegExp("^\\s*"+type+"\\s*\\{","gm"))||[]).length,1);
        assert.match(store,new RegExp("readonly property var "+prop+": "+id));
        assert.doesNotMatch(owner,new RegExp("^\\s*"+type+"\\s*\\{","m"));
    }
    assert.match(owner,/readonly property var taskSafety: KillBackend\.KillStore\.safety/);
    assert.match(owner,/readonly property var processControl: KillBackend\.KillStore\.control/);
    assert.match(owner,/readonly property var processLimits: KillBackend\.KillStore\.limits/);
    assert.match(store,/ProcessLimits \{\s*id: limitBackend\s*onRefreshRequested: afterAction.restart\(\)/);
    assert.match(store,/safetyOwner: root\.safety/);
    assert.match(store,/controlOwner: root\.control/);
    assert.match(store,/limitsOwner: root\.limits/);
    assert.match(store,/bulkBlocked: root\.donorActionBlocked/);
    assert.match(owner,/property: "donorActionBlocked"\s*value: appControlWindow\.destructiveConfirmOpen/);
});

test("K3b: independent guarded gateway and presentation share service custody", () => {
    const store=read("services/kill/KillStore.qml");
    const owner=read("widgets/AppControlW.qml");
    assert.equal((store.match(/^\s*AppControlHubActionGate\s*\{/gm)||[]).length,1);
    assert.equal((store.match(/^\s*ProcessPresentationController\s*\{/gm)||[]).length,1);
    assert.doesNotMatch(owner,/^\s*(AppControlHubActionGate|ProcessPresentationController)\s*\{/m);
    assert.match(owner,/readonly property var hubProcessActionGate: KillBackend\.KillStore\.actionGate/);
    assert.match(owner,/readonly property var processPresentationController: KillBackend\.KillStore\.presentation/);
    assert.match(store,/ownerRows: root\.rows/);
    assert.match(store,/presentationOwner: root\.presentation/);
    assert.match(store,/refreshOwner: root\.refreshAfterActionTimer/);
    assert.match(owner,/property: "donorActionBlocked"\s*value: appControlWindow\.destructiveConfirmOpen/);
    assert.match(store,/bulkBlocked: root\.donorActionBlocked \|\| root\.cpuBulkReview !== null\s*\|\| root\.hunterOperation\.phase !== "idle"/);
    assert.match(owner,/function onConfirmationRequested\([\s\S]*?appControlWindow.openDestructiveConfirm\(/);
    assert.match(read("widgets/appcontrol/AppControlHubActionGate.qml"),/KillBackend\.AppControlHubActionGate \{\}/);
});

test("K3c: service lock adapters reject stale, busy, bulk and unsupported requests", () => {
    const store=read("services/kill/KillStore.qml");
    const a=store.indexOf("    function lockModeForIdentity(");
    const toggleStart=store.indexOf("    function toggleLockForIdentity(",a);
    const close=store.indexOf("\n    }",toggleStart);
    const b=close+"\n    }".length;
    assert.ok(a>=0 && toggleStart>a && close>toggleStart);
    const row={pid:4321,startTicks:98765,comm:"sway"};
    const calls=[];
    const actionGate={
        pending:null,busy:false,bulkBlocked:false,
        exactRow:(pid,birth,name)=>pid===row.pid && birth===row.startTicks && name===row.comm ? row:null,
        toggleOneShotUnlock:()=>{calls.push("master-once");return true;}
    };
    const safety={
        requiresDangerUnlock:()=>true,
        dangerUnlockMode:()=>"sticky",
        dangerActionLocalUnlockMode:()=>"once",
        dangerActionUnlockMode:()=>"sticky",
        toggleDangerStickyUnlock:r=>calls.push(["master-sticky",r]),
        toggleDangerActionStickyUnlock:(r,a)=>calls.push(["action-sticky",r,a]),
        toggleDangerActionUnlock:(r,a)=>calls.push(["action-once",r,a])
    };
    const {lockModeForIdentity:mode,toggleLockForIdentity:toggle}
        =new Function("actionGate","safety",store.slice(a,b)
            +"\nreturn {lockModeForIdentity,toggleLockForIdentity};")(actionGate,safety);
    const args=[row.pid,row.startTicks,row.comm];
    assert.equal(mode(...args,"",false),"sticky");
    assert.equal(mode(...args,"freeze",true),"once");
    assert.equal(mode(...args,"freeze",false),"sticky");
    assert.equal(mode(row.pid,row.startTicks+1,row.comm,"freeze",false),"");
    assert.equal(toggle(row.pid,row.startTicks+1,row.comm,"freeze",true),false);
    assert.equal(toggle(...args,"invalid",true),false);
    assert.equal(toggle(...args,"freeze",null),false);
    for(const flag of ["pending","busy","bulkBlocked"]) {
        actionGate[flag]=true;
        assert.equal(toggle(...args,"freeze",true),false);
        actionGate[flag]=false;
    }
    safety.requiresDangerUnlock=()=>false;
    assert.equal(toggle(...args,"freeze",true),false);
    safety.requiresDangerUnlock=()=>true;
    assert.deepEqual(calls,[]);
    assert.equal(toggle(...args,"",false),true);
    assert.equal(toggle(...args,"",true),true);
    assert.equal(toggle(...args,"restart",true),true);
    assert.equal(toggle(...args,"limit",false),true);
    assert.deepEqual(calls,["master-once",["master-sticky",row],["action-sticky",row,"restart"],["action-once",row,"limit"]]);
});

test("K3c.2a: shared bulk review is immutable and consumed only by exact reference", () => {
    const store=read("services/kill/KillStore.qml");
    const a=store.indexOf("    function captureCpuBulkReview(");
    const b=store.indexOf("    function snapshotCadence(",a);
    assert.ok(a>=0 && b>a);
    const gate={pending:null,busy:false,bulkBlocked:false};
    const api=new Function("actionGate","let cpuBulkReview=null;"+store.slice(a,b)
        +"\nreturn {captureCpuBulkReview,releaseCpuBulkReview,current:()=>cpuBulkReview};")(gate);
    const make=()=>({pid:4321,startTicks:98765,name:"synthetic",identity:"synthetic"});
    for(const flag of ["pending","busy","bulkBlocked"]) {
        gate[flag]=true;
        assert.equal(api.captureCpuBulkReview("kill-all",0,0,[make()]),null);
        gate[flag]=false;
    }
    assert.equal(api.captureCpuBulkReview("kill-all",0,0,[]),null);
    assert.equal(api.captureCpuBulkReview("kill-all",0,0,[make(),make()]),null);
    const source=[make()];
    const review=api.captureCpuBulkReview("kill-all",0,0,source);
    assert.ok(Object.isFrozen(review) && Object.isFrozen(review.targets) && Object.isFrozen(review.targets[0]));
    source.push({pid:4322});
    assert.equal(review.targets.length,1);
    assert.equal(api.current(),review);
    assert.equal(api.captureCpuBulkReview("kill-mice",0,0,[make()]),null);
    assert.equal(api.releaseCpuBulkReview({...review}),false);
    assert.equal(api.releaseCpuBulkReview(review),true);
    assert.equal(api.releaseCpuBulkReview(review),false);
    assert.equal(api.current(),null);
});

test("K3c.2b-2: one service-owned Hunter lifecycle and executor route results without donor relays", () => {
    const store=read("services/kill/KillStore.qml");
    const owner=read("widgets/AppControlW.qml");
    const controller=read("services/kill/HunterOperationController.qml");
    assert.equal((store.match(/^\s*HunterExecutor\s*\{/gm)||[]).length,1);
    assert.equal((store.match(/^\s*HunterOperationController\s*\{/gm)||[]).length,1);
    assert.match(store,/readonly property var hunterExecutor: hunterExecution/);
    assert.match(store,/readonly property var hunterOperation: hunterController/);
    assert.doesNotMatch(owner,/^\s*(HunterExecutor|HunterOperationController)\s*\{/m);
    assert.match(owner,/readonly property var hunterExecutor: KillBackend\.KillStore\.hunterExecutor/);
    assert.match(owner,/readonly property var hunterOperationController: KillBackend\.KillStore\.hunterOperation/);
    assert.match(store,/HunterOperationController\s*\{\s*id: hunterController[\s\S]*?executor: hunterExecution/);
    assert.match(store,/onResultReady: function\(result\) \{ hunterController\.applyResult\(result\); \}/);
    assert.match(store,/onFinished: hunterController\.finish\(\)/);
    assert.match(store,/onErrorRaised: function\(message\)/);
    assert.match(owner,/property: "donorHunterPresentationAvailable"\s*value: true/);
    assert.match(store,/legacyPresentationAvailable: root\.donorHunterPresentationAvailable/);
    assert.doesNotMatch(controller,/\bhost\b/);
    assert.match(store,/readonly property var favoriteStore: FavoritesStore/);
    assert.match(store,/favoriteStoreObject: root\.favoriteStore/);
    assert.doesNotMatch(owner,/property: "donorHunterFavorites"/);
    assert.match(controller,/function start\([^\n]+\)\s*\{\s*if \(!policyReady \|\| \(cpuRecipient !== true && !legacyPresentationAvailable\)\) return;/);
    assert.match(controller,/if \(!policyReady\) \{ stopRemaining\(\); return; \}/);
    assert.match(read("widgets/appcontrol/HunterOperationController.qml"),/KillBackend\.HunterOperationController \{\}/);
    assert.doesNotMatch(owner,/property alias hunterOperation/);
});

test("K4a: donor and service share original bulk eligibility policy", () => {
    const store=read("services/kill/KillStore.qml");
    const a=store.indexOf("    function taskEligibleForKillAll(");
    const b=store.indexOf("    function snapshotCadence(",a);
    assert.ok(a>=0 && b>a);
    const rows=[{_taskRecord:true,pid:4321,user:"synthetic",state:"S"},
                {_taskRecord:true,pid:4322,user:"other",state:"S"},
                {_taskRecord:true,pid:4323,user:"synthetic",state:"Z"},
                {_taskRecord:true,pid:4324,user:"synthetic",state:"S",protected:true},
                {_taskRecord:true,pid:1,user:"synthetic",state:"S"},
                {pid:4325,user:"synthetic",state:"S"}];
    const safety={protectedFromKillAll:row=>!!row.protected};
    const api=new Function("Quickshell","safety","rows",store.slice(a,b)
        +"\nreturn {taskEligibleForKillAll,killAllEligibleTasks};")({env:()=>"synthetic"},safety,rows);
    assert.deepEqual(rows.map(api.taskEligibleForKillAll),[true,false,false,false,false,false]);
    assert.deepEqual(api.killAllEligibleTasks(),[rows[0]]);
    assert.equal(api.taskEligibleForKillAll(null),false);
    const owner=read("widgets/AppControlW.qml");
    assert.match(owner,/return KillBackend\.KillStore\.taskEligibleForKillAll\(entry\)/);
    assert.match(owner,/return KillBackend\.KillStore\.killAllEligibleTasks\(\)/);
});

test("K4b: Hunter uses canonical process identity and one Favorites singleton", () => {
    const store=read("services/kill/KillStore.qml");
    const controller=read("services/kill/HunterOperationController.qml");
    const owner=read("widgets/AppControlW.qml");
    const js=read("services/favorites/FavoritesAppControlIdentityPolicy.js");
    const policy=new Function(js.replace(/^\.pragma library\s*/,"")+"\nreturn {taskIdentity,taskKey};")();
    assert.match(store,/import qs\.services\.favorites/);
    assert.match(store,/readonly property var favoriteStore: FavoritesStore/);
    assert.match(owner,/readonly property var favoriteStore: FavoritesStore/);
    assert.match(store,/favoriteStoreObject: root\.favoriteStore/);
    assert.doesNotMatch(store+owner,/donorHunterFavorites/);
    assert.match(controller,/identity: FavoriteIdentity\.taskIdentity\(entry\)/);
    assert.match(controller,/FavoriteIdentity\.taskIdentity\(row\) === target\.identity/);
    assert.doesNotMatch(controller,/host\.taskPersistentIdentity/);
    const a=store.indexOf("    function taskPersistentIdentity(");
    const b=store.indexOf("    // Preserve the donor",a);
    assert.ok(a>=0 && b>a);
    const favorites={favoriteKeys:["task|brave","task|with%20space"]};
    const api=new Function("FavoriteIdentity","favoriteStore",store.slice(a,b)
        +"\nreturn {taskPersistentIdentity,isTaskFavorite};")(policy,favorites);
    assert.equal(api.taskPersistentIdentity({comm:" Brave "}),"brave");
    assert.equal(api.isTaskFavorite({comm:"BRAVE",pid:22}),true);
    assert.equal(api.isTaskFavorite({comm:"BRAVE",pid:99}),true);
    assert.equal(api.isTaskFavorite({comm:"With Space"}),true);
    assert.equal(api.isTaskFavorite({args:"/usr/bin/brave --x"}),true);
    assert.equal(api.isTaskFavorite({comm:"other"}),false);
    assert.equal(api.isTaskFavorite({}),false);
    favorites.favoriteKeys=[];
    assert.equal(api.isTaskFavorite({comm:"brave"}),false);
    favorites.favoriteKeys=null;
    assert.equal(api.isTaskFavorite({comm:"brave"}),true);
});

test("K4c: shared HOG and MICE rules retain thresholds and refuse unknown window inventory", () => {
    const store=read("services/kill/KillStore.qml");
    const owner=read("widgets/AppControlW.qml");
    const a=store.indexOf("    function hunterTaskActive(");
    const b=store.indexOf("    // Read the original Favorites membership;",a);
    assert.ok(a>=0 && b>a);
    const rows=[];
    const presentation={metricCombined:0,metricCpu:1,metricMemory:2,metricIo:3,metricAge:4,
        taskPeak:e=>e.peak,taskAverage:e=>e.avg,taskMemoryMiB:e=>e.rss,taskIoRate:e=>e.io,
        elapsedSeconds:v=>Number(v),taskMetricScore:(e,m)=>m===2?e.rss:e.peak};
    const root={rows};
    const api=new Function("root","hunterPresentation","taskEligibleForKillAll","isTaskFavorite",
        "let hunterVisibleWindows=null;\n"+store.slice(a,b)
        +"\nreturn {hunterHogCandidates,hunterMouseCandidates,hunterMouseProtectedReason,windows:v=>hunterVisibleWindows=v};")
        (root,presentation,e=>!!e._taskRecord&&!e.protected,e=>!!e.favorite);
    const row=(pid,extra={})=>({_taskRecord:true,pid,ppid:9000,comm:"synthetic-leaf",tty:"?",state:"S",
        elapsed:"3000",cpu:.05,mem:.1,peak:.1,avg:.04,rss:12,io:0,...extra});
    const first=row(4001), favorite=row(4002,{favorite:true}), protectedRow=row(4003,{protected:true});
    const visible=row(4004), interactive=row(4005,{tty:"pts/1"}), orphan=row(4006,{ppid:1});
    const parent=row(4007), child=row(4008,{ppid:4007,elapsed:"10"});
    const helper=row(4009,{comm:"brave-helper"}), frozen=row(4010,{state:"T"});
    rows.push(first,favorite,protectedRow,visible,interactive,orphan,parent,child,helper,frozen);
    assert.deepEqual(api.hunterMouseCandidates(),[]);
    assert.equal(api.hunterMouseProtectedReason(first),"WINDOW INVENTORY UNAVAILABLE");
    api.windows([{pid:visible.pid}]);
    assert.deepEqual(api.hunterMouseCandidates(),[first]);
    assert.equal(api.hunterMouseProtectedReason(favorite),"FAVORITE");
    assert.equal(api.hunterMouseProtectedReason(protectedRow),"SESSION/PROTECTED");
    assert.equal(api.hunterMouseProtectedReason(visible),"ACTIVE APP TREE");
    assert.equal(api.hunterMouseProtectedReason(interactive),"INTERACTIVE/TTY TREE");
    assert.equal(api.hunterMouseProtectedReason(orphan),"USER SERVICE/ORPHAN");
    assert.equal(api.hunterMouseProtectedReason(parent),"PROCESS TREE");
    assert.equal(api.hunterMouseProtectedReason(helper),"IMPORTANT HELPER");
    assert.equal(api.hunterMouseProtectedReason(frozen),"FROZEN");
    const top=row(5001,{peak:30}), above=row(5002,{peak:15}), below=row(5003,{peak:14}),
        excluded=row(5004,{peak:80,favorite:true}), critical=row(5005,{peak:90,protected:true});
    rows.splice(0,rows.length,top,above,below,excluded,critical);
    assert.deepEqual(api.hunterHogCandidates(1),[top,above]);
    assert.match(owner,/return KillBackend\.KillStore\.hunterHogCandidates\(/);
    assert.match(owner,/return KillBackend\.KillStore\.hunterMouseCandidates\(\)/);
    assert.match(store,/readonly property var hunterVisibleWindows: compositor\.settled \? compositor\.windows : null/);
});

test("K4d: direct service admission consumes only the reviewed targets and preserves exclusion", () => {
    const store=read("services/kill/KillStore.qml");
    const recipient=read("widgets/cpuplus/CpuPlusKillWorkspace.qml");
    const a=store.indexOf("    function cpuBulkCandidates(");
    const b=store.indexOf("    // One immutable recipient review.",a);
    const c=store.indexOf("    function captureCpuBulkReview(");
    const d=store.indexOf("    // K4c:",c);
    assert.ok(a>=0 && b>a && c>b && d>c);
    const row={pid:4321,startTicks:98765,name:"synthetic",identity:"synthetic"};
    let starts=[];
    const operation={policyReady:true,phase:"idle",recipientOwned:false,
        targetsFromRows:rs=>rs.map(r=>({...r})),targetIsFavorite:r=>!!r.favorite,
        start:(kind,targets,owned)=>{starts.push({kind,targets,owned});operation.phase="running";operation.recipientOwned=owned;}};
    const gate={pending:null,busy:false,bulkBlocked:false};
    const api=new Function("hunterOperation","actionGate","rows",
        "let cpuVisible=true,donorActionBlocked=false,cpuBulkReview=null;"+
        "let hunterOperationPhase='idle',cpuBulkOperation=false;"+
        "function killAllEligibleTasks(){return rows;} function hunterHogCandidates(){return rows;} function hunterMouseCandidates(){return rows;}"+
        store.slice(a,b)+store.slice(c,d)+
        "\nreturn {prepareCpuBulkReview,confirmCpuBulkReview,cancelCpuBulkReview,acknowledgeCpuBulkReport,"+
        "visible:v=>cpuVisible=v,blocked:v=>donorActionBlocked=v,phase:v=>hunterOperationPhase=v,report:v=>cpuBulkOperation=v};")
        (operation,gate,[row]);
    api.visible(false);
    assert.equal(api.prepareCpuBulkReview("kill-all",0,0),null);
    api.visible(true);
    const review=api.prepareCpuBulkReview("kill-all",0,0);
    assert.ok(review && Object.isFrozen(review.targets));
    assert.equal(api.confirmCpuBulkReview({...review}),false);
    api.blocked(true);
    assert.equal(api.confirmCpuBulkReview(review),false);
    api.blocked(false);
    gate.pending={};
    assert.equal(api.confirmCpuBulkReview(review),false);
    gate.pending=null;
    operation.policyReady=false;
    assert.equal(api.confirmCpuBulkReview(review),false);
    operation.policyReady=true;
    assert.equal(api.confirmCpuBulkReview(review),true);
    assert.equal(api.confirmCpuBulkReview(review),false);
    assert.equal(starts.length,1);
    assert.equal(starts[0].targets,review.targets);
    assert.equal(starts[0].owned,true);
    assert.doesNotMatch(recipient,/appControlWindow\.(cpuBulk|prepareCpuBulk|confirmCpuBulk|cancelCpuBulk|acknowledgeCpuBulk|hunterOperationPhase|hunterOperationKind)/);
});

test("K4e: Hunter dispatch reads the service policy and never the legacy dialog host", () => {
    const store=read("services/kill/KillStore.qml");
    const controller=read("services/kill/HunterOperationController.qml");
    assert.match(store,/policyOwner: root/);
    assert.match(controller,/policyOwner\.collectionEnabled === true/);
    assert.match(controller,/for \(const row of policyOwner\.rows\)/);
    assert.match(controller,/policyOwner\.taskEligibleForKillAll\(row\)/);
    assert.match(controller,/policyOwner\.hunterMouseProtectedReason\(row\)/);
    assert.doesNotMatch(controller,/host\.(taskRows|taskEligibleForKillAll|hunterMouseProtectedReason|taskPersistentIdentity)/);
    const begin=controller.indexOf("    function liveRow("),end=controller.indexOf("    function dispatchNext(",begin);
    const policy={rows:[{pid:4321,startTicks:999,comm:"Synthetic"}]};
    const api=new Function("policyOwner","FavoriteIdentity","let policyReady=true;"+controller.slice(begin,end)
        +"\nreturn {liveRow,ready:v=>policyReady=v};")(policy,{taskIdentity:r=>r.comm.toLowerCase()});
    const target={pid:4321,startTicks:999,name:"Synthetic",identity:"synthetic"};
    assert.equal(api.liveRow(target),policy.rows[0]);
    assert.equal(api.liveRow({...target,startTicks:998}),null);
    api.ready(false);
    assert.equal(api.liveRow(target),null);
});

test("K4f: shared Sway inventory retains tree semantics and refuses unresolved snapshots", () => {
    const store=read("services/kill/KillStore.qml");
    const owner=read("widgets/AppControlW.qml");
    const source=read("services/kill/SwayWindowInventory.qml");
    const a=source.indexOf("    function collectSwayOutputNames(");
    const b=source.indexOf("    function refresh()",a);
    assert.ok(a>=0 && b>a);
    const parse=new Function(source.slice(a,b)+"\nreturn parseSnapshot;")();
    const tree={type:"root",nodes:[{type:"output",name:"DP-1",nodes:[{type:"workspace",name:"1",nodes:[
        {type:"con",id:70,layout:"tabbed",nodes:[{type:"con",id:71,name:"A",app_id:"app",pid:4001}]}
    ],floating_nodes:[{type:"floating_con",nodes:[{type:"con",id:72,name:"B",pid:4002}]}]}]}]};
    const snapshot=parse(JSON.stringify(tree));
    assert.deepEqual(snapshot.outputs,["DP-1"]);
    assert.equal(snapshot.windows.length,2);
    assert.equal(snapshot.windows[0].tabGroupId,70);
    assert.equal(snapshot.windows[0].tabbed,true);
    assert.equal(snapshot.windows[1].floating,true);
    assert.equal(snapshot.windows[1].workspace,"1");
    assert.throws(()=>parse(""));
    assert.throws(()=>parse("{}"));
    assert.deepEqual(parse('{"type":"root","nodes":[]}').windows,[]);
    assert.equal((source.match(/swayTreeProcess\.exec\(/g)||[]).length,1);
    assert.equal((source.match(/^\s*I3IpcListener\s*\{/gm)||[]).length,1);
    assert.doesNotMatch(owner,/swayTreeProcess|function collectSwayWindows\(/);
    assert.match(owner,/readonly property var swayWindows: KillBackend\.KillStore\.windowInventory\.windows/);
    assert.match(owner,/function onSnapshotPublished\(\)/);
    assert.match(source,/settled: enabled && ready && !error && !loading && !pending/);
    assert.match(source,/!loading \|\| !exited \|\| !stdoutDone \|\| !stderrDone/);
    assert.match(store,/readonly property var hunterVisibleWindows: compositor\.settled \? compositor\.windows : null/);
});

test("K5a: Hub process projection and guarded action route use KillStore directly", () => {
    const shell=read("shell.qml");
    const store=read("services/kill/KillStore.qml");
    const gate=read("services/kill/AppControlHubActionGate.qml");
    assert.match(shell,/processActionGate: KillBackend\.KillStore\.collectionEnabled\s*\? KillBackend\.KillStore\.actionGate : null/);
    assert.match(shell,/processSnapshot: KillBackend\.KillStore\.collectionEnabled\s*\? HubProcessesPolicy\.snapshot\(\s*KillBackend\.KillStore\.rows,\s*KillBackend\.KillStore\.telemetry\.snapshotLoading,\s*KillBackend\.KillStore\.telemetry\.snapshotError\)\s*: null/);
    assert.doesNotMatch(shell,/process(?:Snapshot|ActionGate): appControlWindow/);
    assert.match(shell,/appControlAvailable: appControlWindow !== null/);
    assert.match(store,/readonly property var rows: sampler\.rows/);
    assert.match(store,/readonly property var actionGate: guardedActions/);
    assert.match(gate,/if \(busy \|\| pending \|\| bulkBlocked\)/);
    const a=shell.indexOf("            processActionGate: KillBackend.KillStore.collectionEnabled");
    const b=shell.indexOf("            // Clone only bounded display fields",a);
    const c=shell.indexOf("            processSnapshot: KillBackend.KillStore.collectionEnabled",b);
    const d=shell.indexOf("            socialActionsAvailable:",c);
    assert.ok(a>=0 && b>a && c>b && d>c);
    const gateExpr=shell.slice(a,b).split("processActionGate:")[1].trim();
    const snapExpr=shell.slice(c,d).split("processSnapshot:")[1].trim();
    const project=new Function("KillBackend","HubProcessesPolicy",
        "return {gate:"+gateExpr+",snapshot:"+snapExpr+"};");
    const row={pid:42}, guarded={tag:"existing gate"};
    const model={collectionEnabled:false,rows:[row],telemetry:{snapshotLoading:true,snapshotError:""},actionGate:guarded};
    let projected=0;
    const policy={snapshot:(rows,loading,error)=>{projected++;return {rows,loading,error};}};
    assert.deepEqual(project({KillStore:model},policy),{gate:null,snapshot:null});
    assert.equal(projected,0);
    model.collectionEnabled=true;
    const result=project({KillStore:model},policy);
    assert.equal(result.gate,guarded);
    assert.equal(result.snapshot.rows,model.rows);
    assert.equal(result.snapshot.loading,true);
    assert.equal(projected,1);
});

test("K5c: process classification and exclusion use shared safety and store state", () => {
    assert.match(recipient,/readonly property var safety: collectionSource \? collectionSource\.safety : null/);
    assert.match(recipient,/readonly property bool legacyActionBlocked: !collectionSource\s*\|\| collectionSource\.donorActionBlocked !== false/);
    assert.match(recipient,/hasBulkReview \|\| bulkOperation \|\| legacyActionBlocked/);
    assert.match(recipient,/!legacyActionBlocked && isProtected\(row\)/);
    assert.doesNotMatch(recipient,/appControlWindow\.(?:taskDangerReason|taskRequiresDangerUnlock|destructiveConfirmOpen|monitorResultIcon|resultDisplayName)/);
    const start=recipient.indexOf("    function protectedProcessRisk(");
    const end=recipient.indexOf("    function hunterMetricAccent(",start);
    assert.ok(start>=0 && end>start);
    const safety={dangerReason:row=>row.comm==="sway"?"SESSION-CRITICAL":"",
        requiresDangerUnlock:row=>row.comm==="sway"};
    const make=new Function("safety","gate",recipient.slice(start,end)+"\nreturn {protectedProcessRisk,isProtected};");
    const api=make(safety,{});
    assert.equal(api.isProtected({comm:"sway"}),true);
    assert.equal(api.isProtected({comm:"worker"}),false);
    assert.equal(api.isProtected(null),true);
    assert.equal(make(null,{}).isProtected({comm:"worker"}),true);
    assert.equal(make(safety,null).isProtected({comm:"worker"}),true);
    assert.ok(api.protectedProcessRisk({comm:"sway"}).endsWith("SESSION-CRITICAL"));
});

test("K5d: workspace mounts without an AppControl instance and shares process descriptions", () => {
    const donor=read("widgets/AppControlW.qml");
    const fixture=read("tests/cpuplus/fixtures/SharedKillRecipientNative.qml");
    const purpose=read("services/kill/ProcessPurpose.js");
    const loader=host.slice(host.indexOf("id: sharedKillWorkspaceLoader"));
    assert.doesNotMatch(recipient,/appControlWindow/);
    assert.doesNotMatch(loader,/appControlWindow/);
    assert.match(loader,/&& KillBackend\.KillStore\.collectionEnabled/);
    assert.doesNotMatch(fixture,/appControlWindow: fakeOwner/);
    assert.match(donor,/function taskSimplePurpose\(entry\) \{\s*return ProcessPurpose\.taskSimplePurpose\(entry\);/);
    assert.match(recipient,/ProcessPurpose\.taskSimplePurpose\(task\)/);
    const describe=new Function(purpose.replace(/^\.pragma library\s*/,"")+"\nreturn taskSimplePurpose;")();
    assert.equal(describe(null),"");
    assert.ok(describe({comm:"sway"}).startsWith("Sway is the Wayland window manager"));
    assert.ok(describe({comm:"BRAVE"}).startsWith("BRAVE is part of the web browser."));
    assert.ok(describe({name:"synthetic-worker"}).startsWith("synthetic-worker is one live Linux process."));
});

test("K6a: independent history visibility and favorite warm demand", () => {
    const store=read("services/kill/KillStore.qml");
    const policy=read("services/favorites/FavoritesAppControlIdentityPolicy.js").replace(/^\.pragma library\s*/,"");
    const identity=new Function(policy+"\nreturn {hasTaskFavorites};")();
    const vis=store.match(/readonly property bool graphVisible: ([^\n]+)/)[1];
    const visible=new Function("cpuVisible","donorGraphVisible","return "+vis);
    assert.deepEqual([[false,false],[true,false],[false,true],[true,true]].map(a=>visible(...a)),[false,true,true,true]);
    const a=store.indexOf("    readonly property bool hasTaskFavorites:");
    const b=store.indexOf("\n\n",a);
    const expr=store.slice(a,b).split("hasTaskFavorites:")[1].trim();
    const favoriteStore={favoriteTaskMetricKeys:[],favoriteKeys:["app|other"]};
    const demand=new Function("FavoriteIdentity","favoriteStore","root","return "+expr);
    assert.equal(demand(identity,favoriteStore,{favoriteStore}),false);
    favoriteStore.favoriteKeys.push("task|worker");
    assert.equal(demand(identity,favoriteStore,{favoriteStore}),true);
    favoriteStore.favoriteKeys=[];
    favoriteStore.favoriteTaskMetricKeys=["taskmetric|worker|cpu"];
    assert.equal(demand(identity,favoriteStore,{favoriteStore}),true);
});

test("K6c: only the initiating consumer can acknowledge its completed Hunter report", () => {
    const store=read("services/kill/KillStore.qml");
    const owner=read("widgets/AppControlW.qml");
    const a=store.indexOf("    function acknowledgeCpuBulkReport(");
    const b=store.indexOf("    // One immutable recipient review.",a);
    const op={phase:"idle",recipientOwned:false};
    const api=new Function("hunterOperation",store.slice(a,b)+"\nreturn {acknowledgeCpuBulkReport,acknowledgeDonorBulkReport};")(op);
    for(const cpu of [true,false]) {
        const correct=cpu?api.acknowledgeCpuBulkReport:api.acknowledgeDonorBulkReport;
        const wrong=cpu?api.acknowledgeDonorBulkReport:api.acknowledgeCpuBulkReport;
        for(const phase of ["idle","running","report"]) {
            Object.assign(op,{phase,recipientOwned:cpu,kind:"kill-all",targets:[1],results:[2],completed:1,total:1});
            assert.equal(wrong(),false);
            assert.equal(op.phase,phase);
            assert.deepEqual(op.results,[2]);
            assert.equal(correct(),phase==="report");
            assert.equal(op.phase,phase==="report"?"idle":phase);
            assert.deepEqual(op.results,phase==="report"?[]:[2]);
            if(phase==="report") assert.equal(correct(),false);
        }
    }
    const dismiss=owner.slice(owner.indexOf("    function dismissHunterOperationWindow("),owner.indexOf("    function cancelDestructiveConfirm("));
    assert.match(dismiss,/KillBackend\.KillStore\.acknowledgeDonorBulkReport\(\)/);
    assert.doesNotMatch(dismiss,/hunterOperationController\.(?:phase|kind|targets|results|completed|total)\s*=/);
});

test("K6d: Hunter emits legacy presentation events without retaining a widget", () => {
    const controller=read("services/kill/HunterOperationController.qml");
    const owner=read("widgets/AppControlW.qml");
    const a=controller.indexOf("    function refreshMessage(");
    const b=controller.indexOf("    function record(",a);
    const events=[];
    const api=new Function("events",
        "let legacyPresentationAvailable=false,recipientOwned=false,phase='idle',kind='',message='',completed=0,total=0,results=[],targets=[],pendingTargets=[],cursor=0,activeTarget=null,activeResult=null,activeProtocolError=false,policyReady=true;"+
        "function operationLabel(){return 'ALL';} function operationStatusLine(){return 'synthetic';}"+
        "function legacyMessagePublished(v){events.push(['message',v]);} function legacyWindowRequested(...v){events.push(['window',...v]);} function legacyReviewRejected(){events.push(['rejected']);} function dispatchNext(){events.push(['dispatch']);}"+
        controller.slice(a,b)+
        "\nreturn {start,showWindow,refreshMessage,available:v=>legacyPresentationAvailable=v,reset:()=>phase='idle'};")(events);
    const target={pid:4321,startTicks:98765,name:"synthetic",identity:"synthetic"};
    api.start("kill-all",[target],false);
    assert.deepEqual(events,[]);
    api.available(true);
    api.start("kill-all",[target],false);
    assert.equal(events[0][0],"window");
    assert.deepEqual(events[0].slice(-2),[true,true]);
    assert.equal(events[1][0],"message");
    assert.deepEqual(events[2],["dispatch"]);
    assert.equal(api.showWindow(),true);
    assert.deepEqual(events[3],["window","kill-all","",true,false]);
    api.reset(); events.length=0;
    api.start("kill-all",[{...target,startTicks:0}],false);
    assert.deepEqual(events,[["rejected"]]);
    events.length=0; api.available(false);
    api.start("kill-all",[target],true);
    assert.deepEqual(events,[["dispatch"]]);
    assert.equal(api.showWindow(),false);
    assert.match(owner,/function onLegacyWindowRequested\(operationKind, title, resetChoice, clearTargets\)/);
    assert.match(owner,/function onLegacyReviewRejected\(\)\s*\{\s*appControlWindow\.cancelDestructiveConfirm\(\)/);
    assert.doesNotMatch(controller,/\bhost\b/);
});

test("K7b: CPU++ process identity, glow clearance and yellow cancellation", () => {
    const identity=recipient.slice(recipient.indexOf("id: identityGroup"),recipient.indexOf('objectName: "cpuPlusProcessExactIdentity"'));
    assert.match(identity,/id: identityGlyph[\s\S]*?anchors.verticalCenter: parent.verticalCenter[\s\S]*?color: Colors.red[\s\S]*?layer.effect: DropShadow/);
    assert.match(identity,/id: identityText[\s\S]*?anchors.verticalCenter: parent.verticalCenter/);
    assert.match(identity,/objectName: "cpuPlusProcessIdentityName"[\s\S]*?layer.effect: DropShadow/);
    assert.match(identity,/objectName: "cpuPlusProcessIdentityMetadata"[\s\S]*?layer.effect: DropShadow/);
    assert.match(recipient,/objectName: "cpuPlusProcessStateLabel"[\s\S]*?anchors.bottom: parent.bottom[\s\S]*?layer.effect: DropShadow/);
    assert.match(recipient,/objectName: "cpuPlusProcessGlowGutter"[\s\S]*?x: 8\s*y: 8\s*width: Math.max\(0,actuatorScroll.width-30\)/);
    assert.match(recipient,/contentHeight: height\s*interactive: false/);
});

test("K7c: independent selected detail channels share one mini publication", () => {
    const store=read("services/kill/KillStore.qml");
    const telemetry=read("services/system/ProcessTelemetry.qml");
    const session=read("services/kill/KillDetailSession.qml");
    assert.match(store,/id: cpuHistories[\s\S]*?taskMiniCpuHistories: histories\.taskMiniCpuHistories[\s\S]*?taskMiniDisplayRevision: histories\.taskMiniDisplayRevision/);
    assert.match(store,/id: cpuGraph[\s\S]*?telemetry: cpuDetailSampler[\s\S]*?sharedMiniController: graph/);
    assert.match(store,/id: cpuSelectedDetail[\s\S]*?state: cpuHistories[\s\S]*?collectionAllowed: root\.collectionEnabled/);
    assert.match(store,/id: selectedDetail[\s\S]*?collectionAllowed: root\.collectionEnabled/);
    assert.match(store,/id: cpuDetailSampler\s*detailOnly: true\s*onDetailProbeReady: function\(sample\) \{ cpuSelectedDetail\.accept\(sample\); \}/);
    assert.match(telemetry,/function refreshSnapshot\(\)\s*\{\s*if \(detailOnly \|\| snapshotLoading\)/);
    assert.match(telemetry,/function refreshMiniProbe\(request\)\s*\{\s*if \(detailOnly \|\| miniProbeLoading\)/);
    assert.match(session,/requestedKey: !collectionAllowed \? "" : cpuActive/);
    assert.equal((store.match(/id: taskManagerRefreshTimer/g)||[]).length,1);
    assert.equal((store.match(/id: taskMiniDisplayTimer/g)||[]).length,1);
});

test("K7d: observed extra metric samples and no fabricated missing history", () => {
    const src=read("services/system/ProcessTelemetry.qml");
    const a=src.indexOf("    function parseDetailProbe(output) {");
    const b=src.indexOf("\n    Process {",a);
    let now=1000;
    const parse=new Function("Date", "let detailProbeGeneration=2,detailProbeActiveGeneration=2,detailProbePid=4321,detailProbeLastTicks=-1,detailProbeLastIoBytes=-1,detailProbeLastMs=0,detailProbeRequest={pid:4321,startTicks:98765,fallbackCpu:11};"+src.slice(a,b)+"\nreturn parseDetailProbe;")({now:()=>now});
    const first=parse("4321 100 2048 100000 100 4 1000 98765 1000 29 65536");
    assert.equal(first.swapKiB,65536);
    assert.equal(first.threadCount,29);
    assert.equal(first.rssObserved,true);
    assert.equal(first.ioRateObserved,false);
    assert.equal(first.ageObserved,true);
    now=2000;
    const second=parse("4321 200 3072 100000 100 4 1049576 98765 1001 30 0");
    assert.equal(second.swapKiB,0);
    assert.equal(second.ioRateObserved,true);
    assert.equal(second.ioRateBytes,1048576);
    now=3000;
    const unavailable=parse("4321 300 - 100000 100 4 - 98765 - -");
    assert.equal(unavailable.rssObserved,false);
    assert.equal(unavailable.threadCount,null);
    assert.equal(unavailable.swapKiB,null);
    assert.equal(unavailable.ioRateObserved,false);
    assert.equal(unavailable.ageObserved,false);
    now=4000;
    assert.equal(parse("4321 400 3072 100000 100 4 1049576 98765 1003 30").ioRateObserved,false);
    assert.equal(parse("4321 400 3072 100000 100 4 1049576 98764 1003 30"),null);
    const graph=read("services/kill/TaskGraphController.qml");
    const start=graph.indexOf("    function appendExtraDetailHistories(");
    const end=graph.indexOf("    function applyDetailProbe(",start);
    const state={taskExtraDetailHistories:{rss:[],threads:[],io:[],age:[],swap:[]},taskHistoryLimit:3};
    const append=new Function("presentationState",graph.slice(start,end)+"\nreturn appendExtraDetailHistories;")(state);
    append(first); append(second);
    assert.deepEqual(state.taskExtraDetailHistories.rss,[2,3]);
    assert.deepEqual(state.taskExtraDetailHistories.threads,[29,30]);
    assert.deepEqual(state.taskExtraDetailHistories.swap,[64,0]);
    assert.deepEqual(state.taskExtraDetailHistories.io,[1]);
    for(let n=0;n<4;n++) append(second);
    assert.equal(state.taskExtraDetailHistories.rss.length,3);
    append(unavailable);
    assert.deepEqual(state.taskExtraDetailHistories,{rss:[],threads:[],io:[],age:[],swap:[]});
    assert.match(recipient,/objectName: "cpuPlusDetailGraph-"\+extraMetric.modelData.key/);
    assert.match(recipient,/historyLimit: history.taskHistoryLimit\s*scrollDuration: history.taskGraphScrollDuration/);
    assert.match(read("services/kill/KillStore.qml"),/id: cpuGraph[\s\S]*?extraDetailHistoryEnabled: true/);
});

test("K7e: metric cards select at most two graphs and preserve fixed quick controls",()=>{
    const a=recipient.indexOf("    function toggleMetricGraph(");
    const b=recipient.indexOf("\n    readonly property var gate",a);
    assert.ok(a>=0 && b>a);
    const api=new Function("let selectedGraphKeys=['cpu','mem'];"+recipient.slice(a,b)+"\nreturn {toggleMetricGraph,get:()=>selectedGraphKeys};")();
    for (const [key,want] of [["rss",["mem","rss"]],["threads",["rss","threads"]],["rss",["threads"]],["combined",["combined","score"]],["io",["io"]],["pid",["io"]],["swap",["io","swap"]],["io",["swap"]],["swap",[]]]) {
        api.toggleMetricGraph(key);
        assert.deepEqual(api.get(),want);
    }
    assert.match(donorView,/property bool metricGraphSelectionEnabled: false/);
    assert.match(donorView,/onClicked: taskManagerBody.metricGraphRequested\(taskMetricCard.graphKey\)/);
    assert.match(donorView,/host.toggleTaskMetricFavorite\(/);
    assert.match(donorView,/Qt.tint\(Colors.black,Qt.rgba\(modelData.baseAccent.r/);
    assert.match(recipient,/metricGraphSelectionEnabled: true\s*selectedGraphKeys: workspace.selectedGraphKeys/);
    assert.match(recipient,/\.filter\(m=>workspace.selectedGraphKeys.indexOf\(m.key\)>=0\)/);
    assert.match(recipient,/id: quickFooter[\s\S]*?anchors.bottom: parent.bottom/);
    assert.match(recipient,/viewportHeight: Math.max\(1,actuatorScroll.height - quickFooter.height - 24\)/);
    assert.doesNotMatch(recipient,/cpuPlusKillActuatorScroll/);
    assert.match(recipient,/contentHeight: height\s*interactive: false/);
});

test("K7f: swap replaces PID only in recipient cards and identity stays readable",()=>{
    assert.match(donorView,/metrics\[4\] = \{id:"swap",label:"SWAP"/);
    assert.match(donorView,/baseAccent:Colors.resourceColor\("swap"\)/);
    assert.match(recipient,/\{key:"swap", label:"SWAP", unit:" MiB"/);
    assert.match(recipient,/workspace.reviewInk\("PID ", Colors.magenta\)/);
    assert.match(recipient,/workspace.reviewInk\(workspace.selectedPid, Colors.white\)/);
    assert.match(recipient,/objectName: "cpuPlusProcessIdentityMetadata"[\s\S]*?color: Colors.magenta; transparentBorder: true/);
    const src=read("services/system/ProcessTelemetry.qml");
    const a=src.indexOf("    function refreshDetailProbe(");
    const b=src.indexOf("    function parseDetailProbe(",a);
    const probe=src.slice(a,b);
    assert.match(probe,/\^VmRSS:/);
    assert.match(probe,/\^VmSwap:/);
    assert.equal((probe.match(/\/proc\/\$pid\/status/g)||[]).length,1);
});
