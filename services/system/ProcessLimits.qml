import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: processLimits

    // RLIMIT_AS state and mutation queue. Safety/confirmation remains outside
    // this backend so callers must authorize the target before requesting a
    // limit change.
    // Compatibility property name; keys are exact process identities, never PID alone.
    // Only correlated, successfully observed kernel readbacks populate this map.
    property var softLimitPids: ({})
    property var queuedRequest: null
    property var activeRequest: null
    property bool applyLoading: false
    property int requestSerial: 0
    property string applyError: ""

    signal refreshRequested()

    property bool helperExited: false
    property bool stdoutDone: false
    property bool stderrDone: false
    property bool helperTimedOut: false
    property int helperExitCode: -1
    property int helperExitStatus: -1
    property string helperOutput: ""
    property string helperErrors: ""

    function identityKey(entry) {
        if (!entry || !Number.isSafeInteger(entry.pid) || entry.pid <= 1
                || !Number.isSafeInteger(entry.startTicks) || entry.startTicks <= 0
                || typeof entry.comm !== "string" || !entry.comm)
            return "";
        return JSON.stringify([entry.pid, entry.startTicks, entry.comm]);
    }

    function limitBytesFor(entry) {
        const key = identityKey(entry);
        return key && Object.prototype.hasOwnProperty.call(softLimitPids,key)
            ? softLimitPids[key] : 0;
    }

    function hasSoftLimit(entry) {
        const key = identityKey(entry);
        return !!key && Object.prototype.hasOwnProperty.call(softLimitPids,key);
    }

    function minimumMiB(entry) {
        if (!entry)
            return 128;

        // RLIMIT_AS below current VSZ is immediately hostile to the process.
        // Keep the slider's low end just above the current virtual footprint.
        return Math.max(
            128,
            Math.ceil(Number(entry.vsz || 0) / 1024) + 64
        );
    }

    function maximumMiB(entry) {
        const minimum = minimumMiB(entry);
        const stored = limitBytesFor(entry) / (1024 * 1024);

        return Math.max(
            8192,
            Math.ceil((minimum * 4) / 1024) * 1024,
            stored > 0 ? Math.ceil((stored * 1.25) / 1024) * 1024 : 0
        );
    }

    function limitMiB(entry) {
        const bytes = limitBytesFor(entry);
        return bytes > 0 ? bytes / (1024 * 1024) : 0;
    }

    function limitPercent(entry) {
        if (!entry || !hasSoftLimit(entry))
            return 100;

        const minMiB = minimumMiB(entry);
        const maxMiB = maximumMiB(entry);
        const current = Math.max(
            minMiB,
            Math.min(maxMiB, limitMiB(entry))
        );

        return Math.max(
            0,
            Math.min(
                98.5,
                ((current - minMiB) / Math.max(1, maxMiB - minMiB)) * 98.5
            )
        );
    }

    function setLimitMiB(entry, mib) {
        const key = identityKey(entry);
        if (!key || typeof mib !== "number" || !isFinite(mib) || mib < 0) {
            applyError = "INVALID PROCESS IDENTITY OR LIMIT";
            return false;
        }
        // One active and one queued request. Never silently overwrite an
        // accepted request, even if the next target shares a numeric PID.
        if (queuedRequest) {
            applyError = "LIMIT QUEUE FULL // REQUEST NOT ADMITTED";
            return false;
        }

        const minMiB = minimumMiB(entry);
        const maxMiB = maximumMiB(entry);
        let policyBytes = 0;
        if (mib < maxMiB * 0.995) {
            const capMiB = Math.max(minMiB, Math.min(maxMiB - 1, mib));
            policyBytes = Math.floor(capMiB * 1024 * 1024);
        }
        if (!Number.isSafeInteger(policyBytes) || policyBytes < 0) {
            applyError = "INVALID LIMIT BYTES";
            return false;
        }

        requestSerial += 1;
        queuedRequest = {
            serial: requestSerial,
            pid: entry.pid,
            startTicks: entry.startTicks,
            name: entry.comm,
            key: key,
            capBytes: policyBytes
        };
        startQueuedApply();
        return true;
    }

    function applyCommand(request) {
        const script = "import json, os, resource, select, sys\nreq=json.loads(sys.argv[1])\npid=req['pid']; born=req['startTicks']; name=req['name']; requested=req['capBytes']\nreply=dict(serial=req['serial'],pid=pid,startTicks=born,name=name,requested=requested,ok=False)\nfd=None\nattempted=False\ndef observe():\n    if poll.poll(0): raise RuntimeError('ORIGINAL PROCESS EXITED')\n    with open(f'/proc/{pid}/stat',encoding='utf-8') as source: data=source.read().strip()\n    end=data.rfind(')'); fields=data[end+2:].split()\n    if data[data.index('(')+1:end]!=name or int(fields[19])!=born or fields[0]=='Z':\n        raise RuntimeError('PROCESS IDENTITY CHANGED')\n    if poll.poll(0): raise RuntimeError('ORIGINAL PROCESS EXITED')\ntry:\n    if type(pid) is not int or pid<=1 or type(born) is not int or born<=0 or not isinstance(name,str) or not name or type(requested) is not int or requested<0:\n        raise ValueError('INVALID LIMIT REQUEST')\n    fd=os.pidfd_open(pid,0)\n    poll=select.poll(); poll.register(fd,select.POLLIN)\n    observe()\n    old_soft,hard=resource.prlimit(pid,resource.RLIMIT_AS)\n    target=hard if requested==0 else (requested if hard==resource.RLIM_INFINITY else min(requested,hard))\n    observe()\n    # prlimit has no pidfd variant. These checks narrow, not eliminate,\n    # the numeric-PID race. Never retry or assume success on ambiguity.\n    attempted=True\n    resource.prlimit(pid,resource.RLIMIT_AS,(target,hard))\n    observe()\n    soft,hard2=resource.prlimit(pid,resource.RLIMIT_AS)\n    observe()\n    if soft!=target or hard2!=hard: raise RuntimeError('LIMIT READBACK MISMATCH')\n    reply.update(ok=True,soft=-1 if soft==resource.RLIM_INFINITY else soft)\nexcept Exception as exc:\n    reply.update(error=str(exc),attempted=attempted)\nfinally:\n    if fd is not None: os.close(fd)\nprint(json.dumps(reply))\n";
        return ["/usr/bin/python3", "-c", script, JSON.stringify(request)];
    }

    function startQueuedApply() {
        if (applyLoading || !queuedRequest)
            return;
        activeRequest = queuedRequest;
        queuedRequest = null;
        applyLoading = true;
        applyError = "";
        helperExited = false;
        stdoutDone = false;
        stderrDone = false;
        helperTimedOut = false;
        helperExitCode = -1;
        helperExitStatus = -1;
        helperOutput = "";
        helperErrors = "";
        watchdog.restart();
        applyProcess.exec(applyCommand(activeRequest));
    }

    function validatedReply(request, output, errors, code, status, timedOut) {
        if (!request || timedOut || code !== 0 || status !== 0 || errors.trim())
            return null;
        try {
            const reply = JSON.parse(output);
            if (!reply || reply.serial !== request.serial || reply.pid !== request.pid
                    || reply.startTicks !== request.startTicks || reply.name !== request.name
                    || reply.requested !== request.capBytes || typeof reply.ok !== "boolean")
                return null;
            if (reply.ok && (!Number.isSafeInteger(reply.soft) || reply.soft < -1))
                return null;
            if (!reply.ok && (typeof reply.error !== "string" || typeof reply.attempted !== "boolean"))
                return null;
            return reply;
        } catch (error) {
            return null;
        }
    }

    function consumeApply(request, reply) {
        if (!request) return;
        const next = Object.assign({}, softLimitPids);
        if (reply && reply.ok) {
            if (reply.soft === -1)
                delete next[request.key];
            else
                next[request.key] = reply.soft;
            applyError = "";
        } else if (reply && !reply.attempted) {
            // No mutation attempted. Keep only the previous observed value.
            applyError = "LIMIT REFUSED // " + reply.error;
        } else {
            // A helper failure after possible mutation is not a rollback.
            // Forget the unverified value; never transfer it to another PID birth.
            delete next[request.key];
            applyError = "LIMIT OUTCOME UNKNOWN // VERIFY PROCESS STATE";
        }
        softLimitPids = next;
    }

    function maybeFinishApply() {
        if (!applyLoading || !helperExited || !stdoutDone || !stderrDone)
            return;
        watchdog.stop();
        const request = activeRequest;
        const reply = validatedReply(request, helperOutput, helperErrors,
            helperExitCode, helperExitStatus, helperTimedOut);
        consumeApply(request,reply);
        activeRequest = null;
        applyLoading = false;
        refreshRequested();
        Qt.callLater(function() { processLimits.startQueuedApply(); });
    }

    Process {
        id: applyProcess
        onExited: function(exitCode, exitStatus) {
            processLimits.helperExited = true;
            processLimits.helperExitCode = exitCode;
            processLimits.helperExitStatus = exitStatus;
            processLimits.maybeFinishApply();
        }
        stdout: StdioCollector {
            onStreamFinished: {
                processLimits.helperOutput = String(text || "");
                processLimits.stdoutDone = true;
                processLimits.maybeFinishApply();
            }
        }
        stderr: StdioCollector {
            onStreamFinished: {
                processLimits.helperErrors = String(text || "");
                processLimits.stderrDone = true;
                processLimits.maybeFinishApply();
            }
        }
    }

    Timer {
        id: watchdog
        interval: 10000
        repeat: false
        onTriggered: {
            processLimits.helperTimedOut = true;
            applyProcess.running = false;
            processLimits.maybeFinishApply();
        }
    }
}
