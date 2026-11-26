"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const read = p => fs.readFileSync(path.resolve(__dirname, "../..", p), "utf8");
const recipient = read("widgets/cpuplus/CpuPlusKillWorkspace.qml");
const host = read("widgets/CpuPlusW.qml");
const donorView = read("widgets/appcontrol/TaskManagerView.qml");
const gate = read("widgets/appcontrol/AppControlHubActionGate.qml");

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
    assert.match(recipient, /appControlWindow\.taskRows/);
    assert.match(recipient, /appControlWindow\.refreshTaskManager\(\)/);
    assert.match(recipient, /row\._taskRecord === true/);
    assert.match(recipient, /Number\(row\.startTicks\) === selectedStartTicks/);
    assert.match(recipient, /String\(row\.comm \|\| ""\) === selectedComm/);
    for (const forbidden of ["CpuPlusDiagnostics", "CpuPlusProcessPane",
                             "Quickshell.execDetached", "ProcessTelemetry {",
                             "ProcessControl {", "ProcessLimits {", "TaskSafety {"])
        assert.ok(!recipient.includes(forbidden), "unexpected extra owner: " + forbidden);
});

test("all mutation requests use shared action gateway and explicit confirmation", () => {
    assert.match(recipient, /appControlWindow\.hubProcessActionGate/);
    assert.match(recipient, /gate\.exactRow\(selectedPid, selectedStartTicks, selectedComm\)/);
    assert.match(recipient, /gate\.prepare\(/);
    assert.match(recipient, /workspace\.gate\.confirm\(\)/);
    assert.match(recipient, /gate\.cancel\(\)/);
    assert.match(recipient, /gate\.toggleOneShotUnlock\(/);
    assert.match(recipient, /ownedPendingRef && gate\.pending === ownedPendingRef/);
    assert.match(recipient, /workspace\.gate\.pending !== workspace\.ownedPendingRef/);
    assert.match(recipient, /function setLimitPercent\(percent\)[\s\S]*?workspace\.stagedLimitPercent/);
    assert.match(recipient, /Preview only\. Right bay requires APPLY then CONFIRM/);
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
    for(const name of ["cpuPlusKillTargetScroll","cpuPlusKillDetailScroll","cpuPlusKillActuatorScroll"])
        assert.ok(recipient.includes(name));
    assert.match(recipient,/function killAllEligibleTasks\(\) \{ return bulkCandidates\("kill-all"\); \}/);
    assert.match(recipient,/appControlWindow\.prepareCpuBulkReview\(kind,hunterMetricMode,hunterVisibilityMode\)/);
    assert.match(recipient,/appControlWindow\.confirmCpuBulkReview\(bulkReview\)/);
    assert.match(recipient,/objectName: "cpuPlusBulkReview"/);
    const owner=read("widgets/AppControlW.qml");
    assert.match(owner,/cpuBulkReview !== review/);
    assert.match(owner,/hunterOperationController\.start\(review\.kind, review\.targets, true\)/);
    assert.match(owner,/hunterHogCandidates\(metric\)/);
    assert.match(owner,/onCpuPlusProcessVisibleChanged: if \(!cpuPlusProcessVisible\) cpuBulkReview = null/);
});

test("recipient restores existing owner graph and favorite semantics", () => {
    const row = read("widgets/appcontrol/ProcessTargetRow.qml");
    assert.match(recipient,/TaskGraphController\s*\{/);
    assert.match(recipient,/details\.cpuCanvas\.requestPaint\(true\)/);
    assert.match(recipient,/details\.combiScoreCanvas\.requestPaint\(true\)/);
    assert.match(recipient,/detailGraph\.appendSelectedTaskHunterHistories/);
    assert.match(recipient,/appControlWindow\.taskMiniCpuHistories/);
    assert.match(recipient,/appControlWindow\.taskMiniHunterMetricHistories/);
    assert.match(row,/width: 82/);
    assert.match(row,/mini\.combi/);
    assert.match(row,/root\.controller\.miniGraphPoints/);
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
    assert.match(lock,/!root\.masterUnlocked/);
    assert.match(recipient,/objectName: "cpuPlusProcessMasterLock"/);
    assert.match(recipient,/function canChangeLock\(row\)[\s\S]*?exactTargetAvailable[\s\S]*?!gate\.pending && !gate\.busy/);
    assert.match(recipient,/appControlWindow\.taskDangerActionUnlockMode/);
    assert.match(recipient,/appControlWindow\.toggleTaskDangerActionStickyUnlock/);
    assert.match(recipient,/appControlWindow\.toggleTaskDangerStickyUnlock/);
    assert.match(donorView,/property Item actionTarget: null/);
    assert.match(recipient,/actionTarget: rightActions/);
    assert.equal((donorView.match(/parent: taskManagerBody\.actionTarget \|\| taskManagerBody/g)||[]).length,1);
    assert.match(donorView,/property alias actionSection: actionColumn/);
});

test("PROCESS visibility increases only the existing owner sampling cadence", () => {
    const owner=read("widgets/AppControlW.qml");
    const shell=read("shell.qml");
    assert.match(shell,/AppControlW\s*\{[\s\S]*?cpuPlusProcessVisible:\s*cpuPlusWindow\.menuOpen\s*&& cpuPlusWindow\.selectedModeIndex === 1/);
    assert.match(owner,/property bool cpuPlusProcessVisible: false/);
    assert.match(owner,/taskMiniHistoryKeepImmutable: appControlWindow\.menuOpen\s*\|\| appControlWindow\.cpuPlusProcessVisible/);
    assert.match(owner,/function taskMiniProbeNeeded\(\) \{\s*return cpuPlusProcessVisible\s*\|\| \(menuOpen/);
    assert.match(owner,/id: taskManagerRefreshTimer[\s\S]*?interval:\s*appControlWindow\.cpuPlusProcessVisible\s*\? 600/);
    assert.match(owner,/id: taskMiniDisplayTimer[\s\S]*?interval: 1200[\s\S]*?running: appControlWindow\.taskMiniProbeNeeded\(\)/);
    assert.equal((owner.match(/^\s*ProcessTelemetry\s*\{/gm)||[]).length,1);
    assert.doesNotMatch(recipient,/^\s*(Timer|ProcessTelemetry)\s*\{/m);
    assert.match(recipient,/row\.cpuInstant !== undefined \? row\.cpuInstant : row\.cpu/);
    assert.match(recipient,/now-lastDetailSampleMs<history\.taskGraphScrollDuration/);
});

test("both process hosts share the compact information document and action section", () => {
    const app=read("widgets/AppControlW.qml");
    const info=read("widgets/appcontrol/ProcessInformationPanel.qml");
    for (const host of [app,recipient]) {
        assert.match(host,/ProcessInformationButton\s*\{/);
        assert.match(host,/ProcessInformationPanel\s*\{/);
        assert.match(host,/scopeText: visible && task \?/);
        assert.match(host,/maximumHeight: Math.max\(0,/);
    }
    assert.match(info,/onTargetIdentityChanged: open = false/);
    assert.match(info,/onContextActiveChanged: if \(!contextActive\) open = false/);
    assert.match(info,/text: "PROCESS PURPOSE"[\s\S]*text: "PROCESS SCOPE \/\/ LIMIT = THIS PROCESS"[\s\S]*text: "TECHNICAL INFORMATION"[\s\S]*text: "COMMAND LINE"/);
    assert.match(info,/textFormat: Text.PlainText/);
    assert.match(app,/anchors.bottom: pinnedTaskActions.visible \? pinnedTaskActions.top : detailBottomBar.top/);
    assert.match(app,/actionTarget: pinnedTaskActions/);
    assert.match(donorView,/height: taskManagerBody.graphHeight/);
    assert.doesNotMatch(donorView,/id: taskProcessScopeInfo/);
});
