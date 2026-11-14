"use strict";
// BG1-B2B4: local write-drain evidence, NEVER actual Quickshell release.
const test = require("node:test");
const assert = require("node:assert/strict");
const vm = require("node:vm");
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(__dirname, "../..");
const read = p => fs.readFileSync(path.join(root,p), "utf8");
const policy = {};
vm.runInNewContext(
    read("services/time/AlarmWriterQuiescencePolicy.js").replace(
        /^\.pragma library\s*$/m,""), policy);
const plain = value => JSON.parse(JSON.stringify(value));
function snapshot(override={}) {
    return {
        storageState:"ready",
        pendingWrite:false, queuedWrite:false, migrationRequested:false,
        ringingCount:0, previewing:false, audioState:"IDLE",
        notificationOutcome:"DELIVERED",
        ...override
    };
}

test("healthy quiescent local queue is only observation, never a writer release",()=>{
    const state=plain(policy.status(snapshot()));
    assert.deepEqual(state,{
        locallyDrained:true, reason:"LOCAL_WRITE_QUEUE_DRAINED_ONLY",
        releaseAcknowledged:false, canTransferOwnership:false
    });
    const request=plain(policy.requestRelease(snapshot()));
    assert.deepEqual(request,{
        ok:false, reason:"NO_TRUSTED_WRITER_RELEASE_BRIDGE",
        locallyDrained:true, releaseAcknowledged:false,
        canTransferOwnership:false, ownsRealAlarmFile:false, canRing:false
    });
    assert(!JSON.stringify(request).includes("token"));
});

test("every pending/delivering state fails local readiness, without mutating data",()=>{
    const cases=[
        [{storageState:"loading"},"WRITER_STORAGE_NOT_READY"],
        [{storageState:"saving"},"WRITER_STORAGE_NOT_READY"],
        [{storageState:"empty"},"WRITER_STORAGE_NOT_READY"],
        [{storageState:"error"},"WRITER_STORAGE_NOT_READY"],
        [{pendingWrite:true},"WRITER_SAVE_STILL_IN_FLIGHT"],
        [{queuedWrite:true},"WRITER_SAVE_STILL_IN_FLIGHT"],
        [{migrationRequested:true},"WRITER_LEGACY_MIGRATION_PENDING"],
        [{ringingCount:1},"ACTIVE_ALARM_RINGING"],
        [{previewing:true},"ALARM_AUDIO_PREVIEW_ACTIVE"],
        [{audioState:"QT PLAYING"},"ALARM_AUDIO_NOT_IDLE"],
        [{audioState:"QT STARTING"},"ALARM_AUDIO_NOT_IDLE"],
        [{notificationOutcome:"DELIVERY PENDING"},"ALARM_NOTIFICATION_IN_FLIGHT"],
    ];
    for(const [change,reason] of cases) {
        const input=snapshot(change), before=JSON.stringify(input);
        assert.equal(policy.status(input).reason,reason);
        const request=policy.requestRelease(input);
        assert.equal(request.ok,false);
        assert.equal(request.reason,reason);
        assert.equal(request.ownsRealAlarmFile,false);
        assert.equal(JSON.stringify(input),before);
    }
});

test("invalid, forged, missing or hostile snapshot types are rejected",()=>{
    const invalid=[
        null,undefined,[],{},3,"ready",
        snapshot({ringingCount:NaN}),
        snapshot({ringingCount:-1}),
        snapshot({ringingCount:"0"}),
        snapshot({ringingCount:1.3}),
        snapshot({pendingWrite:"false"}),
        snapshot({queuedWrite:null}),
        snapshot({previewing:0}),
        snapshot({storageState:undefined}),
        snapshot({audioState:{toString:()=>"IDLE"}}),
        snapshot({notificationOutcome:1})
    ];
    for(const input of invalid) {
        const res=policy.status(input);
        assert.equal(res.locallyDrained,false);
        assert.equal(res.reason,"INVALID_WRITER_SNAPSHOT");
        assert.equal(policy.requestRelease(input).ok,false);
    }
});

