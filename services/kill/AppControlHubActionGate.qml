import QtQuick
import Quickshell
import Quickshell.Io
import "KillPriorityCustody.js" as Priority

// AppControl-owned bridge. Hub never receives ProcessControl, TaskSafety,
// ProcessLimits or raw ProcessTelemetry. Only explicit typed requests and
// read-only status are exposed. Each final action probes Linux PID birth time.
Scope {
    id: gate

    required property var ownerRows
    required property var safetyOwner
    required property var presentationOwner
    required property var controlOwner
    required property var limitsOwner
    required property var refreshOwner

    property bool bulkBlocked: false
    property var pending: null
    property bool busy: false
    property string feedback: ""
    property string probeReply: ""
    property bool probeExited: false
    property bool probeStdoutDone: false
    property int probeExitStatus: -1
    property int limitDispatchSerial: 0
    property int probeExitCode: -1

    // Same shared action gate owns both the baseline and subprocess lifecycle.
    // No UI admission is enabled until restoration lifetime is qualified.
    property var priorityRecords: ({})
    property var priorityRequest: null
    property int prioritySerial: 0
    property bool priorityExited: false
    property bool priorityOutDone: false
    property bool priorityErrDone: false
    property bool priorityTimedOut: false
    property int priorityExitCode: -1
    property int priorityExitStatus: -1
    property string priorityOutput: ""
    property string priorityErrors: ""

    function priorityRecordFor(pid,birth,name) {
        return priorityRecords[Priority.key(pid,birth,name)] || null;
    }
    function priorityEligible(pid,birth,name) {
        const row=exactRow(pid,birth,name);
        // Initial lane never permits protected targets, even if unlocked.
        return !!row && !safetyOwner.requiresDangerUnlock(row)
            && !bulkBlocked && !limitsOwner.applyLoading && !limitsOwner.queuedRequest;
    }
    function capturePriority(pid,birth,name) {
        if (busy || pending || !priorityEligible(pid,birth,name)) return false;
        const record=priorityRecordFor(pid,birth,name);
        if (record && record.state==="unknown") return false;
        return startPriority({pid:pid,startTicks:birth,comm:name,operation:"capture"});
    }
    function preparePriority(pid,birth,name,operation,target) {
        if (busy || pending || !priorityEligible(pid,birth,name)) return false;
        const plan=Priority.request(priorityRecordFor(pid,birth,name),operation,target);
        if (!plan) {
            feedback="PRIORITY BASELINE OR REVERSIBILITY UNAVAILABLE // REFUSED";
            return false;
        }
        pending=Object.assign({pid:pid,startTicks:birth,name:name,action:"priority"},plan);
        feedback="REVIEW AND CONFIRM PRIORITY // NOT EXECUTED";
        return true;
    }
    function confirmPriority(req) {
        if (!priorityEligible(req.pid,req.startTicks,req.name)) {
            finishRequest("PRIORITY TARGET OR SAFETY STATE CHANGED // REFUSED");
            return false;
        }
        const plan=Priority.request(priorityRecordFor(req.pid,req.startTicks,req.name),req.operation,req.target);
        if (!plan || plan.original!==req.original || !Priority.equal(plan.expectedSnapshot,req.expectedSnapshot)) {
            finishRequest("PRIORITY BASELINE CHANGED // REFUSED");
            return false;
        }
        if (!startPriority(Object.assign({pid:req.pid,startTicks:req.startTicks,comm:req.name},plan))) {
            finishRequest("PRIORITY HELPER UNAVAILABLE // NO ACTION");
            return false;
        }
        return true;
    }
    function startPriority(plan) {
        if (busy || priorityRequest) return false;
        const url=String(Qt.resolvedUrl("priority_control.py"));
        if (!url.startsWith("file:///")) return false;
        let path;
        try { path=decodeURIComponent(url.slice(7)); } catch(error) { return false; }
        priorityRequest=Object.assign({},plan,{serial:++prioritySerial});
        priorityExited=false; priorityOutDone=false; priorityErrDone=false;
        priorityTimedOut=false; priorityExitCode=-1; priorityExitStatus=-1;
        priorityOutput=""; priorityErrors="";
        busy=true;
        feedback=plan.operation==="capture" ? "PRIORITY // CAPTURING ORIGINAL"
            : "PRIORITY // VERIFYING KERNEL RESULT";
        priorityWatchdog.restart();
        priorityProcess.exec(["/usr/bin/python3","-B",path,"--request",JSON.stringify(priorityRequest)]);
        return true;
    }
    function finishPriority() {
        if (!priorityRequest || !priorityExited || !priorityOutDone || !priorityErrDone) return;
        priorityWatchdog.stop();
        const req=priorityRequest;
        const k=Priority.key(req.pid,req.startTicks,req.comm);
        const prior=priorityRecords[k] || null;
        const valid=!priorityTimedOut && priorityExitCode===0 && priorityExitStatus===0 && !priorityErrors.trim();
        const record=Priority.consume(prior,req,valid ? priorityOutput : null);
        priorityRecords=Object.assign({},priorityRecords,{[k]:record});
        priorityRequest=null;
        finishRequest(record.state==="unknown" ? "PRIORITY OUTCOME OR OWNERSHIP UNKNOWN // NO RETRY"
            : record.state==="unavailable" ? "PRIORITY EVIDENCE UNAVAILABLE // REFUSED"
            : req.operation==="capture" ? "PRIORITY // ORIGINAL OBSERVED"
            : "PRIORITY // KERNEL READBACK VERIFIED");
        if (req.operation!=="capture") refreshOwner.restart();
    }
    Timer {
        id: priorityWatchdog
        interval: 5000
        repeat: false
        onTriggered: {
            gate.priorityTimedOut=true;
            gate.feedback="PRIORITY TIMEOUT // DRAINING";
            priorityProcess.running=false;
            gate.finishPriority();
        }
    }
    Process {
        id: priorityProcess
        stdout: StdioCollector {
            onStreamFinished: {
                gate.priorityOutput=String(text || "");
                gate.priorityOutDone=true;
                gate.finishPriority();
            }
        }
        stderr: StdioCollector {
            onStreamFinished: {
                gate.priorityErrors=String(text || "");
                gate.priorityErrDone=true;
                gate.finishPriority();
            }
        }
        onExited: function(code,status) {
            gate.priorityExitCode=code;
            gate.priorityExitStatus=status;
            gate.priorityExited=true;
            gate.finishPriority();
        }
    }

    function exactRow(pid, startTicks, name) {
        if (!Array.isArray(ownerRows) || !Number.isSafeInteger(pid)
                || pid <= 1 || !Number.isSafeInteger(startTicks)
                || startTicks <= 0 || typeof name !== "string" || !name)
            return null;
        for (let i = 0; i < ownerRows.length; i++) {
            const row = ownerRows[i];
            if (!row || row._taskRecord !== true)
                continue;
            if (row.pid === pid && row.startTicks === startTicks
                    && String(row.comm || "") === name)
                return row;
        }
        return null;
    }

    function isProtected(pid, startTicks, name) {
        const row = exactRow(pid, startTicks, name);
        return row ? safetyOwner.requiresDangerUnlock(row) : true;
    }

    function actionLockKind(action) {
        if (action === "freeze" || action === "resume") return "freeze";
        if (action === "restart") return "restart";
        if (action === "limit") return "limit";
        if (action === "end" || action === "kill") return "kill";
        return "";
    }

    function isUnlocked(pid, startTicks, name, action) {
        const row = exactRow(pid, startTicks, name);
        if (!row) return false;
        if (!safetyOwner.requiresDangerUnlock(row)) return true;
        const kind = actionLockKind(action);
        if (!kind) return false;
        return safetyOwner.dangerActionUnlocked(row, kind);
    }

    function currentLimitPercent(pid, startTicks, name) {
        const row = exactRow(pid, startTicks, name);
        return row ? Math.round(presentationOwner.limitPercent(row)) : 100;
    }

    function currentLimitStatus(pid, startTicks, name) {
        const row = exactRow(pid,startTicks,name);
        return row ? presentationOwner.limitResultFor(row).message : "LIMIT IDENTITY UNAVAILABLE";
    }

    function prepareLimitMiB(pid, startTicks, name, mib) {
        if (typeof mib !== "number" || !isFinite(mib) || mib <= 0)
            return false;
        if (!prepare(pid,startTicks,name,"limit",0))
            return false;
        pending = Object.assign({},pending,{mib:mib});
        return true;
    }

    function toggleOneShotUnlock(pid, startTicks, name) {
        const row = exactRow(pid, startTicks, name);
        if (!row || busy || pending || bulkBlocked || !safetyOwner.requiresDangerUnlock(row))
            return false;
        safetyOwner.toggleDangerUnlock(row); // existing AppControl safety state
        feedback = safetyOwner.dangerUnlocked(row)
                   ? "PROTECTED TARGET // UNLOCKED ONCE"
                   : "PROTECTED TARGET // LOCKED";
        return true;
    }

    function prepare(pid, startTicks, name, action, percent) {
        if (busy || pending || bulkBlocked) { feedback = "AN ACTION IS ALREADY PENDING"; return false; }
        const row = exactRow(pid, startTicks, name);
        if (!row) { feedback = "STALE PROCESS IDENTITY // SELECT AGAIN"; return false; }
        if (["freeze","resume","end","restart","limit"].indexOf(action) === -1) {
            feedback = "UNSUPPORTED ACTION"; return false;
        }
        if (action === "limit" && (limitsOwner.applyLoading || limitsOwner.queuedRequest
                || limitsOwner.limitStateFor(row) === "unknown")) {
            feedback = "LIMIT BUSY OR OWNERSHIP UNKNOWN // REFUSED";
            return false;
        }
        if (action === "limit"
                && (typeof percent !== "number" || !isFinite(percent)
                    || percent < 0 || percent > 100)) {
            feedback = "INVALID LIMIT"; return false;
        }
        if (action === "freeze" && presentationOwner.isFrozen(row)) {
            feedback = "ALREADY STOPPED"; return false;
        }
        if (action === "resume" && !presentationOwner.isFrozen(row)) {
            feedback = "NOT STOPPED"; return false;
        }
        const key = actionLockKind(action);
        if (safetyOwner.requiresDangerUnlock(row)
                && !safetyOwner.dangerActionUnlocked(row, key)) {
            feedback = "PROTECTED PROCESS // UNLOCK ONCE FIRST"; return false;
        }
        pending = {pid:pid,startTicks:startTicks,name:name,action:action,
                   percent:action === "limit" ? Math.round(percent) : 0};
        feedback = "REVIEW AND CONFIRM // NOT EXECUTED";
        return true;
    }

    function cancel() {
        if (busy) return false;
        if (pending) {
            const row = exactRow(pending.pid,pending.startTicks,pending.name);
            if (row && pending.action!=="priority")
                safetyOwner.relockDangerAction(row,
                    actionLockKind(pending.action));
        }
        pending = null;
        feedback = "CANCELLED // NO ACTION";
        return true;
    }

    function confirm() {
        if (!pending || busy || bulkBlocked) return false;
        const req = pending;
        const row = exactRow(req.pid,req.startTicks,req.name);
        if (!row) { pending=null; feedback="PROCESS CHANGED // REFUSED"; return false; }
        if (req.action==="priority") return confirmPriority(req);
        const kind = actionLockKind(req.action);
        if (!kind) { pending=null; feedback="UNSUPPORTED ACTION"; return false; }
        if (safetyOwner.requiresDangerUnlock(row)
                && !safetyOwner.dangerActionUnlocked(row,kind)) {
            pending=null; feedback="SAFETY LOCK RE-ENGAGED // REFUSED"; return false;
        }
        probeReply = "";
        probeExited = false;
        probeStdoutDone = false;
        probeExitStatus = -1;
        probeExitCode = -1;
        busy = true;
        feedback = "VERIFYING PROCESS START IDENTITY";
        identityProbe.exec([
            "/usr/bin/python3", "-c",
            "import sys\n"
            + "pid=int(sys.argv[1]); born=int(sys.argv[2]); comm=sys.argv[3]\n"
            + "try:\n"
            + " data=open('/proc/%d/stat'%pid,encoding='utf-8').read().strip()\n"
            + " pos=data.rfind(')'); actual=data[data.index('(')+1:pos]\n"
            + " fields=data[pos+2:].split()\n"
            + " print('MATCH' if actual==comm and int(fields[19])==born else 'STALE')\n"
            + "except Exception: print('STALE')\n",
            String(req.pid), String(req.startTicks), req.name
        ]);
        return true;
    }

    function maybeFinishProbe() {
        if (busy && !signalDispatchActive && !limitDispatchSerial && probeExited && probeStdoutDone) {
            probeExited = false;
            finishProbe(probeExitStatus === 0 ? probeExitCode : -1);
        }
    }

    function finishProbe(exitCode) {
        const req = pending;
        if (!req || exitCode !== 0 || probeReply.trim() !== "MATCH") {
            finishRequest("PROCESS IDENTITY NOT VERIFIED // NO ACTION");
            return;
        }
        const row = exactRow(req.pid,req.startTicks,req.name);
        if (!row || bulkBlocked) {
            finishRequest("PROCESS OR ACTION STATE CHANGED // REFUSED");
            return;
        }
        const kind = actionLockKind(req.action);
        if (!kind || (safetyOwner.requiresDangerUnlock(row)
                && !safetyOwner.dangerActionUnlocked(row,kind))) {
            finishRequest("SAFETY LOCK LOST // REFUSED");
            return;
        }
        if (req.action === "freeze" || req.action === "resume" || req.action === "end") {
            if (req.action === "freeze" && presentationOwner.isFrozen(row)) {
                finishRequest("ALREADY STOPPED"); return;
            }
            if (req.action === "resume" && !presentationOwner.isFrozen(row)) {
                finishRequest("NOT STOPPED"); return;
            }
            const sig = req.action === "freeze" ? "-STOP" : req.action === "resume" ? "-CONT" : "-TERM";
            const command = controlOwner.identitySignalCommand(req.pid,req.startTicks,req.name,sig);
            if (!command.length) { finishRequest("REQUEST REJECTED"); return; }
            safetyOwner.relockDangerAction(row,kind);
            signalDispatchActive = true;
            feedback = "DISPATCHING IDENTITY-BOUND SIGNAL";
            signalDispatch.exec(command);
            return;
        }
        if (req.action === "restart") {
            const command = controlOwner.identityRestartCommand(req.pid,req.startTicks,req.name);
            if (!command.length) { finishRequest("REQUEST REJECTED"); return; }
            safetyOwner.relockDangerAction(row,kind);
            signalDispatchActive = true;
            feedback = "RESTART // WAITING FOR ORIGINAL EXIT";
            signalDispatch.exec(command);
            return;
        }
        if (req.action === "limit") {
            if (limitsOwner.applyLoading || limitsOwner.queuedRequest
                    || limitsOwner.limitStateFor(row) === "unknown") {
                safetyOwner.relockDangerAction(row,kind);
                finishRequest("LIMIT BUSY OR OWNERSHIP UNKNOWN // REFUSED");
                return;
            }
            limitDispatchSerial = limitsOwner.requestSerial + 1;
            feedback = "LIMIT // VERIFYING KERNEL RESULT";
            const admitted = req.mib !== undefined
                ? presentationOwner.setLimitMiB(req.mib,row,gate)
                : presentationOwner.setLimitPercent(req.percent,row,gate);
            safetyOwner.relockDangerAction(row,kind);
            if (!admitted) {
                limitDispatchSerial = 0;
                finishRequest("LIMIT REQUEST REFUSED // " + limitsOwner.applyError);
            }
            return;
        }
        finishRequest("UNSUPPORTED ACTION // REFUSED");
    }

    property bool signalDispatchActive: false

    function finishLimit(result) {
        const req = pending;
        if (!busy || !limitDispatchSerial || !req || req.action !== "limit" || !result
                || result.serial !== limitDispatchSerial || result.pid !== req.pid
                || result.startTicks !== req.startTicks || result.name !== req.name)
            return false;
        limitDispatchSerial = 0;
        finishRequest(result.message);
        refreshOwner.restart();
        return true;
    }

    Connections {
        target: gate.limitsOwner
        function onLimitCompleted(result) { gate.finishLimit(result); }
    }

    function finishRequest(message) {
        feedback = message;
        pending = null;
        busy = false;
    }

    function finishSignal(exitCode, exitStatus) {
        if (!signalDispatchActive) return;
        signalDispatchActive = false;
        const req = pending;
        if (req && req.action === "restart") {
            if (exitStatus !== 0)
                finishRequest("RESTART OUTCOME UNKNOWN // VERIFY OWNER STATE");
            else if (exitCode === 0)
                finishRequest("RESTART // ORIGINAL EXIT OBSERVED // LAUNCH ACCEPTED");
            else if (exitCode === 2)
                finishRequest("RESTART CAPTURE REFUSED // NO SIGNAL");
            else if (exitCode === 3)
                finishRequest("RESTART TIMEOUT // NO REPLACEMENT LAUNCHED");
            else if (exitCode === 4)
                finishRequest("ORIGINAL EXITED // REPLACEMENT LAUNCH FAILED");
            else if (exitCode === 5)
                finishRequest("RESTART SIGNAL REFUSED // NO REPLACEMENT LAUNCHED");
            else
                finishRequest("RESTART OUTCOME UNKNOWN // VERIFY OWNER STATE");
            refreshOwner.restart();
            return;
        }
        if (req && exitCode === 0 && exitStatus === 0) {
            const row = exactRow(req.pid,req.startTicks,req.name);
            if (row && (req.action === "freeze" || req.action === "resume"))
                presentationOwner.markFrozen(row,req.action === "freeze");
            finishRequest(req.action.toUpperCase() + " // SIGNAL ACCEPTED // VERIFY OWNER STATE");
        } else {
            finishRequest("SIGNAL FAILED OR TARGET CHANGED // VERIFY OWNER STATE");
        }
        refreshOwner.restart();
    }

    Process {
        id: signalDispatch
        onExited: function(exitCode, exitStatus) {
            gate.finishSignal(exitCode, exitStatus);
        }
    }

    Process {
        id: identityProbe
        stdout: StdioCollector {
            onStreamFinished: {
                gate.probeReply = String(text || "");
                gate.probeStdoutDone = true;
                gate.maybeFinishProbe();
            }
        }
        onExited: function(exitCode, exitStatus) {
            gate.probeExited = true;
            gate.probeExitCode = exitCode;
            gate.probeExitStatus = exitStatus;
            gate.maybeFinishProbe();
        }
    }
}
