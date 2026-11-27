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
    // Session-only ownership; original kernel values remain exact decimal strings.
    // Uncertain entries block further writes until independently reconciled.
    property var limitOwnership: ({})
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

    function limitStateFor(entry) {
        const key = identityKey(entry);
        const owned = key ? limitOwnership[key] : null;
        return !key || (owned && owned.uncertain) ? "unknown"
            : owned ? "managed" : "unmanaged";
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
        if (limitStateFor(entry) === "unknown") {
            applyError = "LIMIT OWNERSHIP UNKNOWN // VERIFY BEFORE CHANGING";
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
        const script = "import json, os, resource, select, sys\nreq=json.loads(sys.argv[1])\npid=req['pid']; born=req['startTicks']; name=req['name']; requested=req['capBytes']\nreply=dict(serial=req['serial'],pid=pid,startTicks=born,name=name,requested=requested,ok=False)\nfd=None\nattempted=False\nconflict=False\ndef encode(value):\n    return '-1' if value==resource.RLIM_INFINITY else str(value)\ndef decode(value):\n    if not isinstance(value,str) or (value!='-1' and (not value.isascii() or not value.isdecimal())):\n        raise ValueError('INVALID LIMIT BASELINE')\n    return resource.RLIM_INFINITY if value=='-1' else int(value)\ndef observe():\n    if poll.poll(0): raise RuntimeError('ORIGINAL PROCESS EXITED')\n    with open(f'/proc/{pid}/stat',encoding='utf-8') as source: data=source.read().strip()\n    end=data.rfind(')'); fields=data[end+2:].split()\n    if data[data.index('(')+1:end]!=name or int(fields[19])!=born or fields[0]=='Z':\n        raise RuntimeError('PROCESS IDENTITY CHANGED')\n    if poll.poll(0): raise RuntimeError('ORIGINAL PROCESS EXITED')\ntry:\n    if type(pid) is not int or pid<=1 or type(born) is not int or born<=0 or not isinstance(name,str) or not name or type(requested) is not int or requested<0:\n        raise ValueError('INVALID LIMIT REQUEST')\n    owned=req.get('ownership')\n    if owned is not None and (not isinstance(owned,dict) or owned.get('uncertain')):\n        raise ValueError('LIMIT OWNERSHIP UNKNOWN')\n    fd=os.pidfd_open(pid,0)\n    poll=select.poll(); poll.register(fd,select.POLLIN)\n    observe()\n    old_soft,hard=resource.prlimit(pid,resource.RLIMIT_AS)\n    observe()\n    original=encode(old_soft)\n    hard_token=encode(hard)\n    if owned is not None:\n        original=owned['originalSoft']\n        baseline=decode(original)\n        if encode(old_soft)!=owned['appliedSoft'] or hard_token!=owned['hard']:\n            conflict=True\n            raise RuntimeError('EXTERNAL LIMIT CHANGE // NO MUTATION')\n    if requested==0 and owned is None:\n        # Release is a no-op if KILL does not own a previous adjustment.\n        reply.update(ok=True,mode='noop',observedSoft=encode(old_soft),originalSoft=original,hard=hard_token)\n    else:\n        if requested==0:\n            target=baseline\n            if hard!=resource.RLIM_INFINITY and (target==resource.RLIM_INFINITY or target>hard):\n                conflict=True\n                raise RuntimeError('ORIGINAL SOFT LIMIT NO LONGER PERMITTED')\n        else:\n            target=requested if hard==resource.RLIM_INFINITY else min(requested,hard)\n        observe()\n        # Compare once more immediately before the numeric-PID syscall.\n        # This is not atomic; do not retry or claim race-free mutation.\n        if resource.prlimit(pid,resource.RLIMIT_AS)!=(old_soft,hard):\n            conflict=True\n            raise RuntimeError('LIMIT CHANGED BEFORE APPLY // NO MUTATION')\n        observe()\n        if target!=old_soft:\n            attempted=True\n            resource.prlimit(pid,resource.RLIMIT_AS,(target,hard))\n        observe()\n        soft,hard2=resource.prlimit(pid,resource.RLIMIT_AS)\n        observe()\n        if soft!=target or hard2!=hard:\n            conflict=True\n            raise RuntimeError('LIMIT READBACK MISMATCH')\n        mode='released' if requested==0 else ('noop' if owned is None and soft==old_soft else 'managed')\n        reply.update(ok=True,mode=mode,observedSoft=encode(soft),originalSoft=original,hard=hard_token)\nexcept Exception as exc:\n    reply.update(error=str(exc),attempted=attempted,conflict=conflict)\nfinally:\n    if fd is not None: os.close(fd)\nprint(json.dumps(reply))\n";
        return ["/usr/bin/python3", "-c", script, JSON.stringify(request)];
    }

    function startQueuedApply() {
        if (applyLoading || !queuedRequest)
            return;
        const request = queuedRequest;
        queuedRequest = null;
        const ownership = limitOwnership[request.key] || null;
        // Bind the last verified state at dispatch, not while a prior request
        // for the same process may still be in flight.
        if (ownership && ownership.uncertain) {
            applyError = "LIMIT OWNERSHIP UNKNOWN // QUEUED REQUEST REFUSED";
            refreshRequested();
            return;
        }
        activeRequest = Object.assign({},request,{ownership:ownership ? Object.assign({},ownership) : null});
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

    function validLimitToken(value) {
        return typeof value === "string" && /^(-1|0|[1-9][0-9]*)$/.test(value);
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
            if (reply.ok) {
                if (["managed","released","noop"].indexOf(reply.mode) < 0
                        || !validLimitToken(reply.observedSoft) || !validLimitToken(reply.originalSoft)
                        || !validLimitToken(reply.hard))
                    return null;
                const owned = request.ownership;
                if (owned && (reply.originalSoft !== owned.originalSoft || reply.hard !== owned.hard))
                    return null;
                if (reply.mode === "managed" && (request.capBytes <= 0
                        || !Number.isSafeInteger(Number(reply.observedSoft))
                        || Number(reply.observedSoft) < 0 || Number(reply.observedSoft) > request.capBytes))
                    return null;
                if (reply.mode === "released" && (!owned || request.capBytes !== 0
                        || reply.observedSoft !== owned.originalSoft))
                    return null;
                if (reply.mode === "noop" && (owned || reply.observedSoft !== reply.originalSoft))
                    return null;
            } else if (typeof reply.error !== "string" || typeof reply.attempted !== "boolean"
                       || typeof reply.conflict !== "boolean") {
                return null;
            }
            return reply;
        } catch (error) {
            return null;
        }
    }

    function consumeApply(request, reply) {
        if (!request) return;
        const next = Object.assign({},softLimitPids);
        const ownership = Object.assign({},limitOwnership);
        if (reply && reply.ok) {
            if (reply.mode === "managed") {
                next[request.key] = Number(reply.observedSoft);
                ownership[request.key] = {originalSoft:reply.originalSoft,
                    hard:reply.hard,appliedSoft:reply.observedSoft,uncertain:false};
            } else {
                delete next[request.key];
                delete ownership[request.key];
            }
            applyError = "";
        } else if (reply && !reply.attempted && !reply.conflict) {
            applyError = "LIMIT REFUSED // " + reply.error;
        } else {
            // Retain any known baseline for diagnosis, but quarantine writes.
            // Unknown first mutation cannot silently establish a new baseline.
            delete next[request.key];
            ownership[request.key] = Object.assign({},request.ownership || {},{uncertain:true});
            applyError = reply && reply.conflict
                ? "EXTERNAL OR UNVERIFIED LIMIT CHANGE // VERIFY PROCESS STATE"
                : "LIMIT OUTCOME UNKNOWN // VERIFY PROCESS STATE";
        }
        softLimitPids = next;
        limitOwnership = ownership;
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