test("privileged-looking caller data or signed evidence cannot bypass refusal",()=>{
    const privileged=snapshot({
        productionAuthority:true, roleAuthenticated:true,
        signedInstalledClock:true, canWriteAlarmFile:true,
        releaseAcknowledged:true, ownerEpoch:999,
        transferToken:"fake",document:{alarms:[{
            name:"PRIVATE ALARM",note:"PRIVATE NOTE"
        }]}
    });
    const before=JSON.stringify(privileged);
    const report=policy.requestRelease(privileged);
    assert.equal(report.ok,false);
    assert.equal(report.releaseAcknowledged,false);
    assert.equal(report.canTransferOwnership,false);
    assert.equal(report.ownsRealAlarmFile,false);
    assert.equal(JSON.stringify(privileged),before);
    assert(!JSON.stringify(report).includes("PRIVATE"));
    assert(!JSON.stringify(report).includes("fake"));
});

test("future writer barrier model denies both new writes and ticks outside ACTIVE",()=>{
    assert.deepEqual(plain(policy.writerBarrier("ACTIVE")),
        {allowSave:true,allowTick:true});
    for(const phase of ["QUIESCING","RELEASED","FAILED","ACTIVE ",null,{}]) {
        assert.deepEqual(plain(policy.writerBarrier(phase)),
            {allowSave:false,allowTick:false});
    }
});

test("live AlarmManager retains passive B2B4 probe alongside guarded B2B6 write routes",()=>{
    const qml=read("services/time/AlarmManagerService.qml");
    assert.match(qml,/import "AlarmWriterQuiescencePolicy.js" as WriterQuiescence/);
    assert.match(qml,/readonly property bool writerReleaseAcknowledged: false/);
    assert.match(qml,/readonly property bool writerReleaseActivated: false/);
    assert.match(qml,/readonly property var writerQuiescenceStatus:/);
    assert.match(qml,/function writerQuiescenceSnapshot\(\)/);
    assert.match(qml,/function requestWriterRelease\(\)/);
    assert.match(qml,/return WriterQuiescence\.requestRelease\(writerQuiescenceSnapshot\(\)\)/);
    const start=qml.indexOf("function requestWriterRelease()");
    const end=qml.indexOf("readonly property bool canEdit:",start);
    assert(start>=0 && end>start);
    const requestBlock=qml.slice(start,end);
    for(const forbidden of ["beginWrite(", "setText(", "saveDocument(",
            "stopAlarm(", "snoozeAlarm(", "checkDue(", "Qt.callLater",
            "request.send", "Process {", "FileView {", "stage(", "write("]) {
        assert(!requestBlock.includes(forbidden),"release request mutates: "+forbidden);
    }
    assert.match(qml,/function saveDocument\(next\) \{\s*if \(!alarmWriterMaySave \|\| !canEdit \|\| !Policy\.validDocument\(next\)\)/);
    assert.match(qml,/function beginWrite\(next\) \{[\s\S]*?if \(!alarmWriterMaySave \|\| !Policy\.validDocument\(next\)\)[\s\S]*?storageState = "saving";/);
    assert.match(qml,/if \(queued !== null\s*&& JSON\.stringify\(saved\) !== JSON\.stringify\(queued\)\)\s*manager\.beginWrite\(queued\);/);
    assert.match(qml,/function checkDue\(\) \{\s*if \(!alarmWriterMayTick \|\| !canEdit\) return;/);
    assert.match(qml,/if \(!canEdit\) \{\s*document = r\.document;\s*syncSound\(\);/);
    assert.match(qml,/atomicWrites: true/);
    assert.match(qml,/blockWrites: false/);
    assert.match(qml,/readonly property string alarmWriterBarrierPhase: "ACTIVE"/);
    assert.match(qml,/return WriterBarrier\.requestPause\(writerPauseSnapshot\(\)\)/);
    assert.match(qml,/if \(!alarmWriterMayAnnounce\) return;/);
    assert.match(qml,/if \(!alarmWriterMayAudioStart\)/);
    assert.equal(qml.match(/alarmFile\.setText\(/g)?.length,1);
    assert(!qml.includes("AlarmOwnershipBroker"));
    assert(!qml.includes("AlarmSignedRoleOrigin"));
    assert(!qml.includes("AlarmCanonicalHandoffFixture"));
});
