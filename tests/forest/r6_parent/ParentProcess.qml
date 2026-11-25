import QtQuick
import Quickshell
import Quickshell.Io
import "ParentWire.js" as Wire
import "PublicRuntimeStatusDisplay.js" as Status
import "PublicHistoryDisplay.js" as History

// CI-only native exchange; optional actual ForestW Loader consumer.
// Never an installed connection.
// One instance owns one tracked Process for its entire lifetime.
Item {
    id: root
    required property string trial
    required property string fixtureDirectory
    required property var originalOwner
    property var observedOwner: null
    property bool joined: false
    property var originalLoader: null
    property bool reopenReady: false
    property bool historyConfirmed: false
    property int positiveHistoryAcks: 0
    property int negativeHistoryAcks: 0
    property bool eligible: false
    property bool acceptOffer: false
    readonly property bool current: eligible && originalOwner !== null
        && observedOwner === originalOwner
        && (!joined || (originalLoader !== null && originalLoader.active
            && originalLoader.visible && originalLoader.item === originalOwner
            && originalOwner.visible))
    property var wire: null
    property string phase: "NEW"
    property int action: 0
    property string pending: ""
    property bool offered: false
    property var ref: null
    property var used: []
    property var historyController: null
    property var historyScope: null
    property var historyDisplay: null
    property var pageRequest: null
    property int historyGeneration: 0
    property string sessionAlias: ""
    property int sequence: 0
    property bool stopRequested: false
    property int turnsStarted: 0
    property int turnSteps: 0
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
        if (joined) {
            if (!originalOwner.beginConnectedHistory()) return false;
        } else historyController = History.createController();
        phase = "STARTING";
        trialClock.restartMs();
        phaseClock.restartMs();
        worker.running = true;
        return true;
    }
    function clearHistory(touchView = true) {
        // Retire local custody first. QML item destruction can invalidate a
        // wrapper before it compares equal to null.
        const scope = historyScope;
        historyConfirmed = false;
        historyScope = null;
        pageRequest = null;
        historyDisplay = historyController ? historyController.close() : null;
        if (touchView && joined && current && scope) {
            const view = originalOwner;
            const observed = view.historyCurrentScope;
            if (observed && Object.keys(scope).every(k=>scope[k]===observed[k])
                && current && originalOwner===view)
                view.historyCurrentScope = null;
        }
    }
    function clearOriginal(touchView = true) {
        const oldRef = ref;
        ref = null;
        sequence = 0;
        status = "";
        clearHistory(touchView);
        if (touchView && joined && current && oldRef) {
            const view = originalOwner;
            if (Status.same(Status.correlation(oldRef),Status.correlation(view.runtimeCurrentCorrelation))
                && current && originalOwner===view) {
                view.runtimeViewOpen = false;
                if (current && originalOwner===view)
                    view.runtimeCurrentCorrelation = null;
            }
        }
    }
    function hold(reason) {
        if (reaped || cleanupStarted) return;
        failure = reason; // fixed local labels only
        outcome = possibleEffect ? "UNKNOWN_HOLD" : "REFUSED";
        // Fence reentrant callbacks and arm process cleanup independently
        // of the visual item. Never dereference a lost Loader item.
        cleanupStarted = true;
        cleanupClock.restartMs();
        pending = "";
        phase = "HOLD";
        if (wire) wire.stop();
        try {
            clearOriginal(reason !== "OWNER_LOST" && current);
        } finally {
            if (worker.running && (!startedSeen || worker.processId === originalPid))
                worker.signal(15);
        }
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
    function request(kind, pageId, limit) {
        if (!live() || pending || action >= Wire.ACTIONS) return false;
        let data = {};
        if (kind === "HELLO") {
            if (phase !== "STARTING" || action !== 0) return false;
        } else if (kind === "NEXT") {
            if (phase !== "IDLE" || turnsStarted >= 3) return false;
            clearOriginal();
            stopRequested = false;
            reopenReady = false;
            turnSteps = 0;
        } else if (kind === "STEP" || kind === "STOP") {
            if (phase !== "ACTIVE" || ref === null) return false;
            if (kind === "STOP" && (stopRequested || turnSteps < 4)) return false;
            // Third fixed public turn is STOP-only, never allow sixth row.
            if (kind === "STEP" && turnsStarted === 3 && turnSteps >= 4
                && !stopRequested) return false;
            data = {ref:ref};
        } else if (kind === "REOPEN") {
            if (phase !== "IDLE" || !reopenReady) return false;
            clearOriginal();
            reopenReady = false;
        } else if (kind === "HISTORY_ATTACH") {
            if (phase !== "IDLE") return false;
            clearHistory();
        } else if (kind === "HISTORY_PAGE") {
            if (phase !== "IDLE" || !historyConfirmed || historyScope === null || !Wire.token(pageId)
                || pageId === trial || used.indexOf(pageId)>=0 || pageId === sessionAlias
                || used.length >= 128 || !Wire.integer(limit,1,2)) return false;
            if (joined) {
                if (!originalOwner.historyScopeActive || !live()) return false;
                const state = originalOwner.fixtureState;
                if (state !== "CLOSED" && state !== "PARTIAL") return false;
                const ok = state === "PARTIAL"
                    ? originalOwner.nextHistoryPage(historyScope,pageId,limit)
                    : originalOwner.openHistoryPage(historyScope,pageId,limit);
                if (!ok || !live() || !originalOwner.historyPendingRequest) {
                    hold("HISTORY_REQUEST"); return false;
                }
                pageRequest = originalOwner.historyPendingRequest;
            } else {
                if (historyDisplay && historyDisplay.state === "COMPLETE") return false;
                const d = historyDisplay && historyDisplay.state === "PARTIAL"
                    ? historyController.next(historyScope,pageId,limit)
                    : historyController.open(historyScope,pageId,limit);
                if (d.state !== "PENDING" || !d.request) { hold("HISTORY_REQUEST"); return false; }
                pageRequest = d.request;
                historyDisplay = d;
            }
            used = used.concat([pageId]);
            data = {scope:historyScope,request:pageRequest};
        } else if (kind === "CLOSE") {
            if (phase !== "IDLE" && phase !== "ACTIVE" && phase !== "BLOCKED")
                return false;
            clearOriginal();
        } else return false;
        if (!wire.reserve(kind === "NEXT" || kind === "HISTORY_ATTACH")) { hold("RESERVE"); return false; }
        action++;
        pending = kind;
        offered = false;
        phaseClock.restartMs();
        // ACK/STEP/CLOSE writes may race effects; never infer rollback.
        if (kind === "STEP" || kind === "STOP" || kind === "CLOSE" || kind === "REOPEN") possibleEffect = true;
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
                || data.ref.requestId === trial || data.ref.viewKey === trial || data.ref.requestId === sessionAlias || data.ref.viewKey === sessionAlias
                || used.indexOf(data.ref.requestId)>=0 || used.indexOf(data.ref.viewKey)>=0)
                return false;
            offered = true;
            // Independent owner eligibility/decision, never supplied by frame.
            let accepted = current && acceptOffer;
            if (accepted) {
                ref = {requestId:data.ref.requestId,viewKey:data.ref.viewKey,
                    generation:data.ref.generation};
                used = used.concat([ref.requestId,ref.viewKey]);
                if (joined) {
                    originalOwner.runtimeTreeKey = "CHERRY";
                    originalOwner.runtimeCurrentCorrelation = ref;
                    originalOwner.runtimeViewOpen = true;
                    accepted = live() && originalOwner.runtimeInitialized
                        && originalOwner.openRuntimeLifetime(ref) && live();
                    if (!accepted) clearOriginal();
                }
                if (accepted) possibleEffect = true;
            }
            return send("OPEN_ACK",{ref:data.ref,accepted:accepted});
        }
        if (frame.kind === "HISTORY_OFFER") {
            const v = data.scope;
            if (pending !== "HISTORY_ATTACH" || offered || !Wire.exact(data,["scope"])
                || !Wire.exact(v,["treeKey","generation","sessionId","revision","viewKey"])
                || v.treeKey !== "CHERRY" || !Wire.integer(v.generation,1,Number.MAX_SAFE_INTEGER)
                || v.generation !== historyGeneration+1 || v.revision !== turnsStarted*2
                || !Wire.token(v.sessionId) || !Wire.token(v.viewKey)
                || v.sessionId === v.viewKey || v.sessionId === trial || v.viewKey === trial
                || used.indexOf(v.viewKey)>=0 || used.indexOf(v.sessionId)>=0
                || (sessionAlias && v.sessionId !== sessionAlias) || used.length>=128) return false;
            offered = true;
            let accepted = live() && acceptOffer;
            if (accepted) {
                historyScope = Object.assign({},v);
                if (joined) {
                    // The actual original consumer must accept before a positive ACK.
                    originalOwner.historyCurrentScope = historyScope;
                    accepted = live() && historyScope !== null
                        && originalOwner.attachHistoryScope(historyScope)
                        && live() && originalOwner.historyScopeActive
                        && originalOwner.sameHistoryScope(historyScope,originalOwner.historyCurrentScope);
                }
                if (accepted) {
                    historyGeneration = v.generation;
                    sessionAlias = v.sessionId;
                    used = used.concat([v.viewKey]);
                } else clearHistory(current);
            }
            if (!live()) return false;
            if (!send("HISTORY_ACK",{scope:v,accepted:accepted})) return false;
            if (accepted) positiveHistoryAcks++;
            else negativeHistoryAcks++;
            return true;
        }
        if (frame.kind === "PAGE") {
            if (pending !== "HISTORY_PAGE" || !historyConfirmed || !pageRequest || !historyScope
                || !Wire.exact(data,["scope","page"])
                || !Wire.exact(data.scope,Object.keys(historyScope))
                || !Object.keys(historyScope).every(k=>data.scope[k]===historyScope[k])) return false;
            const projected = History.project(data.page,pageRequest,pageRequest);
            if (projected.state !== "STRUCTURALLY_VALID_PUBLIC_FIXTURE"
                || projected.messages.some(r=>!Wire.token(r.turnId) || r.turnId===trial
                    || r.turnId===sessionAlias || used.indexOf(r.turnId)>=0)
                || projected.complete !== (pageRequest.after+projected.messages.length===historyScope.revision)
                || !live()) return false;
            if (joined) {
                if (!originalOwner.historyScopeActive
                    || !originalOwner.receiveHistoryPage(historyScope,data.page)
                    || !live() || originalOwner.fixtureState !== (projected.complete ? "COMPLETE" : "PARTIAL"))
                    return false;
            } else {
                const d = historyController.receive(data.page,historyScope);
                if (d.state !== "PARTIAL" && d.state !== "COMPLETE") return false;
                historyDisplay = d;
            }
            pageRequest = null;
            pending = "";
            actionFinished("PAGE_READY");
            return true;
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
        else if (pending === "HISTORY_ATTACH" && offered && historyScope !== null
                && code === "HISTORY_ATTACHED" && !data.units.length) {
            if (joined && (!live() || !originalOwner.historyScopeActive
                || !originalOwner.sameHistoryScope(historyScope,originalOwner.historyCurrentScope))) return false;
            historyConfirmed = true;
            next = "IDLE";
        } else if (pending === "REOPEN" && code === "JOURNAL_REOPENED" && !data.units.length)
            next = "IDLE";
        else if (pending === "NEXT" && offered && ref !== null
                && code === "TURN_STARTED" && !data.units.length) {
            turnsStarted++;
            next = "ACTIVE";
        } else if (pending === "STOP" && !stopRequested && code === "STOP_OBSERVED") {
            batch = prevalidateUnits(data.units);
            if (!batch || batch.status !== "STOP_REQUESTED") return false;
            stopRequested = true;
            next = "ACTIVE";
        } else if (pending === "STEP" && ["ACTIVE","COMMITTED_LOCAL","ABORTED_LOCAL","UNKNOWN_HOLD"].indexOf(code)>=0) {
            batch = prevalidateUnits(data.units);
            if (!batch) return false;
            if ((code === "ACTIVE" && ["LOCAL_COMMIT_RECORDED","UNKNOWN_HOLD"].indexOf(batch.status)>=0)
                || (code === "COMMITTED_LOCAL" && batch.status !== "LOCAL_COMMIT_RECORDED")
                || ((code === "ABORTED_LOCAL" || code === "UNKNOWN_HOLD")
                    && batch.status === "LOCAL_COMMIT_RECORDED")) return false;
            if (code === "ABORTED_LOCAL" && !stopRequested) return false;
            if (turnsStarted === 3 && code === "COMMITTED_LOCAL") return false;
            turnSteps++;
            if (code === "COMMITTED_LOCAL") reopenReady = true;
            next = code === "ACTIVE" ? "ACTIVE" : code === "COMMITTED_LOCAL" ? "IDLE" : "BLOCKED";
        } else if (pending === "CLOSE" && code === "CLOSED" && !data.units.length) {
            next = "CLOSE_EXIT";
            closeResult = true;
        } else return false;
        // Whole batch validated before any actual consumer call.
        if (batch) {
            if (!live()) return false;
            if (joined) for (const unit of data.units) {
                if (!live() || !originalOwner.runtimeEligible
                    || !Status.same(Status.correlation(ref),Status.correlation(originalOwner.runtimeCurrentCorrelation)))
                    return false;
                originalOwner.receiveRuntimeUnit(unit);
                if (!live() || originalOwner.runtimeState !== "DISPLAYING") return false;
            }
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
        // Exit/reap must not depend on the destroyed view.
        try {
            clearOriginal(!cleanupStarted && current);
        } finally {
            phase = "EXIT_SEEN";
            settle.restart();
        }
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
