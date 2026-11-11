pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import "AlarmManagerPolicy.js" as Policy

// V2 is the only mounted Alarm owner; V1 remains read-only migration input.
// TimeW is just a view. No QtMultimedia dependency in the scheduler itself.
Scope {
    id: manager

    readonly property string storagePath: Quickshell.dataDir + "/time-alarms-v2.json"
    readonly property string legacyPath: Quickshell.dataDir + "/time-alarm-v1.json"
    property string storageState: "loading"
    property string storageError: ""
    property string feedback: "LOADING ALARMS"
    property var document: Policy.initialDocument()
    property var pendingDocument: null
    property var queuedDocument: null
    property bool v2Absent: false
    property bool legacyReadFinished: false
    property var legacyDocument: null
    property string legacyError: ""
    property bool migrationRequested: false
    property double nowMs: Date.now()
    property string audioState: "NOT REQUESTED"
    property bool previewing: false
    property string previewSoundId: "chime"
    property int previewVolume: 60
    readonly property bool canEdit:
        storageState === "ready" || storageState === "empty"
        || storageState === "saving"
    readonly property int count: document.alarms.length
    readonly property int ringingCount: document.alarms.filter(function(a) {
        return a.ringing;
    }).length
    readonly property var firstSoundAlarm: {
        for (let i = 0; i < document.alarms.length; i++) {
            const a = document.alarms[i];
            if (a.ringing && a.soundEnabled)
                return a;
        }
        return null;
    }

    function beginWrite(next) {
        storageState = "saving";
        pendingDocument = next;
        alarmFile.setText(JSON.stringify(next, null, 2) + "\n");
    }
    function saveDocument(next) {
        if (!canEdit || !Policy.validDocument(next))
            return false;
        document = next;
        if (pendingDocument !== null)
            queuedDocument = next;
        else
            beginWrite(next);
        syncSound();
        return true;
    }

    function maybeInitialize() {
        if (!v2Absent || !legacyReadFinished || storageState !== "loading")
            return;
        if (legacyError !== "") {
            storageState = "error";
            storageError = "LEGACY_ALARM_UNREADABLE";
            feedback = "OLD ALARM COULD NOT BE READ // NOT OVERWRITTEN";
            return;
        }
        if (legacyDocument !== null) {
            storageState = "empty";
            migrationRequested = true;
            if (saveDocument(legacyDocument))
                feedback = "MIGRATING EXISTING ALARM // WAIT FOR SAVE";
            else {
                storageState = "error";
                feedback = "ALARM MIGRATION REFUSED";
            }
        } else {
            document = Policy.initialDocument();
            storageState = "empty";
            feedback = "ALARM LIBRARY READY // NO SAVED ALARMS";
        }
    }

    function findAlarm(id) { return Policy.byId(document, id); }
    function nextOccurrence(id) {
        return Policy.nextOccurrenceMs(findAlarm(id), nowMs);
    }
    function nextText(id) {
        const a = findAlarm(id);
        if (!a) return "NO ALARM";
        if (a.ringing) return "RINGING";
        if (a.completed) return "FINISHED";
        if (!a.enabled) return "DISABLED";
        if (a.pausedUntilDate !== ""
                && a.pausedUntilDate > Policy.dayKey(nowMs))
            return "PAUSED UNTIL " + a.pausedUntilDate;
        const next = nextOccurrence(id);
        return next ? "NEXT // " + new Date(next).toLocaleString()
                    : "NO FUTURE OCCURRENCE";
    }

    function createAlarm() {
        if (!canEdit) { feedback = "STORAGE UNAVAILABLE"; return 0; }
        const r = Policy.create(document);
        if (!r.ok) { feedback = r.error; return 0; }
        if (!saveDocument(r.document)) return 0;
        feedback = "ALARM CREATED // EDIT AND ENABLE TO ARM";
        return r.id;
    }
    function duplicateAlarm(id) {
        if (!canEdit) return 0;
        const r = Policy.duplicate(document, id);
        if (!r.ok) { feedback = r.error; return 0; }
        if (!saveDocument(r.document)) return 0;
        feedback = "COPY CREATED // EDIT AND ARM";
        return r.id;
    }
    function saveAlarm(id, edit) {
        if (!canEdit) { feedback = "STORAGE UNAVAILABLE"; return false; }
        const r = Policy.update(document, id, edit, Date.now());
        if (!r.ok) { feedback = r.error; return false; }
        if (!saveDocument(r.document)) return false;
        feedback = "ALARM SAVED";
        return true;
    }
    function enableAlarm(id, enabled) {
        return saveAlarm(id, {enabled: enabled});
    }
    function pauseAlarm(id, resumeDate) {
        if (!Policy.validDate(resumeDate, true)) {
            feedback = "INVALID RESUME DATE";
            return false;
        }
        const a = findAlarm(id);
        if (!a) return false;
        if (resumeDate !== "" && resumeDate <= Policy.dayKey(Date.now())) {
            feedback = "RESUME DATE MUST BE IN THE FUTURE";
            return false;
        }
        if (resumeDate !== "" && a.mode === "once" && a.date < resumeDate) {
            feedback = "ONE-TIME ALARM WOULD EXPIRE BEFORE RESUME";
            return false;
        }
        return saveAlarm(id, {pausedUntilDate: resumeDate});
    }
    function removeAlarm(id) {
        if (!canEdit) return false;
        const r = Policy.remove(document, id);
        if (!r.ok) { feedback = r.error; return false; }
        const ok = saveDocument(r.document);
        if (ok) feedback = "ALARM DELETED";
        return ok;
    }

    // STOP/STOP ALL always silences locally, including when persistence is
    // unhealthy. The UI explicitly warns when the stop could not be saved.
    function stopAlarm(id) {
        const r = Policy.stop(document, id);
        if (!r.ok) return false;
        if (!canEdit) {
            document = r.document;
            syncSound();
            feedback = "SILENCED LOCALLY // SAVE FAILED // MAY REPEAT";
            return false;
        }
        const ok = saveDocument(r.document);
        if (ok) feedback = "ALARM STOPPED";
        return ok;
    }
    function stopAll() {
        let next = document, countStopped = 0;
        for (let i = 0; i < document.alarms.length; i++) {
            const id = document.alarms[i].id;
            const r = Policy.stop(next, id);
            if (r.ok) { next = r.document; countStopped++; }
        }
        if (countStopped === 0) return false;
        if (!canEdit) {
            document = next;
            syncSound();
            feedback = "SILENCED LOCALLY // SAVE FAILED";
            return false;
        }
        const ok = saveDocument(next);
        if (ok) feedback = "ALL RINGING ALARMS STOPPED";
        return ok;
    }
    function snoozeAlarm(id) {
        const r = Policy.snooze(document, id, Date.now());
        if (!r.ok) return false;
        if (!canEdit) {
            document = r.document;
            syncSound();
            feedback = "SNOOZED LOCALLY // SAVE FAILED";
            return false;
        }
        const ok = saveDocument(r.document);
        if (ok) feedback = "SNOOZED // 5 MINUTES";
        return ok;
    }

    function previewSound(soundId, volumePercent) {
        if (ringingCount > 0 || Policy.SOUND_IDS.indexOf(soundId) < 0
                || !Number.isInteger(volumePercent)
                || volumePercent < 0 || volumePercent > 100)
            return false;
        previewing = true;
        previewSoundId = soundId;
        previewVolume = volumePercent;
        syncSound();
        previewTimer.restart();
        feedback = "TEST SOUND // 4 SECONDS";
        return true;
    }
    function endPreview() {
        previewing = false;
        previewTimer.stop();
        syncSound();
    }
    function syncSound() {
        // Deterministic first audible alarm if several alarms ring together.
        // Every ringing alarm remains visible and independently stoppable.
        const sourceId = previewing ? previewSoundId
                         : firstSoundAlarm ? firstSoundAlarm.soundId : "";
        const volume = previewing ? previewVolume
                       : firstSoundAlarm ? firstSoundAlarm.volumePercent : 60;
        if (sourceId === "") {
            audioLoader.active = false;
            return;
        }
        if (!audioLoader.active) {
            audioLoader.active = true;
            return;
        }
        if (audioLoader.item) {
            const changed = audioLoader.item.soundId !== sourceId;
            audioLoader.item.soundId = sourceId;
            audioLoader.item.outputVolume = volume / 100;
            if (changed || !audioLoader.item.requested)
                audioLoader.item.start();
        }
    }
    function checkDue() {
        if (!canEdit) return;
        const r = Policy.tick(document, nowMs);
        if (!r.changed) {
            if (firstSoundAlarm && !audioLoader.active)
                syncSound();
            return;
        }
        if (saveDocument(r.document)) {
            if (r.started.length) {
                if (previewing) endPreview();
                feedback = "RINGING // " + r.started.length + " ALARM(S)";
            }
            else if (r.missed.length)
                feedback = "MISSED // " + r.missed.length + " ALARM(S)";
        }
    }

    Timer {
        interval: 1000
        running: true
        repeat: true
        onTriggered: {
            manager.nowMs = Date.now();
            manager.checkDue();
        }
    }
    Timer {
        id: previewTimer
        interval: 4000
        repeat: false
        onTriggered: manager.endPreview()
    }
    Loader {
        id: audioLoader
        active: false
        source: "AlarmAudioV2.qml"
        onLoaded: {
            if (item) {
                const a = manager.firstSoundAlarm;
                item.soundId = manager.previewing ? manager.previewSoundId
                               : a ? a.soundId : "chime";
                item.outputVolume = (manager.previewing ? manager.previewVolume
                                    : a ? a.volumePercent : 60) / 100;
                item.start();
            }
        }
        onStatusChanged: {
            if (status === Loader.Error)
                manager.audioState = "AUDIO MODULE UNAVAILABLE";
        }
    }
    Connections {
        target: audioLoader.item
        ignoreUnknownSignals: true
        function onFailed(message) { manager.audioState = message; }
        function onPlaying() { manager.audioState = "PLAYING"; }
    }

    FileView {
        id: alarmFile
        path: manager.storagePath
        watchChanges: false
        atomicWrites: true
        blockWrites: false
        printErrors: false
        onLoaded: {
            if (manager.storageState === "saving") return;
            const parsed = Policy.parse(alarmFile.text());
            if (!parsed.ok) {
                manager.storageState = "error";
                manager.storageError = parsed.error;
                manager.feedback = "V2 FILE INVALID // NOT OVERWRITTEN";
                return;
            }
            manager.document = parsed.document;
            manager.storageState = "ready";
            manager.feedback = "SAVED ALARMS LOADED";
            Qt.callLater(manager.checkDue);
        }
        onLoadFailed: function(error) {
            if (error === FileViewError.FileNotFound) {
                manager.v2Absent = true;
                manager.maybeInitialize();
            } else {
                manager.storageState = "error";
                manager.storageError = "V2_FILE_UNREADABLE";
                manager.feedback = "V2 ALARMS UNREADABLE // NOT OVERWRITTEN";
            }
        }
        onSaved: {
            if (manager.storageState !== "saving" || manager.pendingDocument === null)
                return;
            const saved = manager.pendingDocument;
            const queued = manager.queuedDocument;
            manager.pendingDocument = null;
            manager.queuedDocument = null;
            if (queued !== null
                    && JSON.stringify(saved) !== JSON.stringify(queued))
                manager.beginWrite(queued);
            else {
                manager.storageState = "ready";
                if (manager.migrationRequested) {
                    manager.migrationRequested = false;
                    manager.feedback = "V1 ALARM MIGRATED // V1 FILE PRESERVED";
                }
                Qt.callLater(manager.checkDue);
            }
        }
        onSaveFailed: function(error) {
            manager.pendingDocument = null;
            manager.queuedDocument = null;
            manager.storageState = "error";
            manager.storageError = "V2_SAVE_FAILED";
            manager.feedback = "SAVE FAILED // NOT DURABLE";
        }
    }
    FileView {
        id: legacyFile
        path: manager.legacyPath
        watchChanges: false
        printErrors: false
        onLoaded: {
            const result = Policy.migrateLegacy(legacyFile.text(), Date.now());
            if (result.ok) manager.legacyDocument = result.document;
            else manager.legacyError = result.error;
            manager.legacyReadFinished = true;
            manager.maybeInitialize();
        }
        onLoadFailed: function(error) {
            if (error !== FileViewError.FileNotFound)
                manager.legacyError = "V1_FILE_UNREADABLE";
            manager.legacyReadFinished = true;
            manager.maybeInitialize();
        }
    }
}
