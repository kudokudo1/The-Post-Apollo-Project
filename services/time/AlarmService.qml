pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import "AlarmPolicy.js" as AlarmPolicy

// Single Clock alarm owner. Real local system time, never display offset.
// Sound is an optional output; a missing media backend never prevents the
// schedule from being inspected, armed, silenced, or stored.
Scope {
    id: alarmService

    readonly property string storagePath:
        Quickshell.dataDir + "/time-alarm-v1.json"
    property string storageState: "loading"
    property string storageError: ""
    property var document: AlarmPolicy.initialDocument()
    property var pendingDocument: null
    property var queuedDocument: null
    readonly property var alarm: document.alarm
    readonly property bool canEdit:
        storageState === "ready" || storageState === "empty"
        || storageState === "saving"
    readonly property bool ringing: alarm.ringing
    readonly property bool enabled: alarm.enabled
    property string feedback: "ALARM STORE LOADING"
    property string soundState: "NOT REQUESTED"
    property bool previewing: false
    property double nowMs: Date.now()
    readonly property string nextLabel: AlarmPolicy.nextLabel(document, nowMs)

    function beginWrite(next) {
        pendingDocument = next;
        storageState = "saving";
        alarmFile.setText(JSON.stringify(next, null, 2) + "\n");
    }

    function saveDocument(next) {
        if (!canEdit)
            return false;
        document = next; // one live owner, not delayed until disk callback
        if (pendingDocument !== null)
            queuedDocument = next;
        else
            beginWrite(next);
        return true;
    }

    function stopAudio() {
        previewing = false;
        soundPreviewTimeout.stop();
        soundLoader.active = false;
    }

    function ensureAudio() {
        if ((ringing && alarm.soundEnabled) || previewing) {
            soundState = "AUDIO REQUESTED";
            if (!soundLoader.active)
                soundLoader.active = true;
            else if (soundLoader.item)
                soundLoader.item.start();
        } else {
            stopAudio();
        }
    }

    function refreshAlarm() {
        if (!canEdit)
            return;
        const outcome = AlarmPolicy.tick(document, nowMs);
        if (outcome.changed && saveDocument(outcome.document)) {
            if (outcome.event === "ring") {
                feedback = "ALARM RINGING // STOP OR SNOOZE";
                ensureAudio();
            } else if (outcome.event === "expired") {
                feedback = "ALARM EXPIRED // NEXT DAY";
                stopAudio();
            } else if (outcome.event === "snooze-missed") {
                feedback = "MISSED SNOOZE // NEXT DAY";
                stopAudio();
            }
        } else if (ringing && alarm.soundEnabled && !soundLoader.active) {
            // Recovery after a shell reload: recently ringing state is saved.
            ensureAudio();
        }
    }

    function arm(hourText, minuteText, name) {
        if (!canEdit) {
            feedback = "ALARM STORAGE UNAVAILABLE";
            return false;
        }
        const result = AlarmPolicy.withSettings(document, hourText, minuteText,
                                                 name, Date.now());
        if (!result.ok) {
            feedback = result.reason;
            return false;
        }
        stopAudio();
        const accepted = saveDocument(result.document);
        feedback = accepted ? "ALARM ARMED // DAILY LOCAL TIME" : "SAVE FAILED";
        return accepted;
    }

    function disarm() {
        if (!canEdit) return false;
        const result = AlarmPolicy.disarm(document);
        if (!result.ok) return false;
        stopAudio();
        const accepted = saveDocument(result.document);
        feedback = accepted ? "ALARM DISARMED" : "SAVE FAILED";
        return accepted;
    }

    function stopRinging() {
        if (!canEdit || !ringing) return false;
        const result = AlarmPolicy.stop(document);
        if (!result.ok) return false;
        stopAudio();
        const accepted = saveDocument(result.document);
        feedback = accepted ? "ALARM STOPPED // DAILY SCHEDULE RETAINED" : "SAVE FAILED";
        return accepted;
    }

    function snoozeRinging() {
        if (!canEdit || !ringing) return false;
        const result = AlarmPolicy.snooze(document, Date.now());
        if (!result.ok) return false;
        stopAudio();
        const accepted = saveDocument(result.document);
        feedback = accepted ? "SNOOZED // 5 MINUTES" : "SAVE FAILED";
        return accepted;
    }

    function setSoundEnabled(value) {
        if (!canEdit || typeof value !== "boolean") return false;
        const result = AlarmPolicy.withSound(document, value);
        if (!result.ok) return false;
        const accepted = saveDocument(result.document);
        feedback = accepted
            ? (value ? "SOUND ENABLED" : "SOUND DISABLED // VISUAL ONLY")
            : "SAVE FAILED";
        if (accepted) ensureAudio();
        return accepted;
    }

    function previewSound() {
        if (!canEdit || ringing) return false;
        previewing = true;
        ensureAudio();
        soundPreviewTimeout.restart();
        feedback = "SOUND PREVIEW // UP TO 4 SECONDS";
        return true;
    }

    Timer {
        interval: 1000
        running: true
        repeat: true
        onTriggered: {
            alarmService.nowMs = Date.now();
            alarmService.refreshAlarm();
        }
    }

    Timer {
        id: soundPreviewTimeout
        interval: 4000
        repeat: false
        onTriggered: {
            if (!alarmService.ringing) {
                alarmService.stopAudio();
                alarmService.feedback = "SOUND PREVIEW FINISHED";
            }
        }
    }

    Loader {
        id: soundLoader
        active: false
        source: "AlarmAudio.qml"
        onLoaded: {
            if (item && (alarmService.previewing
                    || (alarmService.ringing && alarmService.alarm.soundEnabled)))
                item.start();
        }
        onStatusChanged: {
            if (status === Loader.Error)
                alarmService.soundState = "AUDIO MODULE UNAVAILABLE";
        }
    }

    Connections {
        target: soundLoader.item
        ignoreUnknownSignals: true
        function onFailed(message) {
            alarmService.soundState = message;
        }
    }

    FileView {
        id: alarmFile
        path: alarmService.storagePath
        watchChanges: false
        atomicWrites: true
        blockWrites: false
        printErrors: false

        onLoaded: {
            if (alarmService.storageState === "saving")
                return;
            const parsed = AlarmPolicy.parse(alarmFile.text());
            if (!parsed.ok) {
                alarmService.storageState = "error";
                alarmService.storageError = parsed.reason;
                alarmService.feedback = "INVALID ALARM FILE // NOT OVERWRITTEN";
                return;
            }
            alarmService.document = parsed.document;
            alarmService.storageState = "ready";
            alarmService.storageError = "";
            alarmService.feedback = "ALARM LOADED";
            Qt.callLater(alarmService.refreshAlarm);
        }
        onLoadFailed: function(error) {
            if (alarmService.storageState === "saving")
                return;
            const notFound = error === FileViewError.FileNotFound;
            alarmService.storageState = notFound ? "empty" : "error";
            alarmService.storageError = notFound ? "" : "ALARM_LOAD_FAILED";
            alarmService.feedback = notFound ? "ALARM READY // NOT ARMED"
                                             : "ALARM FILE UNAVAILABLE";
        }
        onSaved: {
            if (alarmService.storageState !== "saving"
                    || alarmService.pendingDocument === null)
                return;
            const saved = alarmService.pendingDocument;
            const queued = alarmService.queuedDocument;
            alarmService.pendingDocument = null;
            alarmService.queuedDocument = null;
            alarmService.storageError = "";
            if (queued !== null
                    && JSON.stringify(saved) !== JSON.stringify(queued))
                alarmService.beginWrite(queued);
            else
                alarmService.storageState = "ready";
        }
        onSaveFailed: function(error) {
            alarmService.pendingDocument = null;
            alarmService.queuedDocument = null;
            alarmService.storageState = "error";
            alarmService.storageError = "ALARM_SAVE_FAILED";
            alarmService.feedback = "ALARM SAVE FAILED // RETRY AFTER RECOVERY";
        }
    }
}
