import QtQuick
import Quickshell
import Quickshell.Io
import "TaskFileViewNativeEvidenceM11i.js" as NativeEvidence
import "TaskJsonNativeCallbackGuardM11q.js" as CallbackGuard

// M11m ISOLATED NATIVE TEST: never mount this in shell.qml or TASKS.
// The host's real OS lock/journal are limited to an owned, pre-existing,
// disposable m11l-tasks-copy/todo-copy.json source. Not production authority.
Scope {
    id: bridge

    property string fixturePath: ""
    property string writerId: ""
    // M11q: volatile evidence and generation checks are diagnostics only.
    // They confer no host authority and do not survive a process restart.
    property int sessionGeneration: 0
    // Explicit operator-armed fault in the STANDALONE synthetic harness.
    // Never parsed from production config, persisted or triggered by default.
    property string armedTestFault: "NONE"
    property var nativeEvidence: NativeEvidence.empty()
    readonly property var nativeSummary: NativeEvidence.summarize(nativeEvidence)
    readonly property string nativeRecent: NativeEvidence.recent(nativeEvidence, 6)
    property bool bootstrapTestAuthority: false
    property bool attached: false
    property bool connected: false
    property bool fileLoaded: false
    property bool busy: false
    property bool freezeQueued: false
    property int epoch: -1
    property int nextRequestId: 1
    property int awaitingId: -1
    property string awaitingKind: ""
    property string pendingStageId: ""
    property string pendingRaw: ""
    property string confirmedRaw: ""
    property int confirmedCounter: -1
    property string phase: "UNVERIFIED"
    property string fileState: "UNLOADED"
    property string status: "NOT_STARTED"
    property string errorCode: ""
    property var recentEvents: []
    readonly property bool testStageEligible:
        attached && connected && fileLoaded && !busy && !freezeQueued
        && phase === "JSON_ACTIVE" && fileState === "READY"
        && pendingStageId === ""
    readonly property bool liveWriterAuthorized: false
    readonly property bool sqliteWriteAuthorized: false
    readonly property bool migrationAuthorized: false
    readonly property bool remoteWriteAuthorized: false
    readonly property bool productionActivation: false

    signal observed()

    function event(label) {
        var copy = recentEvents.slice(-5);
        copy.push(label);
        recentEvents = copy;
        // Reuse the existing M11i privacy-safe enum and chain verifier.
        // No paths, JSON payloads, stage IDs or host stdout are recorded.
        var tags = {
            "ATTACH_REQUEST":"ATTACH_REQUEST",
            "FILE_INITIAL_LOAD":"FILE_INITIAL_LOAD",
            "HOST_HELLO":"HOST_HELLO",
            "STAGE_REQUEST":"STAGE_REQUEST",
            "HOST_RESERVED":"HOST_ADMIT",
            "FILE_SAVED":"FILE_SAVED",
            "FILE_READBACK_OK":"FILE_READBACK_OK",
            "HOST_SETTLED":"HOST_SETTLED",
            "FREEZE_REQUESTED":"FREEZE_REQUEST",
            "HOST_FROZEN":"HOST_FROZEN",
            "FILE_SAVE_FAILED":"FILE_SAVE_FAILURE",
            "FILE_LOAD_FAILED":"FILE_LOAD_FAILURE",
            "FILE_READBACK_MISMATCH":"FILE_READBACK_MISMATCH",
            "HOST_REFUSAL":"HOST_REFUSAL",
            "REJECTED":"RECOVERY_REVIEW",
            "STOP_REQUESTED":"STOP_REQUEST",
            "HOST_EXIT":"HOST_EXIT"
        };
        if (Object.prototype.hasOwnProperty.call(tags, label)) {
            nativeEvidence = NativeEvidence.append(nativeEvidence,
                                                   tags[label], phase);
        }
        observed();
    }

    function reject(reason) {
        // Fence any Qt.callLater readback scheduled for an old session.
        sessionGeneration++;
        armedTestFault = "NONE";
        status = "RECOVERY_REVIEW";
        phase = "RECOVERY_REVIEW";
        errorCode = reason;
        connected = false;
        busy = false;
        freezeQueued = true;
        fileLoaded = false;
        fileState = "RECOVERY_REVIEW";
        pendingRaw = "";
        pendingStageId = "";
        awaitingId = -1;
        awaitingKind = "";
        event("REJECTED");
        if (host.running) host.running = false;
    }

    function cycleSyntheticFault() {
        if (!testStageEligible) return false;
        var variants = ["NONE", "AFTER_RESERVE", "AFTER_SAVED",
                        "AFTER_READBACK", "AFTER_SETTLEMENT"];
        var index = variants.indexOf(armedTestFault);
        armedTestFault = variants[(index + 1) % variants.length];
        event("FAULT_ARMED");
        return true;
    }

    function maybeSyntheticFault(point) {
        if (armedTestFault !== point) return false;
        armedTestFault = "NONE";
        event("FAULT_INJECTED");
        // Discard volatile pending data and kill ONLY this disposable host.
        // Leave the durable journal in its observed state for fresh review.
        reject("M11Q_SYNTHETIC_FAULT_" + point);
        return true;
    }

    function beginTest() {
        if (attached || host.running || busy) return false;
        if (typeof fixturePath !== "string"
                || !fixturePath.startsWith("/")
                || !fixturePath.endsWith("/m11l-tasks-copy/todo-copy.json")
                || fixturePath.indexOf("/../") !== -1
                || !/^[A-Za-z0-9][A-Za-z0-9._:-]{7,95}$/.test(writerId)) {
            reject("DISPOSABLE_COPY_PATH_REQUIRED");
            return false;
        }
        sessionGeneration++;
        armedTestFault = "NONE";
        nativeEvidence = NativeEvidence.empty();
        attached = true;
        connected = false;
        fileLoaded = false;
        busy = true;
        freezeQueued = false;
        phase = "UNVERIFIED";
        status = "CONNECTING";
        fileState = "LOADING";
        errorCode = "";
        pendingRaw = "";
        pendingStageId = "";
        confirmedRaw = "";
        confirmedCounter = -1;
        epoch = -1;
        nextRequestId = 1;
        awaitingId = 0;
        awaitingKind = "hello";
        event("ATTACH_REQUEST");
        var dir = fixturePath.slice(0, fixturePath.lastIndexOf("/"));
        var args = ["python3", "-B", "-I",
            Quickshell.shellPath("tests/tasks/fixtures/TaskJsonGateTransportM11m.py"),
            "--directory", dir, "--writer-id", writerId];
        if (bootstrapTestAuthority) args.push("--bootstrap-test");
        host.exec(args);
        return true;
    }

    function send(kind, extra) {
        if (!attached || !connected || !host.running || busy
                || nextRequestId > 50 || freezeQueued && kind === "reserve")
            return false;
        var request = {requestId:nextRequestId, kind:kind};
        if (kind === "reserve") {
            if (!extra || typeof extra.stageId !== "string"
                    || typeof extra.candidateText !== "string"
                    || extra.candidateText.length > 1048576)
                return false;
            request.stageId = extra.stageId;
            request.candidateText = extra.candidateText;
        } else if (kind === "verify") {
            if (!extra || extra.stageId !== pendingStageId || epoch < 0)
                return false;
            request.stageId = extra.stageId;
            request.expectedEpoch = epoch;
        } else if (kind === "fail") {
            if (!extra || extra.stageId !== pendingStageId)
                return false;
            request.stageId = extra.stageId;
        } else if (kind === "freeze") {
            if (epoch < 0) return false;
            request.expectedEpoch = epoch;
        } else if (kind !== "status") return false;
        awaitingId = nextRequestId;
        awaitingKind = kind;
        nextRequestId++;
        busy = true;
        host.write(JSON.stringify(request) + "\n");
        event("HOST_" + kind.toUpperCase() + "_SENT");
        return true;
    }

    function incrementTestTitle() {
        if (!testStageEligible) return false;
        try {
            var doc = JSON.parse(confirmedRaw);
            if (doc.version !== 3 || doc.tasks.length !== 1
                    || doc.tasks[0].title !== "M11M_TEST_" + confirmedCounter
                    || confirmedCounter < 0 || confirmedCounter >= 99)
                throw new Error("NOT_A_TEST_DOCUMENT");
            doc.tasks[0].title = "M11M_TEST_" + (confirmedCounter + 1);
            doc.tasks[0].updatedAtMs = Math.max(Date.now(),
                                                doc.tasks[0].updatedAtMs);
            pendingRaw = JSON.stringify(doc, null, 2) + "\n";
            pendingStageId = "m11m-stage-" + nextRequestId + "-copy";
            fileState = "RESERVING";
            event("STAGE_REQUEST");
            if (!send("reserve", {stageId:pendingStageId,
                                  candidateText:pendingRaw}))
                throw new Error("HOST_RESERVE_SEND_FAILED");
            return true;
        } catch (e) {
            reject("INVALID_TEST_CANDIDATE");
            return false;
        }
    }

    function freezeTest() {
        if (!attached || !connected || phase !== "JSON_ACTIVE" || freezeQueued)
            return false;
        freezeQueued = true;
        event("FREEZE_REQUESTED");
        if (!busy && pendingStageId === ""
                && !send("freeze", {})) {
            reject("FREEZE_SEND_FAILED");
            return false;
        }
        return true;
    }

    function finishStage() {
        armedTestFault = "NONE";
        pendingStageId = "";
        pendingRaw = "";
        fileState = "READY";
        if (freezeQueued && connected && phase === "JSON_ACTIVE"
                && !send("freeze", {}))
            reject("FREEZE_SEND_FAILED");
        observed();
    }

    function acceptHostLine(line) {
        if (!busy || awaitingId < 0 || typeof line !== "string"
                || line.length > 4096) {
            reject("UNEXPECTED_HOST_OUTPUT");
            return;
        }
        try {
            var reply = JSON.parse(line);
            var keys = ["protocol", "requestId", "kind", "ok", "status",
                        "phase", "epoch", "pending", "stageId",
                        "liveWriterAuthorized", "sqliteWriteAuthorized",
                        "migrationAuthorized", "remoteWriteAuthorized"];
            if (!reply || typeof reply !== "object" || Array.isArray(reply)
                    || Object.keys(reply).length !== keys.length)
                throw new Error("BAD_HOST_SCHEMA");
            for (var i = 0; i < keys.length; i++) {
                if (!Object.prototype.hasOwnProperty.call(reply, keys[i]))
                    throw new Error("MISSING_HOST_FIELD");
            }
            if (reply.protocol !== 1 || reply.requestId !== awaitingId
                    || typeof reply.ok !== "boolean"
                    || typeof reply.status !== "string"
                    || typeof reply.pending !== "boolean"
                    || reply.liveWriterAuthorized !== false
                    || reply.sqliteWriteAuthorized !== false
                    || reply.migrationAuthorized !== false
                    || reply.remoteWriteAuthorized !== false
                    || (reply.epoch !== null
                        && (!Number.isSafeInteger(reply.epoch) || reply.epoch < 0))
                    || ["UNVERIFIED", "JSON_ACTIVE", "FREEZE_REQUESTED",
                        "JSON_QUIESCED", "RECOVERY_REVIEW"].indexOf(reply.phase) < 0
                    || (reply.stageId !== null
                        && (typeof reply.stageId !== "string"
                            || reply.stageId.length > 96)))
                throw new Error("UNSAFE_HOST_REPLY");
            if (!reply.ok) {
                event("HOST_REFUSAL");
                reject("HOST_REFUSED_" + reply.status);
                return;
            }
            if (reply.kind !== awaitingKind)
                throw new Error("STALE_HOST_REPLY");
            var kind = awaitingKind;
            var previousEpoch = epoch;
            awaitingId = -1;
            awaitingKind = "";
            busy = false;
            connected = true;
            phase = reply.phase;
            epoch = reply.epoch === null ? -1 : reply.epoch;
            if (kind === "hello") {
                if (phase !== "JSON_ACTIVE" || reply.pending)
                    throw new Error("HOST_REQUIRES_REVIEW");
                status = "TEST_HOST_READY";
                event("HOST_HELLO");
            } else if (kind === "reserve") {
                if (phase !== "JSON_ACTIVE" || !reply.pending
                        || reply.stageId !== pendingStageId
                        || fileState !== "RESERVING")
                    throw new Error("INVALID_RESERVATION");
                fileState = "SAVING";
                event("HOST_RESERVED");
                if (maybeSyntheticFault("AFTER_RESERVE")) return;
                fixtureFile.setText(pendingRaw);
            } else if (kind === "verify") {
                if (!CallbackGuard.settledReplyEligible({
                        attached:attached, connected:connected,
                        hostRunning:host.running, fileState:fileState,
                        pendingStageId:pendingStageId, pendingRaw:pendingRaw,
                        epoch:previousEpoch
                    }, reply, previousEpoch))
                    throw new Error("INVALID_SETTLEMENT");
                // Durable journal may have settled even though this QML
                // process dies before it publishes the confirmed snapshot.
                if (maybeSyntheticFault("AFTER_SETTLEMENT")) return;
                confirmedRaw = pendingRaw;
                confirmedCounter++;
                event("HOST_SETTLED");
                finishStage();
            } else if (kind === "freeze") {
                if (phase !== "JSON_QUIESCED" || reply.pending || !freezeQueued
                        || reply.epoch !== previousEpoch + 1)
                    throw new Error("INVALID_FREEZE");
                status = "TEST_FROZEN";
                fileState = "FROZEN";
                event("HOST_FROZEN");
            } else if (kind !== "status") {
                throw new Error("UNEXPECTED_KIND");
            }
            observed();
        } catch (e) {
            reject("INVALID_HOST_RESPONSE");
        }
    }

    function stopTest() {
        sessionGeneration++;
        armedTestFault = "NONE";
        event("STOP_REQUESTED");
        attached = false;
        connected = false;
        busy = false;
        freezeQueued = true;
        fileLoaded = false;
        fileState = "RECOVERY_REVIEW";
        phase = "RECOVERY_REVIEW";
        status = "STOPPED";
        pendingStageId = "";
        pendingRaw = "";
        if (host.running) host.running = false;
        observed();
    }

    FileView {
        id: fixtureFile
        path: bridge.attached ? bridge.fixturePath : ""
        atomicWrites: true
        blockWrites: false
        watchChanges: false
        printErrors: false

        onLoaded: {
            if (!bridge.attached) return;
            if (bridge.fileState === "LOADING") {
                try {
                    var raw = fixtureFile.text();
                    var doc = JSON.parse(raw);
                    if (!doc || doc.version !== 3 || !Array.isArray(doc.tasks)
                            || doc.tasks.length !== 1 || doc.tasks[0].id !== "t1"
                            || !/^M11M_TEST_(0|[1-9][0-9]?)$/.test(doc.tasks[0].title))
                        throw new Error("INVALID_DISPOSABLE_SOURCE");
                    bridge.confirmedRaw = raw;
                    bridge.confirmedCounter = Number(doc.tasks[0].title.slice(10));
                    bridge.fileLoaded = true;
                    bridge.fileState = "READY";
                    bridge.event("FILE_INITIAL_LOAD");
                } catch (e) { bridge.reject("NOT_A_TEST_FIXTURE"); }
            } else if (bridge.fileState === "VERIFYING") {
                if (fixtureFile.text() !== bridge.pendingRaw) {
                    bridge.event("FILE_READBACK_MISMATCH");
                    bridge.reject("FILE_READBACK_MISMATCH");
                } else {
                    bridge.fileState = "SETTLING";
                    bridge.event("FILE_READBACK_OK");
                    if (bridge.maybeSyntheticFault("AFTER_READBACK")) return;
                    if (!bridge.send("verify", {stageId:bridge.pendingStageId}))
                        bridge.reject("VERIFY_SEND_FAILED");
                }
            } else bridge.reject("UNEXPECTED_FILE_LOAD");
        }
        onLoadFailed: function(error) {
            if (bridge.attached) {
                bridge.event("FILE_LOAD_FAILED");
                bridge.reject("FILE_LOAD_FAILED");
            }
        }
        onSaved: {
            if (!bridge.attached || bridge.fileState !== "SAVING"
                    || bridge.pendingStageId === "") {
                bridge.reject("UNEXPECTED_FILE_SAVED");
                return;
            }
            bridge.fileState = "VERIFYING";
            bridge.event("FILE_SAVED");
            if (bridge.maybeSyntheticFault("AFTER_SAVED")) return;
            var savedTicket = CallbackGuard.ticket(
                bridge.sessionGeneration, bridge.epoch,
                bridge.pendingStageId, bridge.fixturePath);
            Qt.callLater(function() {
                // Neither a canceled host nor a replacement session may
                // initiate a delayed readback from a prior reservation.
                if (CallbackGuard.canDeferredReadback({
                        attached:bridge.attached,
                        connected:bridge.connected,
                        hostRunning:host.running,
                        generation:bridge.sessionGeneration,
                        epoch:bridge.epoch,
                        pendingStageId:bridge.pendingStageId,
                        fixturePath:bridge.fixturePath,
                        fileState:bridge.fileState,
                        pendingRaw:bridge.pendingRaw
                    }, savedTicket)) {
                    fixtureFile.reload();
                }
            });
        }
        onSaveFailed: function(error) {
            bridge.event("FILE_SAVE_FAILED");
            if (bridge.connected && !bridge.busy
                    && bridge.pendingStageId !== ""
                    && bridge.send("fail", {stageId:bridge.pendingStageId}))
                return;
            bridge.reject("FILE_SAVE_FAILURE");
        }
    }

    Process {
        id: host
        stdinEnabled: true
        stdout: SplitParser {
            splitMarker: "\n"
            onRead: function(line) { bridge.acceptHostLine(line); }
        }
        stderr: StdioCollector {}
        onExited: function(code, exitStatus) {
            bridge.sessionGeneration++;
            bridge.connected = false;
            bridge.fileLoaded = false;
            bridge.busy = false;
            bridge.freezeQueued = true;
            bridge.phase = "RECOVERY_REVIEW";
            bridge.fileState = "RECOVERY_REVIEW";
            bridge.pendingStageId = "";
            bridge.pendingRaw = "";
            if (bridge.status !== "STOPPED") {
                bridge.status = "HOST_EXITED";
                bridge.errorCode = "FRESH_OWNER_REVIEW_REQUIRED";
            }
            bridge.event("HOST_EXIT");
        }
    }
}
