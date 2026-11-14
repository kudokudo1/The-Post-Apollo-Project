"use strict";
// BG1-B2B6: mounted old-writer write-path barriers, no production release.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "../..");
const read = name => fs.readFileSync(path.join(root,name),"utf8");
const policy = {};
vm.runInNewContext(
    read("services/time/AlarmWriterBarrierPolicy.js")
        .replace(/^\.pragma library\s*$/m,""),policy);
const plain = value => JSON.parse(JSON.stringify(value));

function ready(overrides={}) {
    return {storageState:"ready",pendingWrite:false,queuedWrite:false,
        migrationRequested:false,ringingCount:0,previewing:false,
        audioState:"IDLE",notificationOutcome:"DELIVERED",
        ...overrides};
}
function functionBody(text,name) {
    const beginning=text.indexOf("    function "+name+"(");
    assert(beginning>=0, "missing "+name);
    const open=text.indexOf("{",beginning);
    let depth=0, end=-1;
    for(let i=open;i<text.length;i++) {
        if(text[i]==="{")depth++;
        if(text[i]==="}") {
            depth--;
            if(depth===0) {end=i+1;break;}
        }
    }
    assert(end>open,"unclosed "+name);
    return text.slice(beginning,end);
}

test("normal ACTIVE phase preserves disk mutation, tick and notification",()=>{
    assert.equal(policy.allowDiskMutation("ACTIVE"),true);
    assert.equal(policy.allowSchedulerTick("ACTIVE"),true);
    assert.equal(policy.allowRingAnnouncement("ACTIVE"),true);
    assert.equal(policy.allowAudioStart("ACTIVE"),true);
    assert.equal(policy.allowLocalStop("ACTIVE"),true);
});

test("QUIESCING/RELEASED and unknown phases block saves, ring and audio",()=>{
    for(const phase of [
        "QUIESCING","RELEASED","FAILED","ACTIVE ",null,undefined,0,
        {},["ACTIVE"],new String("ACTIVE"),true]) {
        assert.equal(policy.allowDiskMutation(phase),false);
        assert.equal(policy.allowSchedulerTick(phase),false);
        assert.equal(policy.allowRingAnnouncement(phase),false);
        assert.equal(policy.allowAudioStart(phase),false);
        assert.equal(policy.allowLocalStop(phase),
            phase==="QUIESCING"||phase==="RELEASED");
    }
    assert.equal(policy.allowLocalStop("QUIESCING"),true);
    assert.equal(policy.allowLocalStop("RELEASED"),true);
});

test("drain preflight refuses pending/queued saves, previews and ringing",()=>{
    assert.equal(policy.canBeginQuiescing(ready()),true);
    const disallowed=[
        {storageState:"saving"},{storageState:"loading"},
        {storageState:"error"},{storageState:"empty"},
        {pendingWrite:true},{queuedWrite:true},
        {migrationRequested:true},{ringingCount:1},
        {previewing:true},{audioState:"QT PLAYING"},
        {audioState:"QT STARTING"},
        {notificationOutcome:"DELIVERY PENDING"},
        {notificationOutcome:undefined},
        {notificationOutcome:null},
        {notificationOutcome:1},
        {notificationOutcome:""}
    ];
    for(const change of disallowed) {
        assert.equal(policy.canBeginQuiescing(ready(change)),false,
            JSON.stringify(change));
    }
});

test("pause request is always denied, even with fake trusted role fields",()=>{
    const candidates=[
        ready(), ready({signedClockAuthority:true,releaseAcknowledged:true,
            ownerEpoch:999,canRing:true}),
        ready({pendingWrite:true}),null,{},[],3,"READY"
    ];
    for(const candidate of candidates) {
        const saved=JSON.stringify(candidate);
        const value=plain(policy.requestPause(candidate));
        assert.equal(value.ok,false);
        assert.equal(value.phase,"ACTIVE");
        assert.equal(value.writerStopped,false);
        assert.equal(value.releaseAcknowledged,false);
        assert.equal(value.ownsAlarmFile,false);
        assert.equal(value.canRing,false);
        assert.equal(value.canTransferOwnership,false);
        assert.equal(JSON.stringify(candidate),saved);
    }
});

