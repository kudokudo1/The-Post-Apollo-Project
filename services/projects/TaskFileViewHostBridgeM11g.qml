import QtQuick
import Quickshell
import Quickshell.Io
import "TaskFileViewNativeEvidenceM11i.js" as NativeEvidence

// M11g standalone TEST ONLY. Do not mount in shell.qml/TASKS.
// Process owns an M10p OS flock and synthetic SQLite admission journal.
// This QML writes only a preexisting, private fixture-only.json sample.
// QML path checks cannot defeat malicious symlink replacement; use only an
// independently inspected private disposable directory.
Scope {
    id: bridge
    property string fixturePath: ""
    property string writerId: ""
    property bool bootstrapTestAuthority: false
    property bool attached: false
    property bool fileLoaded: false
    property bool connected: false
    property bool busy: false
    property bool freezeQueued: false
    property int epoch: -1
    property int nextRequestId: 1
    property int awaitingId: -1
    property string awaitingKind: ""
    property string pendingStageId: ""
    property string pendingRaw: ""
    property string status: "NOT_STARTED"
    property string phase: "UNVERIFIED"
    property string errorCode: ""
    property string fileState: "UNLOADED"
    property int confirmedCounter: -1
    property var nativeEvidence: NativeEvidence.empty()
    readonly property var nativeSummary: NativeEvidence.summarize(nativeEvidence)
    readonly property string nativeRecent: NativeEvidence.recent(nativeEvidence, 5)
    function observeNative(kind) {
        nativeEvidence = NativeEvidence.append(nativeEvidence, kind, phase);
    }
    readonly property bool testStageEligible:
        connected && fileLoaded && !busy && !freezeQueued
        && phase === "JSON_ACTIVE" && fileState === "READY"
        && pendingStageId === ""
    readonly property bool liveWriterAuthorized: false
    readonly property bool sqliteWriteAuthorized: false
    readonly property bool remoteWriteAuthorized: false
    readonly property bool migrationAuthorized: false
    readonly property bool productionActivation: false

    signal observed()

    function reject(reason) {
        observeNative("RECOVERY_REVIEW");
        status = "RECOVERY_REVIEW";
        phase = "RECOVERY_REVIEW";
        errorCode = reason;
        connected = false;
        busy = false;
        fileLoaded = false;
        fileState = "RECOVERY_REVIEW";
        pendingRaw = "";
        pendingStageId = "";
        freezeQueued = true;
        awaitingId = -1;
        awaitingKind = "";
        if (host.running) host.running = false;
        observed();
    }

    function startTestSession() {
        if (attached || host.running || busy) return false;
        if (!/^\/.+\/m11e-fileview-test\/fixture-only\.json$/.test(fixturePath)
                || !/^[A-Za-z0-9][A-Za-z0-9._:-]{7,95}$/.test(writerId)) {
            reject("PRIVATE_SYNTHETIC_PATH_REQUIRED");
            return false;
        }
        attached = true;
        busy = true;
        fileLoaded = false;
        connected = false;
        fileState = "LOADING";
        confirmedCounter = -1;
        errorCode = "";
        phase = "UNVERIFIED";
        status = "CONNECTING";
        epoch = -1;
        nextRequestId = 1;
        awaitingId = 0;
        awaitingKind = "hello";
        pendingRaw = "";
        pendingStageId = "";
        freezeQueued = false;
        var args = ["python3", "-B", "-I",
            Quickshell.shellPath("tests/tasks/fixtures/TaskFileViewOwnerHostM11g.py"),
            "--db", fixturePath.slice(0, fixturePath.lastIndexOf("/") + 1)
                    + "handoff-test.db",
            "--writer-id", writerId];
        if (bootstrapTestAuthority) args.push("--bootstrap-fixture");
        observeNative("ATTACH_REQUEST");
        host.exec(args);
        observed();
        return true;
    }

    function send(kind, extras) {
        if (!connected || !host.running || busy || nextRequestId > 100
                || ["status","admit","verify","fail","freeze"].indexOf(kind) < 0)
            return false;
        var request = {requestId:nextRequestId,kind:kind};
        if (kind === "admit" || kind === "verify" || kind === "fail") {
            if (!extras || !/^[A-Za-z0-9][A-Za-z0-9._:-]{7,95}$/.test(extras.stageId))
                return false;
            request.stageId = extras.stageId;
        }
        if (kind === "freeze") {
            if (epoch < 0) return false;
            request.expectedEpoch = epoch;
        }
        awaitingId = nextRequestId;
        awaitingKind = kind;
        nextRequestId++;
        busy = true;
        host.write(JSON.stringify(request) + "\n");
        observed();
        return true;
    }

    function incrementSynthetic() {
        if (!testStageEligible) return false;
        observeNative("STAGE_REQUEST");
        var stage = "m11g-synthetic-stage-" + nextRequestId;
        pendingStageId = stage;
        fileState = "RESERVING";
        if (!send("admit",{stageId:stage})) {
            reject("RESERVATION_SEND_FAILED");
            return false;
        }
        return true;
    }

    function freezeTest() {
        if (!connected || phase !== "JSON_ACTIVE" || freezeQueued)
            return false;
        observeNative("FREEZE_REQUEST");
        // Close this QML's local test stage gate before asking the host.
        freezeQueued = true;
        if (!busy && pendingStageId === "") {
            if (!send("freeze",{})) reject("FREEZE_SEND_FAILED");
        }
        observed();
        return true;
    }

    function afterSettle() {
        pendingStageId = "";
        pendingRaw = "";
        fileState = "READY";
        if (freezeQueued && phase === "JSON_ACTIVE") {
            if (!send("freeze",{})) reject("FREEZE_SEND_FAILED");
        }
    }

    function acceptLine(line) {
        if (!busy || line.length > 2048 || awaitingId < 0) {
            reject("UNEXPECTED_HOST_REPLY");
            return;
        }
        try {
            var msg = JSON.parse(line);
            var keys = ["protocol","requestId","kind","ok","status",
                "phase","epoch","pending","payload","liveWriterAuthorized",
                "sqliteWriteAuthorized","remoteWriteAuthorized","migrationAuthorized"];
            if (!msg || typeof msg !== "object" || Array.isArray(msg)
                    || Object.keys(msg).length !== keys.length)
                throw new Error("BAD_HOST_RESPONSE");
            for (var i=0; i<keys.length; i++)
                if (!Object.prototype.hasOwnProperty.call(msg,keys[i]))
                    throw new Error("MISSING_HOST_FIELD");
            if (msg.protocol !== 1 || msg.kind !== awaitingKind
                    || msg.requestId !== awaitingId || typeof msg.ok !== "boolean"
                    || typeof msg.status !== "string" || msg.status.length > 72
                    || typeof msg.pending !== "boolean"
                    || (msg.payload !== null && typeof msg.payload !== "string")
                    || (msg.epoch !== null &&
                        (!Number.isSafeInteger(msg.epoch) || msg.epoch < 0))
                    || ["JSON_ACTIVE","FREEZE_REQUESTED","RECOVERY_REVIEW",
                        "JSON_QUIESCED","UNKNOWN"].indexOf(msg.phase) < 0
                    || msg.liveWriterAuthorized !== false
                    || msg.sqliteWriteAuthorized !== false
                    || msg.remoteWriteAuthorized !== false
                    || msg.migrationAuthorized !== false)
                throw new Error("UNSAFE_HOST_RESPONSE");
            var kind = awaitingKind;
            busy = false;
            awaitingId = -1;
            awaitingKind = "";
            phase = msg.phase;
            epoch = msg.epoch === null ? -1 : msg.epoch;
            if (!msg.ok) {
                observeNative("HOST_REFUSAL");
                reject("HOST_" + msg.status);
                return;
            }
            connected = true;
            status = "TEST_HOST_READY";
            errorCode = "";
            if (kind === "hello") {
                observeNative("HOST_HELLO");
                if (phase !== "JSON_ACTIVE" || msg.pending) {
                    reject("HOST_REQUIRES_RECOVERY_REVIEW");
                    return;
                }
            } else if (kind === "admit") {
                var expected = JSON.parse(msg.payload);
                if (!msg.pending || phase !== "JSON_ACTIVE"
                        || expected.fixture !== "M11E_SYNTHETIC_ONLY"
                        || expected.marker !== "sample"
                        || !Number.isSafeInteger(expected.counter)
                        || expected.counter !== confirmedCounter + 1
                        || expected.revision !== expected.counter
                        || msg.payload.length > 2048)
                    throw new Error("INVALID_STAGE_PAYLOAD");
                pendingRaw = msg.payload;
                observeNative("HOST_ADMIT");
                fileState = "SAVING";
                fixtureFile.setText(pendingRaw);
            } else if (kind === "verify") {
                if (msg.pending || pendingStageId === ""
                        || fileState !== "SETTLING")
                    throw new Error("INVALID_SETTLEMENT");
                confirmedCounter++;
                observeNative("HOST_SETTLED");
                afterSettle();
            } else if (kind === "fail") {
                reject("FILEVIEW_FAILED_REVIEW_REQUIRED");
                return;
            } else if (kind === "freeze") {
                if (phase !== "FREEZE_REQUESTED" || !freezeQueued
                        || msg.pending)
                    throw new Error("FREEZE_NOT_DRAINED");
                status = "TEST_FROZEN";
                observeNative("HOST_FROZEN");
                fileState = "FROZEN";
            }
            observed();
        } catch(e) {reject("INVALID_HOST_RESPONSE");}
    }

    function stopTest() {
        observeNative("STOP_REQUEST");
        freezeQueued = true;
        fileState = "RECOVERY_REVIEW";
        status = "STOPPED";
        connected = false;
        fileLoaded = false;
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
                    var data = JSON.parse(fixtureFile.text());
                    if (data.fixture !== "M11E_SYNTHETIC_ONLY"
                            || data.marker !== "sample"
                            || !Number.isSafeInteger(data.counter)
                            || data.revision !== data.counter)
                        throw new Error("BAD_FIXTURE");
                    bridge.confirmedCounter = data.counter;
                    bridge.fileLoaded = true;
                    bridge.fileState = "READY";
                    bridge.observeNative("FILE_INITIAL_LOAD");
                    bridge.observed();
                } catch(e) {bridge.reject("BAD_INITIAL_TEST_FILE");}
            } else if (bridge.fileState === "VERIFYING") {
                if (fixtureFile.text() !== bridge.pendingRaw) {
                    bridge.observeNative("FILE_READBACK_MISMATCH");
                    if (!bridge.send("fail",{stageId:bridge.pendingStageId}))
                        bridge.reject("MISMATCH_REPORT_FAILED");
                } else {
                    bridge.observeNative("FILE_READBACK_OK");
                    bridge.fileState = "SETTLING";
                    if (!bridge.send("verify",{stageId:bridge.pendingStageId}))
                        bridge.reject("VERIFY_SEND_FAILED");
                }
            } else {
                bridge.reject("UNEXPECTED_FILE_LOAD");
            }
        }
        onLoadFailed: function(error) {
            if (!bridge.attached) return;
            bridge.observeNative("FILE_LOAD_FAILURE");
            if (bridge.pendingStageId !== "" && bridge.connected
                    && !bridge.busy) {
                if (!bridge.send("fail",{stageId:bridge.pendingStageId}))
                    bridge.reject("FILE_LOAD_FAILURE");
            } else bridge.reject("FILE_LOAD_FAILURE");
        }
        onSaved: {
            if (bridge.fileState !== "SAVING" || bridge.pendingStageId === "") {
                bridge.reject("UNEXPECTED_FILE_SAVED");
                return;
            }
            bridge.fileState = "VERIFYING";
            bridge.observeNative("FILE_SAVED");
            // Quickshell 0.2.1 emits saved() before clearing its active
            // asynchronous writer. A same-path reload inside that signal
            // does not start a fresh read. Defer until the callback unwinds,
            // and fence late callbacks with the exact synthetic stage ID.
            var savedStageId = bridge.pendingStageId;
            Qt.callLater(function() {
                if (bridge.attached && bridge.connected
                        && bridge.fileState === "VERIFYING"
                        && bridge.pendingStageId === savedStageId
                        && savedStageId !== "" && bridge.pendingRaw !== "") {
                    fixtureFile.reload();
                }
            });
            bridge.observed();
        }
        onSaveFailed: function(error) {
            bridge.observeNative("FILE_SAVE_FAILURE");
            if (bridge.pendingStageId !== "" && bridge.connected
                    && !bridge.busy) {
                if (!bridge.send("fail",{stageId:bridge.pendingStageId}))
                    bridge.reject("FILE_SAVE_FAILURE");
            } else bridge.reject("FILE_SAVE_FAILURE");
        }
    }

    Process {
        id: host
        stdinEnabled: true
        stdout: SplitParser {
            splitMarker: "\n"
            onRead: function(line) {bridge.acceptLine(line);}
        }
        stderr: StdioCollector {}
        onExited: function(code, exitStatus) {
            bridge.observeNative("HOST_EXIT");
            bridge.connected = false;
            bridge.busy = false;
            bridge.freezeQueued = true;
            bridge.fileLoaded = false;
            bridge.fileState = "RECOVERY_REVIEW";
            bridge.phase = "RECOVERY_REVIEW";
            bridge.pendingStageId = "";
            bridge.pendingRaw = "";
            if (bridge.status !== "STOPPED") {
                bridge.status = "HOST_EXITED";
                bridge.errorCode = "RESTART_REQUIRES_INSPECTION";
            }
            bridge.observed();
        }
    }
}
