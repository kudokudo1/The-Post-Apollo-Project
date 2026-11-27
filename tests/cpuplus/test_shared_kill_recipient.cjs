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
    for(const name of ["cpuPlusKillTargetScroll","cpuPlusKillInstrumentViewport","cpuPlusKillActuatorScroll"])
        assert.ok(recipient.includes(name));
    assert.match(recipient,/function killAllEligibleTasks\(\) \{ return bulkCandidates\("kill-all"\); \}/);
    assert.match(recipient,/appControlWindow\.prepareCpuBulkReview\(kind,hunterMetricMode,hunterVisibilityMode\)/);
    assert.match(recipient,/appControlWindow\.confirmCpuBulkReview\(bulkReview\)/);
    assert.match(recipient,/objectName: "cpuPlusBulkReview"/);
    const owner=read("widgets/AppControlW.qml");
    assert.match(owner,/cpuBulkReview !== review/);
    assert.match(owner,/hunterOperationController\.start\(review\.kind, review\.targets, true\)/);
    assert.match(owner,/hunterHogCandidates\(metric\)/);
    assert.match(owner,/onCpuPlusProcessVisibleChanged: if \(!cpuPlusProcessVisible\) cancelCpuBulkReview\(cpuBulkReview\)/);
    assert.match(owner,/readonly property var cpuBulkReview: KillBackend\.KillStore\.cpuBulkReview/);
    assert.match(owner,/KillBackend\.KillStore\.captureCpuBulkReview\(kind, metric, visibility, captures\)/);
    assert.match(owner,/if \(!KillBackend\.KillStore\.releaseCpuBulkReview\(review\)\) return false;\s*hunterOperationController\.start/);
});

test("recipient restores existing owner graph and favorite semantics", () => {
    const row = read("widgets/appcontrol/ProcessTargetRow.qml");
    assert.match(recipient,/readonly property var detailGraph: graphController/);
    assert.match(recipient,/details\.cpuCanvas\.requestPaint\(true\)/);
    assert.match(recipient,/details\.combiScoreCanvas\.requestPaint\(true\)/);
    assert.doesNotMatch(recipient,/detailGraph\.appendSelectedTaskHunterHistories/);
    assert.match(host,/graphSource: KillBackend\.KillStore\.graphState/);
    assert.match(recipient,/readonly property var history: graphSource/);
    assert.match(host,/graphController: KillBackend\.KillStore\.graphController/);
    assert.match(host,/graphSession: KillBackend\.KillStore\.detailSession/);
    assert.doesNotMatch(recipient,/appControlWindow\.taskMini(?:CpuHistories|HunterMetricHistories|DisplayRevision)/);
    assert.match(row,/width: 82/);
    assert.match(row,/mini\.combi/);
    assert.match(row,/root\.controller\.miniHistory/);
    assert.match(row,/root\.favorite \? "✦" : "✧"/);
    assert.match(recipient,/appControlWindow\.taskFavoriteKey\(row\)/);
    assert.match(recipient,/ownerFavoriteStore\.favoriteKeys=next/);
    assert.match(recipient,/appControlWindow\.toggleTaskMetricFavorite/);
    assert.doesNotMatch(recipient,/new ProcessTelemetry/);
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
    assert.match(shell,/AppControlW\s*\{[\s\S]*?cpuPlusProcessVisible:\s*cpuPlusWindow\.menuOpen\s*&& cpuPlusWindow\.selectedModeIndex === 1/);
    assert.match(owner,/property bool cpuPlusProcessVisible: false/);
    assert.match(owner,/property: "graphVisible"\s*value: appControlWindow\.menuOpen\s*\|\| appControlWindow\.cpuPlusProcessVisible/);
    assert.match(owner,/function taskMiniProbeNeeded\(\) \{\s*return KillBackend\.KillStore\.miniProbeNeeded/);
    assert.match(shell,/property: "cpuVisible"\s*value: cpuPlusWindow\.menuOpen && cpuPlusWindow\.selectedModeIndex === 1/);
    assert.match(shell,/KillBackend\.KillStore\.collectionEnabled = true/);
    assert.doesNotMatch(owner,/id: taskManagerRefreshTimer|id: taskMiniDisplayTimer|id: taskRefreshAfterKillTimer/);
    const store=read("services/kill/KillStore.qml");
    assert.match(store,/id: taskManagerRefreshTimer[\s\S]*?interval: root.snapshotInterval[\s\S]*?running: root.collectionEnabled/);
    assert.match(store,/id: taskMiniDisplayTimer[\s\S]*?interval: 1200[\s\S]*?running: root.collectionEnabled && root.miniProbeNeeded/);
    assert.match(store,/id: afterAction[\s\S]*?interval: 320/);
    assert.match(store,/^pragma Singleton/m);
    assert.equal((store.match(/^\s*ProcessTelemetry\s*\{/gm)||[]).length,1);
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
    assert.match(recipient,/height: Math.max\(48, lockRail.reservedHeight/);
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
    assert.match(right,/id: reviewCancel[\s\S]*?normalFace: true[\s\S]*?idleForegroundColor: Colors.white[\s\S]*?hoverForegroundColor: Colors.white/);
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
    assert.equal((store.match(/^\s*ProcessPresentationState\s*\{/gm)||[]).length,1);
    assert.equal((store.match(/^\s*TaskGraphController\s*\{/gm)||[]).length,1);
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
    assert.match(owner,/property: "donorActionBlocked"\s*value: appControlWindow.cpuBulkReview !== null/);
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
    assert.match(owner,/property: "donorActionBlocked"\s*value: appControlWindow.cpuBulkReview !== null\s*\|\| appControlWindow.hunterOperationPhase !== "idle"\s*\|\| appControlWindow.destructiveConfirmOpen/);
    assert.match(owner,/function onConfirmationRequested\([\s\S]*?appControlWindow.openDestructiveConfirm\(/);
    assert.match(read("widgets/appcontrol/AppControlHubActionGate.qml"),/KillBackend\.AppControlHubActionGate \{\}/);
});

test("K3c: service lock adapters reject stale, busy, bulk and unsupported requests", () => {
    const store=read("services/kill/KillStore.qml");
    const a=store.indexOf("    function lockModeForIdentity(");
    const b=store.indexOf("    function snapshotCadence(",a);
    assert.ok(a>=0 && b>a);
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
