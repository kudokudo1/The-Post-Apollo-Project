import QtQuick
import Quickshell
import Quickshell.Io

// M10q UNMOUNTED rehearsal. No task data, no FileView, no actual staging.
// Calls only tests/tasks/fixtures/TaskSqliteHandoffHost.py with an explicit
// private handoff-test.db path. Does not bootstrap or auto-start a process.
// Backend replies are test observations, not a capability for the live store.
Scope {
    id: rehearsal

    property string fixturePath: ""
    property string writerId: ""
    property string status: "NOT_STARTED"
    property string phase: "UNVERIFIED"
    property string errorCode: ""
    property bool busy: false
    property bool initialized: false
    property bool simulatedAdmission: false
    property bool pendingStage: false
    property int epoch: -1
    property int nextRequestId: 1
    property int awaitingId: -1
    property string awaitingKind: ""
    readonly property bool writeReady: false
    readonly property bool sqliteWriteAuthorized: false
    readonly property bool liveChangePerformed: false

    signal observed()

    function beginRehearsal() {
        if (host.running || busy || initialized) return false;
        if (!/^\/.+\/handoff-test\.db$/.test(fixturePath)
                || !/^[A-Za-z0-9][A-Za-z0-9._:-]{7,95}$/.test(writerId)) {
            status = "ERROR";
            errorCode = "EXPLICIT_TEST_FIXTURE_REQUIRED";
            return false;
        }
        status = "CONNECTING";
        phase = "UNVERIFIED";
        errorCode = "";
        initialized = false;
        busy = true; // held until hello
        epoch = -1;
        nextRequestId = 1;
        awaitingId = 0;
        awaitingKind = "hello";
        simulatedAdmission = false;
        pendingStage = false;
        host.exec(["python3", "-B", "-I",
            Quickshell.shellPath("tests/tasks/fixtures/TaskSqliteHandoffHost.py"),
            "--db", fixturePath, "--writer-id", writerId]);
        return true;
    }

    function sendRequest(kind, details) {
        if (!initialized || busy || !host.running || nextRequestId > 1000)
            return false;
        if (["status", "admit", "freeze", "settle"].indexOf(kind) < 0)
            return false;
        var req = {requestId: nextRequestId, kind: kind};
        if (kind === "admit" || kind === "settle") {
            if (!details || !/^[A-Za-z0-9][A-Za-z0-9._:-]{7,95}$/.test(details.stageId))
                return false;
            req.stageId = details.stageId;
        }
        if (kind === "settle") {
            if (typeof details.saved !== "boolean") return false;
            req.saved = details.saved;
        }
        if (kind === "freeze") {
            if (!Number.isSafeInteger(epoch) || epoch < 0) return false;
            req.expectedEpoch = epoch;
        }
        awaitingId = nextRequestId;
        awaitingKind = kind;
        nextRequestId += 1;
        busy = true;
        // Neither the QML surface nor its Python test fixture touches
        // ApolloHubTodoStore.stage() or creates a TASKS database.
        host.write(JSON.stringify(req) + "\n");
        return true;
    }

    function inspectFixture() {
        return sendRequest("status", {});
    }
    function simulateStage(stageId) {
        return sendRequest("admit", {stageId: stageId});
    }
    function simulateFreeze() {
        return sendRequest("freeze", {});
    }
    function simulateSaveCallback(stageId, saved) {
        return sendRequest("settle", {stageId: stageId, saved: saved});
    }

    function acceptLine(line) {
        if (!busy || line.length > 1024 || awaitingId < 0) {
            rejectResponse("UNEXPECTED_OR_OVERSIZED_REPLY");
            return;
        }
        try {
            var msg = JSON.parse(line);
            var fields = ["protocol","requestId","kind","ok","status",
                "phase","epoch","pending","simulatedAdmission",
                "sqliteWriteAuthorized","liveChangePerformed"];
            if (!msg || Object.keys(msg).length !== fields.length)
                throw new Error("BAD_REPLY");
            for (var i=0; i<fields.length; i++)
                if (!Object.prototype.hasOwnProperty.call(msg,fields[i]))
                    throw new Error("MISSING_FIELD");
            if (msg.protocol !== 1 || msg.requestId !== awaitingId
                    || msg.kind !== awaitingKind || typeof msg.ok !== "boolean"
                    || typeof msg.status !== "string" || msg.status.length > 72
                    || msg.sqliteWriteAuthorized !== false
                    || msg.liveChangePerformed !== false
                    || typeof msg.pending !== "boolean"
                    || typeof msg.simulatedAdmission !== "boolean"
                    || ["JSON_ACTIVE","FREEZE_REQUESTED","JSON_QUIESCED",
                        "RECOVERY_REVIEW","UNKNOWN"].indexOf(msg.phase) < 0
                    || !(msg.epoch === null
                        || Number.isSafeInteger(msg.epoch) && msg.epoch >= 0)) {
                throw new Error("UNSAFE_REPLY");
            }
            busy = false;
            awaitingId = -1;
            awaitingKind = "";
            if (!msg.ok) {
                status = "REFUSED";
                errorCode = msg.status;
                // On a rejected test request, simulated admission is
                // deliberately not treated as a live write capability.
            } else {
                status = "READY";
                errorCode = "";
                initialized = true;
            }
            phase = msg.phase;
            epoch = msg.epoch === null ? -1 : msg.epoch;
            pendingStage = msg.pending;
            simulatedAdmission = msg.ok && msg.simulatedAdmission;
            observed();
        } catch (e) {
            rejectResponse("INVALID_HOST_RESPONSE");
        }
    }

    function rejectResponse(why) {
        status = "ERROR";
        errorCode = why;
        phase = "RECOVERY_REVIEW";
        initialized = false;
        simulatedAdmission = false;
        pendingStage = false;
        epoch = -1;
        busy = false;
        awaitingId = -1;
        awaitingKind = "";
        if (host.running) host.running = false;
        observed();
    }

    function stopRehearsal() {
        if (host.running) host.running = false;
        initialized = false;
        busy = false;
        awaitingId = -1;
        awaitingKind = "";
        status = "STOPPED";
        phase = "RECOVERY_REVIEW";
        simulatedAdmission = false;
        pendingStage = false;
        epoch = -1;
    }

    Process {
        id: host
        stdinEnabled: true
        stdout: SplitParser {
            splitMarker: "\n"
            onRead: function(line) { rehearsal.acceptLine(line); }
        }
        // Do not print private paths or subprocess diagnostics to QS logs.
        stderr: StdioCollector {}
        onExited: function(code, exitStatus) {
            rehearsal.initialized = false;
            rehearsal.busy = false;
            rehearsal.awaitingId = -1;
            rehearsal.awaitingKind = "";
            rehearsal.phase = "RECOVERY_REVIEW";
            rehearsal.simulatedAdmission = false;
            rehearsal.pendingStage = false;
            rehearsal.epoch = -1;
            if (rehearsal.status !== "STOPPED") {
                rehearsal.status = "PROCESS_EXITED";
                rehearsal.errorCode = "RESTART_REQUIRES_INSPECTION";
            }
            rehearsal.observed();
        }
    }
}
