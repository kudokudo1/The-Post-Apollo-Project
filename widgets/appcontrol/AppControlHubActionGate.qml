import QtQuick
import Quickshell
import Quickshell.Io

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

    property var pending: null
    property bool busy: false
    property string feedback: ""
    property string probeReply: ""

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

    function isUnlocked(pid, startTicks, name, action) {
        const row = exactRow(pid, startTicks, name);
        if (!row) return false;
        if (!safetyOwner.requiresDangerUnlock(row)) return true;
        const kind = action === "freeze" || action === "resume" ? "freeze"
                     : action === "limit" ? "limit" : "kill";
        return safetyOwner.dangerActionUnlocked(row, kind);
    }

    function currentLimitPercent(pid, startTicks, name) {
        const row = exactRow(pid, startTicks, name);
        return row ? Math.round(presentationOwner.limitPercent(row)) : 100;
    }

    function toggleOneShotUnlock(pid, startTicks, name) {
        const row = exactRow(pid, startTicks, name);
        if (!row || busy || pending || !safetyOwner.requiresDangerUnlock(row))
            return false;
        safetyOwner.toggleDangerUnlock(row); // existing AppControl safety state
        feedback = safetyOwner.dangerUnlocked(row)
                   ? "PROTECTED TARGET // UNLOCKED ONCE"
                   : "PROTECTED TARGET // LOCKED";
        return true;
    }

    function prepare(pid, startTicks, name, action, percent) {
        if (busy || pending) { feedback = "AN ACTION IS ALREADY PENDING"; return false; }
        const row = exactRow(pid, startTicks, name);
        if (!row) { feedback = "STALE PROCESS IDENTITY // SELECT AGAIN"; return false; }
        if (["freeze","resume","end","restart","limit"].indexOf(action) === -1) {
            feedback = "UNSUPPORTED ACTION"; return false;
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
        const key = action === "freeze" || action === "resume"
                    ? "freeze" : action === "limit" ? "limit" : "kill";
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
            if (row)
                safetyOwner.relockDangerAction(row,
                    pending.action === "freeze" || pending.action === "resume"
                    ? "freeze" : pending.action === "limit" ? "limit" : "kill");
        }
        pending = null;
        feedback = "CANCELLED // NO ACTION";
        return true;
    }

    function confirm() {
        if (!pending || busy) return false;
        const req = pending;
        const row = exactRow(req.pid,req.startTicks,req.name);
        if (!row) { pending=null; feedback="PROCESS CHANGED // REFUSED"; return false; }
        const kind = req.action === "freeze" || req.action === "resume" ? "freeze"
                     : req.action === "limit" ? "limit" : "kill";
        if (safetyOwner.requiresDangerUnlock(row)
                && !safetyOwner.dangerActionUnlocked(row,kind)) {
            pending=null; feedback="SAFETY LOCK RE-ENGAGED // REFUSED"; return false;
        }
        probeReply = "";
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

    function finishProbe(exitCode) {
        const req = pending;
        busy = false;
        pending = null;
        if (!req || exitCode !== 0 || probeReply.trim() !== "MATCH") {
            feedback = "PROCESS IDENTITY NOT VERIFIED // NO ACTION";
            return;
        }
        const row = exactRow(req.pid,req.startTicks,req.name);
        if (!row) { feedback="PROCESS CHANGED SINCE VERIFICATION // REFUSED"; return; }
        const kind = req.action === "freeze" || req.action === "resume" ? "freeze"
                     : req.action === "limit" ? "limit" : "kill";
        if (safetyOwner.requiresDangerUnlock(row)
                && !safetyOwner.dangerActionUnlocked(row,kind)) {
            feedback="SAFETY LOCK LOST // REFUSED"; return;
        }
        // Existing AppControl owners dispatch every change. No new
        // kill/prlimit backend. Detached commands are requests, not proof.
        if (req.action === "freeze") {
            if (presentationOwner.isFrozen(row)) { feedback="ALREADY STOPPED"; return; }
            if (!controlOwner.sendSignal(req.pid,"-STOP")) { feedback="REQUEST REJECTED"; return; }
            presentationOwner.markFrozen(row,true);
        } else if (req.action === "resume") {
            if (!presentationOwner.isFrozen(row)) { feedback="NOT STOPPED"; return; }
            if (!controlOwner.sendSignal(req.pid,"-CONT")) { feedback="REQUEST REJECTED"; return; }
            presentationOwner.markFrozen(row,false);
        } else if (req.action === "end") {
            if (!controlOwner.sendSignal(req.pid,"-TERM")) { feedback="REQUEST REJECTED"; return; }
        } else if (req.action === "restart") {
            if (!controlOwner.restart(req.pid)) { feedback="REQUEST REJECTED"; return; }
        } else if (req.action === "limit") {
            presentationOwner.setLimitPercent(req.percent,row);
        }
        safetyOwner.relockDangerAction(row,kind);
        feedback = req.action.toUpperCase() + " // REQUEST ISSUED // VERIFY OWNER STATE";
        refreshOwner.restart();
    }

    Process {
        id: identityProbe
        stdout: StdioCollector {
            onStreamFinished: gate.probeReply = String(text || "")
        }
        onExited: function(exitCode, exitStatus) {
            gate.finishProbe(exitCode);
        }
    }
}
