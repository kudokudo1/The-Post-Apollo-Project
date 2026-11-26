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
