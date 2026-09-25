import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: processLimitMutation

    // Shared verified RLIMIT_AS mutation backend.
    // Policy and semantic scope identity remain with higher-level controllers.
    property var queuedRequests: []
    property var activeRequest: null
    property var batches: ({})
    property int requestSerial: 0
    property int batchSerial: 0
    property bool loading: false
    property string lastError: ""

    signal batchFinished(
        int batchId,
        var context,
        bool ok,
        var results
    )

    function normalizedPids(pids) {
        const source = Array.isArray(pids) ? pids : [];
        const seen = ({});
        const result = [];

        for (let i = 0; i < source.length; i++) {
            const pid = Number(source[i] || 0);

            if (pid <= 1 || seen[String(pid)])
                continue;

            seen[String(pid)] = true;
            result.push(pid);
        }

        return result;
    }

    function requestLimitMany(pids, capBytes, context) {
        const targets = normalizedPids(pids);
        const requested = Number(capBytes || 0);

        if (targets.length === 0
                || !isFinite(requested)
                || requested < 0)
            return 0;

        batchSerial += 1;
        const batchId = batchSerial;
        const batch = {
            context: context || ({}),
            pending: targets.length,
            ok: true,
            results: []
        };

        const nextBatches = Object.assign({}, batches);
        nextBatches[String(batchId)] = batch;
        batches = nextBatches;

        const nextQueue = queuedRequests.slice();

        for (let i = 0; i < targets.length; i++) {
            requestSerial += 1;
            nextQueue.push({
                serial: requestSerial,
                batchId: batchId,
                pid: targets[i],
                capBytes: Math.floor(requested)
            });
        }

        queuedRequests = nextQueue;
        startNext();
        return batchId;
    }

    function requestLimit(pid, capBytes, context) {
        return requestLimitMany([pid], capBytes, context);
    }

    function startNext() {
        if (loading || activeRequest || queuedRequests.length === 0)
            return;

        const nextQueue = queuedRequests.slice();
        activeRequest = nextQueue.shift();
        queuedRequests = nextQueue;
        loading = true;
        lastError = "";

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
            + "    print(json.dumps({'ok':soft==target,'pid':pid,'soft':(-1 if soft==resource.RLIM_INFINITY else int(soft)),'requested':requested,'oldSoft':(-1 if old_soft==resource.RLIM_INFINITY else int(old_soft))}))\n"
            + "except Exception as exc:\n"
            + "    print(json.dumps({'ok':False,'pid':pid,'requested':requested,'error':str(exc)}))\n",
            String(activeRequest.pid),
            String(activeRequest.capBytes)
        ]);
    }

    function finishActive(payload) {
        const request = activeRequest;

        if (!request)
            return;

        const key = String(request.batchId);
        const current = batches[key];

        if (current) {
            current.results.push(payload || ({ ok: false }));
            current.pending = Math.max(0, Number(current.pending || 0) - 1);

            if (!payload || !payload.ok)
                current.ok = false;

            if (current.pending === 0) {
                const nextBatches = Object.assign({}, batches);
                delete nextBatches[key];
                batches = nextBatches;

                batchFinished(
                    Number(request.batchId),
                    current.context || ({}),
                    !!current.ok,
                    current.results.slice()
                );
            }
        }

        activeRequest = null;
        loading = false;

        Qt.callLater(function() {
            processLimitMutation.startNext();
        });
    }

    Process {
        id: applyProcess

        stdout: StdioCollector {
            onStreamFinished: {
                let payload = null;

                try {
                    payload = JSON.parse(String(text || "{}"));
                } catch (error) {
                    payload = {
                        ok: false,
                        error: String(error)
                    };
                }

                if (!payload.ok)
                    processLimitMutation.lastError =
                        String(payload.error || "LIMIT MUTATION FAILED");

                processLimitMutation.finishActive(payload);
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const message = String(text || "").trim();

                if (message.length > 0)
                    processLimitMutation.lastError = message;
            }
        }
    }
}
