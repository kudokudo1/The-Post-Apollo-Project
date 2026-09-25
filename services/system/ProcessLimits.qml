import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: processLimits

    // RLIMIT_AS state and mutation queue. Safety/confirmation remains outside
    // this backend so callers must authorize the target before requesting a
    // limit change.
    property var softLimitPids: ({})
    property var queuedRequest: null
    property var activeRequest: null

    // Optional compatibility bridge. Until T3 wires the shared mutation
    // lifetime, ProcessLimits keeps its original verified fallback backend.
    property var mutationService: null
    property int activeMutationBatchId: 0

    property bool applyLoading: false
    property int requestSerial: 0
    property string applyError: ""

    signal refreshRequested()

    function limitBytesFor(entry) {
        if (!entry)
            return 0;

        return Number(
            softLimitPids["pid:" + String(entry.pid || 0)] || 0
        );
    }

    function hasSoftLimit(entry) {
        return limitBytesFor(entry) > 0;
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
        if (!entry || Number(entry.pid || 0) <= 1)
            return;

        const pid = Number(entry.pid || 0);
        const key = "pid:" + String(pid);
        const previousBytes = Number(softLimitPids[key] || 0);
        const minMiB = minimumMiB(entry);
        const maxMiB = maximumMiB(entry);
        const requested = Number(mib);
        let policyBytes = 0;

        if (isFinite(requested) && requested < maxMiB * 0.995) {
            const capMiB = Math.max(
                minMiB,
                Math.min(maxMiB - 1, requested)
            );
            policyBytes = Math.floor(capMiB * 1024 * 1024);
        }

        // Optimistic UI, then verify what the kernel actually accepted.
        const optimistic = Object.assign({}, softLimitPids);

        if (policyBytes > 0)
            optimistic[key] = policyBytes;
        else
            delete optimistic[key];

        softLimitPids = optimistic;

        requestSerial += 1;
        queuedRequest = {
            serial: requestSerial,
            pid: pid,
            key: key,
            capBytes: policyBytes,
            previousBytes: previousBytes
        };

        startQueuedApply();
    }

    function startQueuedApply() {
        if (applyLoading || !queuedRequest)
            return;

        activeRequest = queuedRequest;
        queuedRequest = null;
        applyLoading = true;
        applyError = "";

        if (mutationService && mutationService.requestLimit) {
            activeMutationBatchId = mutationService.requestLimit(
                activeRequest.pid,
                activeRequest.capBytes,
                {
                    consumer: "process-limits",
                    serial: Number(activeRequest.serial || 0)
                }
            );

            if (activeMutationBatchId > 0)
                return;

            activeMutationBatchId = 0;
        }

        // Compatibility fallback for the current live donor lifetime. Once
        // ProcessLimitMutation is wired, this path becomes cold.
        applyProcess.exec([
            "/usr/bin/python3",
            "-c",
            "import json,resource,sys\n"
            + "pid=int(sys.argv[1]); requested=int(sys.argv[2])\n"
            + "try:\n"
            + "    old_soft,hard=resource.prlimit(pid,resource.RLIMIT_AS)\n"
            + "    target=(hard if hard!=resource.RLIM_INFINITY else resource.RLIM_INFINITY) if requested<=0 else (requested if hard==resource.RLIM_INFINITY else min(requested,hard))\n"
            + "    resource.prlimit(pid,resource.RLIMIT_AS,(target,hard))\n"
            + "    soft,hard2=resource.prlimit(pid,resource.RLIMIT_AS)\n"
            + "    print(json.dumps({'ok':soft==target,'pid':pid,'soft':(-1 if soft==resource.RLIM_INFINITY else int(soft)),'requested':requested}))\n"
            + "except Exception as exc:\n"
            + "    print(json.dumps({'ok':False,'pid':pid,'requested':requested,'error':str(exc)}))\n",
            String(activeRequest.pid),
            String(activeRequest.capBytes)
        ]);
    }

    function consumeApply(output) {
        const request = activeRequest;
        let payload = null;

        try {
            payload = JSON.parse(String(output || "{}"));
        } catch (error) {
            payload = {
                ok: false,
                error: String(error)
            };
        }

        const newerQueued =
            queuedRequest
            && request
            && Number(queuedRequest.serial || 0)
               > Number(request.serial || 0);

        if (request && !newerQueued) {
            const next = Object.assign({}, softLimitPids);
            const key = String(request.key || "");

            if (payload && payload.ok) {
                if (Number(request.capBytes || 0) <= 0)
                    delete next[key];
                else {
                    const verified = Number(payload.soft || 0);
                    next[key] =
                        verified > 0
                        ? verified
                        : Number(request.capBytes || 0);
                }

                applyError = "";
            } else {
                const previous = Number(request.previousBytes || 0);

                if (previous > 0)
                    next[key] = previous;
                else
                    delete next[key];

                applyError = String(
                    payload && payload.error
                    ? payload.error
                    : "KERNEL MEMORY LIMIT WAS NOT APPLIED"
                );
            }

            softLimitPids = next;
        }

        activeRequest = null;
        applyLoading = false;
        refreshRequested();

        Qt.callLater(function() {
            processLimits.startQueuedApply();
        });
    }

    Connections {
        target: processLimits.mutationService
        ignoreUnknownSignals: true

        function onBatchFinished(batchId, context, ok, results) {
            if (Number(batchId || 0)
                    !== Number(processLimits.activeMutationBatchId || 0))
                return;

            if (!context
                    || String(context.consumer || "") !== "process-limits"
                    || !processLimits.activeRequest
                    || Number(context.serial || 0)
                       !== Number(processLimits.activeRequest.serial || 0))
                return;

            processLimits.activeMutationBatchId = 0;

            const rows = Array.isArray(results) ? results : [];
            const payload =
                rows.length > 0
                ? rows[0]
                : {
                    ok: !!ok,
                    error:
                        ok
                        ? ""
                        : "PROCESS LIMIT MUTATION RETURNED NO RESULT"
                };

            processLimits.consumeApply(JSON.stringify(payload || {}));
        }
    }

    Process {
        id: applyProcess

        stdout: StdioCollector {
            onStreamFinished: {
                processLimits.consumeApply(text);
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const message = String(text || "").trim();

                if (message.length > 0)
                    processLimits.applyError = message;
            }
        }
    }
}