test("mounted Clock phase is immutable ACTIVE with no setter/bridge",()=>{
    const qml=read("services/time/AlarmManagerService.qml");
    assert.match(qml,/import "AlarmWriterBarrierPolicy.js" as WriterBarrier/);
    assert.match(qml,/readonly property string alarmWriterBarrierPhase: "ACTIVE"/);
    assert.match(qml,/readonly property bool alarmWriterMaySave:/);
    assert.match(qml,/readonly property bool alarmWriterMayTick:/);
    assert.match(qml,/readonly property bool alarmWriterMayAnnounce:/);
    assert.match(qml,/readonly property bool alarmWriterMayAudioStart:/);
    assert.match(qml,/function requestAlarmWriterPause\(\)/);
    assert.match(functionBody(qml,"requestAlarmWriterPause"),
        /return WriterBarrier\.requestPause\(writerPauseSnapshot\(\)\)/);
    assert.doesNotMatch(qml,/(?:writerBarrierPhase|alarmWriterBarrierPhase)\s*=/);
    assert.doesNotMatch(qml,/function (?:authorize|activate|release)AlarmWriter/);
    assert.doesNotMatch(qml,/AlarmOwnershipBroker|AlarmSignedRoleOrigin|AlarmSignedWriterReleaseFixture|AlarmCanonicalHandoffFixture/);
    assert.doesNotMatch(qml,/Process\s*\{/);
});

test("file write cannot bypass barrier even through direct beginWrite",()=>{
    const qml=read("services/time/AlarmManagerService.qml");
    const begin=functionBody(qml,"beginWrite");
    assert.match(begin,/if \(!alarmWriterMaySave \|\| !Policy\.validDocument\(next\)\)/);
    assert(begin.indexOf("if (!alarmWriterMaySave") <
           begin.indexOf("alarmFile.setText("));
    assert.match(begin,/return false;/);
    assert.match(begin,/alarmFile\.setText\(JSON\.stringify\(next, null, 2\)/);
    assert.equal(qml.match(/alarmFile\.setText\(/g)?.length,1);
    const save=functionBody(qml,"saveDocument");
    assert.match(save,/if \(!alarmWriterMaySave \|\| !canEdit \|\| !Policy\.validDocument\(next\)\)/);
    assert(save.indexOf("!alarmWriterMaySave")<save.indexOf("document = next"));
    assert.match(save,/queuedDocument = next/);
    assert.match(save,/beginWrite\(next\)/);
    assert.match(qml,/readonly property bool canEdit:\s*alarmWriterMaySave &&/);
});

test("no stale queued-write callback can bypass pause barrier",()=>{
    const qml=read("services/time/AlarmManagerService.qml");
    const onSaved=qml.slice(qml.indexOf("        onSaved: {"),
        qml.indexOf("        onSaveFailed:",qml.indexOf("        onSaved: {")));
    assert.match(onSaved,/if \(queued !== null[\s\S]*?&& !manager\.alarmWriterMaySave\)/);
    assert.match(onSaved,/manager\.queuedDocument = queued;/);
    assert.match(onSaved,/manager\.storageError = "WRITER_BARRIER_PENDING_QUEUE";/);
    assert(onSaved.indexOf("&& !manager.alarmWriterMaySave") <
           onSaved.indexOf("manager.beginWrite(queued)"));
    assert.match(onSaved,/manager\.beginWrite\(queued\)/);
    assert.match(onSaved,/manager\.storageState = "ready"/);
});

test("timer, migration and restart ring-announcement paths are gated",()=>{
    const qml=read("services/time/AlarmManagerService.qml");
    assert.match(functionBody(qml,"maybeInitialize"),
        /if \(!alarmWriterMaySave\) return;/);
    assert.match(functionBody(qml,"checkDue"),
        /if \(!alarmWriterMayTick \|\| !canEdit\) return;/);
    assert.match(functionBody(qml,"announceRestoredRinging"),
        /if \(!alarmWriterMayAnnounce \|\| !canEdit\) return;/);
    assert.match(functionBody(qml,"reportRingOccurrence"),
        /if \(!alarmWriterMayAnnounce\) return;/);
    assert.match(qml,/onTriggered: manager\.checkDue\(\)/);
    assert.match(qml,/Qt\.callLater\(manager\.checkDue\)/);
    assert.match(qml,/Qt\.callLater\(manager\.announceRestoredRinging\)/);
});

test("emergency local STOP/SNOOZE fallback is preserved without save claim",()=>{
    const qml=read("services/time/AlarmManagerService.qml");
    for(const name of ["stopAlarm","stopAll","snoozeAlarm"]) {
        const body=functionBody(qml,name);
        assert.match(body,/if \(!canEdit\)/);
        assert.match(body,/document = /);
        assert.match(body,/syncSound\(\)/);
        assert.match(body,/SAVE FAILED/);
    }
    assert.match(functionBody(qml,"syncSound"),
        /if \(!alarmWriterMayAudioStart\) \{[\s\S]*?audioLoader\.active = false/);
    assert.match(functionBody(qml,"previewSound"),
        /if \(!alarmWriterMayAudioStart/);
    const load=qml.slice(qml.indexOf("        onLoaded: {"),
        qml.indexOf("        onStatusChanged:",qml.indexOf("        onLoaded: {")));
    assert.match(load,/if \(item && manager\.alarmWriterMayAudioStart\)/);
    assert.match(qml,/blockWrites: false/);
    assert.match(qml,/atomicWrites: true/);
});

test("no live actuation/deployment, independent secrets or real handoff",()=>{
    const source=read("services/time/AlarmWriterBarrierPolicy.js");
    const qml=read("services/time/AlarmManagerService.qml");
    for(const word of ["systemctl","notify-send","SO_PEERPIDFD",
        "Ed25519PrivateKey","subprocess.Popen","jwt","productionAuthority=true"]) {
        assert(!source.includes(word));
    }
    assert.match(source,/releaseAcknowledged:false/);
    assert.match(source,/writerStopped:false/);
    assert.match(source,/canTransferOwnership:false/);
    assert.match(source,/AUTHENTICATED_WRITER_PAUSE_UNAVAILABLE/);
    assert(!qml.includes('alarmWriterBarrierPhase = "RELEASED"'));
});
