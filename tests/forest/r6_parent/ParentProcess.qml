import QtQuick
import Quickshell
import Quickshell.Io
import "ParentWire.js" as Wire
import "PublicRuntimeStatusDisplay.js" as Status

// CI-only first actual child exchange. No Loader, history, UI paint or
// installed ForestW connection. The harness owns an independent view object.
// One instance owns one tracked Process for its entire lifetime.
Item {
    id: root
    required property string trial
    required property string fixtureDirectory
    required property var originalOwner
    property var observedOwner: null
    property bool eligible: false
    property bool acceptOffer: false
    readonly property bool current: eligible && originalOwner !== null
        && observedOwner === originalOwner
    property var wire: null
    property string phase: "NEW"
    property int action: 0
    property string pending: ""
    property bool offered: false
    property var ref: null
    property var used: []
    property int sequence: 0
    property string status: ""
    property int originalPid: 0
    property bool startedSeen: false
    property bool exitedSeen: false
    property bool cleanupStarted: false
    property bool killSent: false
    property bool reaped: false
    property bool closeResult: false
    property bool refusedResult: false
    property bool possibleEffect: false
    property string outcome: "NONE"
    property string failure: ""
    readonly property bool running: worker.running
    signal finished()
    signal actionFinished(string code)

    ElapsedTimer { id: trialClock }
    ElapsedTimer { id: phaseClock }
    ElapsedTimer { id: cleanupClock }

    function live() {
        return startedSeen && !exitedSeen && worker.running
            && worker.processId === originalPid && current
            && !cleanupStarted && trialClock.elapsedMs() < 120000
            && phaseClock.elapsedMs() < 5000;
    }
    function start() {
        if (phase !== "NEW" || !current || !Wire.token(trial) || worker.running)
            return false;
        wire = Wire.createWire();
        phase = "STARTING";
        trialClock.restartMs();
        phaseClock.restartMs();
        worker.running = true;
        return true;
    }
    function clearOriginal() {
        // This object cannot mutate another owner's view; no callbacks to a
        // replacement. Clear only its own retained reference and status.
        ref = null;
        sequence = 0;
        status = "";
    }
    function hold(reason) {
        if (reaped || cleanupStarted) return;
        failure = reason; // fixed local labels only
        outcome = possibleEffect ? "UNKNOWN_HOLD" : "REFUSED";
        clearOriginal();
        if (wire) wire.stop();
        pending = "";
        phase = "HOLD";
        cleanupStarted = true;
        cleanupClock.restartMs();
        if (worker.running && (!startedSeen || worker.processId === originalPid))
            worker.signal(15);
    }
    onCurrentChanged: {
        if (!current && phase !== "NEW" && !reaped)
            hold("OWNER_LOST");
    }
    function send(kind,data) {
        if (!live()) return false;
        const raw = wire.prepare({v:1,trial:trial,action:action,kind:kind,data:data});
        if (raw === null || !live()) return false;
        worker.write(raw);
        return true;
    }
    // Explicit harness actions only. No action queue and no automatic retry.
    function request(kind) {
        if (!live() || pending || action >= Wire.ACTIONS) return false;
        let data = {};
        if (kind === "HELLO") {
            if (phase !== "STARTING" || action !== 0) return false;
        } else if (kind === "NEXT") {
            if (phase !== "IDLE") return false;
            clearOriginal();
        } else if (kind === "STEP") {
            if (phase !== "ACTIVE" || ref === null) return false;
            data = {ref:ref};
        } else if (kind === "CLOSE") {
            if (phase !== "IDLE" && phase !== "ACTIVE" && phase !== "BLOCKED")
                return false;
            clearOriginal();
        } else return false;
        if (!wire.reserve(kind === "NEXT")) { hold("RESERVE"); return false; }
        action++;
        pending = kind;
        offered = false;
        phaseClock.restartMs();
        // ACK/STEP/CLOSE writes may race effects; never infer rollback.
        if (kind === "STEP" || kind === "CLOSE") possibleEffect = true;
        if (!send(kind,data)) { hold("WRITE"); return false; }
        return true;
    }
    function exactRef(value) {
        return Wire.exact(value,["requestId","viewKey","generation"])
            && Wire.token(value.requestId) && Wire.token(value.viewKey)
            && value.requestId !== value.viewKey
            && Wire.integer(value.generation,1,Number.MAX_SAFE_INTEGER);
    }
    function prevalidateUnits(units) {
        if (!Array.isArray(units) || units.length > 2 || ref === null)
            return null;
        let seq = sequence, previous = status;
        for (const unit of units) {
            if (!Wire.exact(unit,["requestId","viewKey","generation","sequence","kind","statusPacket"])
                || unit.requestId !== ref.requestId || unit.viewKey !== ref.viewKey
                || unit.generation !== ref.generation || unit.kind !== "STATUS"
                || !Wire.integer(unit.sequence,1,Number.MAX_SAFE_INTEGER)
                || unit.sequence !== seq+1 || !Status.packetOK(unit.statusPacket)
                || !Status.allowed(previous,unit.statusPacket.status)) return null;
            seq = unit.sequence; previous = unit.statusPacket.status;
        }
        return {sequence:seq,status:previous};
    }
    function consume(frame) {
        if (!live() || !pending || frame.trial !== trial || frame.action !== action)
            return false;
        const data = frame.data;
        if (frame.kind === "OPEN_OFFER") {
            if (pending !== "NEXT" || offered || !Wire.exact(data,["ref"])
                || !exactRef(data.ref) || used.length >= 128
                || data.ref.requestId === trial || data.ref.viewKey === trial
                || used.indexOf(data.ref.requestId)>=0 || used.indexOf(data.ref.viewKey)>=0)
                return false;
            offered = true;
            // Independent owner eligibility/decision, never supplied by frame.
            const accepted = current && acceptOffer;
            if (accepted) {
                ref = {requestId:data.ref.requestId,viewKey:data.ref.viewKey,
                    generation:data.ref.generation};
                used = used.concat([ref.requestId,ref.viewKey]);
                possibleEffect = true;
            }
            return send("OPEN_ACK",{ref:data.ref,accepted:accepted});
        }
        if (frame.kind !== "RESULT" || !Wire.exact(data,["code","units"])
            || !Array.isArray(data.units) || typeof data.code !== "string")
            return false;
        const code = data.code;
        let next = "", batch = null;
        if (code === "REFUSED") {
            if (data.units.length) return false;
            refusedResult = true;
            next = "REFUSED_EXIT";
            clearOriginal();
            outcome = possibleEffect ? "UNKNOWN_HOLD" : "REFUSED";
        } else if (pending === "HELLO" && code === "READY" && !data.units.length)
            next = "IDLE";
        else if (pending === "NEXT" && offered && ref !== null
                && code === "TURN_STARTED" && !data.units.length)
            next = "ACTIVE";
        else if (pending === "STEP" && ["ACTIVE","COMMITTED_LOCAL","ABORTED_LOCAL","UNKNOWN_HOLD"].indexOf(code)>=0) {
            batch = prevalidateUnits(data.units);
            if (!batch) return false;
            if ((code === "ACTIVE" && ["LOCAL_COMMIT_RECORDED","UNKNOWN_HOLD"].indexOf(batch.status)>=0)
                || (code === "COMMITTED_LOCAL" && batch.status !== "LOCAL_COMMIT_RECORDED")
                || ((code === "ABORTED_LOCAL" || code === "UNKNOWN_HOLD")
                    && batch.status === "LOCAL_COMMIT_RECORDED")) return false;
            next = code === "ACTIVE" ? "ACTIVE" : code === "COMMITTED_LOCAL" ? "IDLE" : "BLOCKED";
        } else if (pending === "CLOSE" && code === "CLOSED" && !data.units.length) {
            next = "CLOSE_EXIT";
            closeResult = true;
        } else return false;
        // Whole batch validated before any local projection. No UI2 consumer
        // call here; R6d will apply the original Loader guard for each unit.
        if (batch) {
            if (!live()) return false;
            sequence = batch.sequence;
            status = batch.status;
        }
        pending = "";
        phase = next;
        if (code === "COMMITTED_LOCAL" || code === "ABORTED_LOCAL" || code === "UNKNOWN_HOLD")
            outcome = code;
        actionFinished(code); // harness schedules later explicit action
        return true;
    }
    function receiveChunk(data) {
        if (cleanupStarted) return; // original trial has already failed closed
        if (!live() || !wire.receive(data,consume)) hold("STDOUT");
    }
    function exitObserved(code,exitStatus) {
        if (exitedSeen) { failure = "DUPLICATE_EXIT"; return; }
        exitedSeen = true;
        // No acceptance from result or running=false alone. Reject any
        // remainder, prior failure, wrong exit or data after expected result.
        if (!cleanupStarted) {
            const drained = wire && wire.end();
            if (!startedSeen || !current || !drained || pending
                || phaseClock.elapsedMs() >= 5000 || trialClock.elapsedMs() >= 120000
                || exitStatus !== 0 || !((closeResult && phase === "CLOSE_EXIT" && code === 0)
                    || (refusedResult && phase === "REFUSED_EXIT" && code === 2))) {
                failure = "EXIT_UNCERTAIN";
                outcome = possibleEffect ? "UNKNOWN_HOLD" : "REFUSED";
            }
        }
        clearOriginal();
        phase = "EXIT_SEEN";
        settle.restart();
    }

    Process {
        id: worker
        running: false
        command: ["/usr/bin/python3","-I","-B","-u",
            Quickshell.shellPath("runtime/runtime_public_child_r6b.py")]
        workingDirectory: root.fixtureDirectory
        clearEnvironment: true
        environment: ({HOME:root.fixtureDirectory,TMPDIR:root.fixtureDirectory,
            LANG:"C.UTF-8",FOREST_R6_CI_ONLY:"1"})
        stdinEnabled: true
        onStarted: {
            if (root.startedSeen || root.phase !== "STARTING" || !processId
                || !root.current || phaseClock.elapsedMs()>=5000) {
                root.hold("START"); return;
            }
            root.startedSeen = true;
            root.originalPid = processId;
            if (!root.request("HELLO")) root.hold("HELLO");
        }
        stdout: SplitParser {
            splitMarker: ""
            onRead: function(data) {
                if (root.exitedSeen) { root.failure = "LATE_STDOUT"; return; }
                root.receiveChunk(data);
            }
        }
        stderr: SplitParser {
            splitMarker: ""
            onRead: function(data) {
                if (data.length) {
                    if (root.exitedSeen) root.failure = "LATE_STDERR";
                    else root.hold("STDERR");
                }
            }
        }
        onExited: function(code,exitStatus) { root.exitObserved(code,exitStatus); }
    }
    Timer {
        interval: 25
        repeat: true
        running: !root.reaped && root.phase !== "NEW"
        onTriggered: {
            if (root.exitedSeen) return;
            if (root.cleanupStarted) {
                const elapsed = cleanupClock.elapsedMs();
                if (elapsed >= 2000 && !root.killSent && worker.running
                    && (!root.startedSeen || worker.processId === root.originalPid)) {
                    root.killSent = true;
                    worker.signal(9);
                }
                if (elapsed >= 4000) {
                    root.failure = "UNREAPED";
                    root.phase = "HOLD";
                    stop(); root.finished(); // no reaped assertion or restart
                }
            } else if (trialClock.elapsedMs() >= 120000 || phaseClock.elapsedMs() >= 5000)
                root.hold("DEADLINE");
        }
    }
    Timer {
        id: settle
        interval: 100
        onTriggered: {
            if (worker.running || !root.exitedSeen) {
                root.failure = "UNREAPED";
                root.finished(); return;
            }
            root.reaped = true;
            root.phase = "REAPED";
            root.finished();
        }
    }
}
