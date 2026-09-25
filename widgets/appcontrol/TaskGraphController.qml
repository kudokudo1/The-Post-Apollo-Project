import QtQuick

QtObject {
    id: taskGraphController

    required property var presentationState
    required property var telemetry
    required property var hunterPresentation
    property var taskRows: []

    signal prepareCpuMemAppend()
    signal prepareCombiAppend()
    signal repaintCpuMem(bool forceReset)
    signal repaintCpu(bool forceReset)
    signal repaintAll(bool forceReset)
    signal retryRequested()

    function seedHunterDetailHistories(entry) {
        const pid = Number(entry && entry.pid || 0);
        const histories = presentationState.taskMiniHunterMetricHistories;

        function seed(metric) {
            if (pid <= 0)
                return [];

            const values = histories[metric + ":pid:" + String(pid)];
            return Array.isArray(values)
                   ? values.slice(-presentationState.taskHistoryLimit)
                   : [];
        }

        presentationState.taskHunterDetailHistories = {
            cpu: seed("cpu"),
            mem: seed("mem"),
            io: seed("io"),
            age: seed("age"),
            combined: seed("combined")
        };
        presentationState.taskHunterDetailHistoryRevision += 1;
    }

    function appendSelectedTaskHunterHistories(
        entry,
        cpuPercent,
        rssKiB,
        memPercent,
        ioRateBytes,
        ageSeconds
    ) {
        if (!entry)
            return;

        const pid = Number(entry.pid || 0);
        if (pid <= 1)
            return;

        const ioBytesPerSecond = Math.max(
            0,
            Number(
                ioRateBytes !== undefined
                ? ioRateBytes
                : hunterPresentation.taskIoRate(entry)
            )
        );
        const ioMiB = ioBytesPerSecond / (1024.0 * 1024.0);
        const ageMinutes = Math.max(
            0,
            Number(
                ageSeconds !== undefined
                ? ageSeconds
                : hunterPresentation.elapsedSeconds(entry.elapsed)
            )
        ) / 60.0;
        const memoryMiB = Math.max(0, Number(rssKiB || 0)) / 1024.0;
        const combined =
            Math.max(0, Number(cpuPercent || 0))
            + Math.max(0, Number(memPercent || 0)) * 0.35
            + Math.log(1 + ioMiB) * 3.0;

        const previous = presentationState.taskHunterDetailHistories;
        const next = ({
            cpu: Array.isArray(previous.cpu) ? previous.cpu.slice() : [],
            mem: Array.isArray(previous.mem) ? previous.mem.slice() : [],
            io: Array.isArray(previous.io) ? previous.io.slice() : [],
            age: Array.isArray(previous.age) ? previous.age.slice() : [],
            combined: Array.isArray(previous.combined)
                      ? previous.combined.slice() : []
        });

        function append(metric, value) {
            next[metric].push(Math.max(0, Number(value || 0)));
            while (next[metric].length > presentationState.taskHistoryLimit)
                next[metric].shift();
        }

        append("cpu", cpuPercent);
        append("mem", memoryMiB);
        append("io", ioMiB);
        append("age", ageMinutes);
        append("combined", combined);

        prepareCombiAppend();
        presentationState.taskHunterDetailHistories = next;
        presentationState.taskHunterDetailHistoryRevision += 1;

        Qt.callLater(function() {
            taskGraphController.repaintCpu(false);
        });
    }

    function clearDetailHistory() {
        presentationState.taskHistoryPid = 0;
        presentationState.taskCpuHistory = [];
        presentationState.taskMemHistory = [];
        presentationState.taskHunterDetailHistories = ({
            cpu: [], mem: [], io: [], age: [], combined: []
        });
        presentationState.taskHunterDetailHistoryRevision += 1;
        telemetry.resetDetailProbe(0);
    }

    function resetForSelection(entry, preloadedCpu, forceReset) {
        if (!entry) {
            clearDetailHistory();
            return;
        }

        const pid = Number(entry.pid || 0);

        if (presentationState.taskHistoryPid === pid) {
            if (forceReset) {
                presentationState.taskMiniHistoryRevision += 1;
                presentationState.taskHunterDetailHistoryRevision += 1;
                Qt.callLater(function() {
                    taskGraphController.repaintCpuMem(true);
                });
            }
            return;
        }

        presentationState.taskHistoryPid = pid;

        const preload =
            Array.isArray(preloadedCpu) && preloadedCpu.length > 0
            ? preloadedCpu.slice(-presentationState.taskHistoryLimit)
            : [Math.max(0, Math.min(100, Number(entry.cpu || 0)))];

        presentationState.taskCpuHistory = preload;

        const memorySeed = Math.max(0, Number(entry.mem || 0));
        const mem = [];
        for (let i = 0; i < Math.max(1, preload.length); i++)
            mem.push(memorySeed);
        presentationState.taskMemHistory = mem;

        seedHunterDetailHistories(entry);
        telemetry.resetDetailProbe(pid);

        Qt.callLater(function() {
            taskGraphController.repaintAll(true);
        });
    }

    function appendTaskHistoryValues(cpuValue, memValue) {
        const cpu = presentationState.taskCpuHistory.slice();
        const mem = presentationState.taskMemHistory.slice();

        cpu.push(Math.max(0, Math.min(100, Number(cpuValue || 0))));
        mem.push(Math.max(0, Number(memValue || 0)));

        while (cpu.length > presentationState.taskHistoryLimit)
            cpu.shift();
        while (mem.length > presentationState.taskHistoryLimit)
            mem.shift();

        prepareCpuMemAppend();

        presentationState.taskCpuHistory = cpu;
        presentationState.taskMemHistory = mem;

        Qt.callLater(function() {
            taskGraphController.repaintCpuMem(false);
        });
    }

    function appendTaskHistory(entry) {
        if (!entry
                || Number(entry.pid || 0)
                   !== presentationState.taskHistoryPid)
            return;

        appendTaskHistoryValues(
            Number(entry.cpu || 0),
            Number(entry.mem || 0)
        );
    }

    function refreshDetailProbe(entry) {
        if (!entry
                || Number(entry.pid || 0) <= 1
                || telemetry.detailProbeLoading)
            return;

        telemetry.refreshDetailProbe({
            pid: Number(entry.pid || 0),
            fallbackCpu:
                Math.max(0, Math.min(100, Number(entry.cpu || 0))),
            fallbackIoRate:
                Math.max(0, hunterPresentation.taskIoRate(entry)),
            fallbackAgeSeconds:
                Math.max(0, hunterPresentation.elapsedSeconds(entry.elapsed))
        });
    }

    function applyDetailProbe(sample, currentEntry) {
        const data = sample || ({});
        const pid = Number(data.pid || 0);

        if (pid !== presentationState.taskHistoryPid) {
            Qt.callLater(function() {
                taskGraphController.retryRequested();
            });
            return;
        }

        appendTaskHistoryValues(
            Number(data.cpuPercent || 0),
            Number(data.memPercent || 0)
        );

        appendSelectedTaskHunterHistories(
            currentEntry,
            Number(data.cpuPercent || 0),
            Number(data.rssKiB || 0),
            Number(data.memPercent || 0),
            Number(data.ioRateBytes || 0),
            Number(data.ageSeconds || 0)
        );
    }
    function sourceItem(entry) {
        if (entry && entry._favoriteRecord)
            return entry._sourceItem;
        return entry;
    }

    function identityFromFavoriteKey(key) {
        const raw = String(key || "");
        if (raw.indexOf("task|") !== 0)
            return "";
        try {
            return decodeURIComponent(raw.slice(5));
        } catch (error) {
            return "";
        }
    }

    function persistentIdentity(entry) {
        const source = sourceItem(entry) || entry;
        if (!source)
            return "";

        const comm = String(
            source.comm || source.name || source.label || ""
        ).trim();
        if (comm)
            return comm.toLowerCase();

        const args = String(source.args || "").trim();
        if (!args)
            return "";

        const first = args.split(/\s+/)[0] || "";
        const pieces = first.split("/");
        return String(pieces[pieces.length - 1] || first).toLowerCase();
    }

    function identityForEntry(entry) {
        if (!entry)
            return "";

        if (entry._favoriteRecord
                && String(entry._favoriteType || "") === "task") {
            const stored = identityFromFavoriteKey(entry._favoriteKey);
            if (stored)
                return String(stored).trim().toLowerCase();
        }

        return persistentIdentity(entry);
    }

    function liveTaskForMiniGraph(entry) {
        const source = sourceItem(entry) || entry;
        if (!source || !source._taskRecord)
            return null;

        const sourcePid = Number(source.pid || 0);
        if (sourcePid > 1) {
            for (let i = 0; i < taskRows.length; i++) {
                const exact = taskRows[i];
                if (Number(exact && exact.pid || 0) === sourcePid)
                    return exact;
            }

            if (!entry._favoriteRecord)
                return source;
        }

        const identity = identityForEntry(entry);
        if (identity) {
            let best = null;

            for (let i = 0; i < taskRows.length; i++) {
                const candidate = taskRows[i];
                if (persistentIdentity(candidate) !== identity)
                    continue;
                if (Number(candidate.pid || 0) <= 0)
                    continue;
                if (!best
                        || Number(candidate.cpu || 0)
                           > Number(best.cpu || 0))
                    best = candidate;
            }

            if (best)
                return best;
        }

        return source;
    }

    function updateMiniCpuHistories(rows) {
        const sourceRows = Array.isArray(rows) ? rows : [];
        const previous = presentationState.taskMiniCpuHistories;
        const next = ({});
        const previousIdentity =
            presentationState.taskMiniCpuIdentityHistories;
        const nextIdentity = ({});
        const identitySamples = ({});

        for (let i = 0; i < sourceRows.length; i++) {
            const entry = sourceRows[i];
            const pid = Number(entry && entry.pid || 0);
            if (pid <= 0)
                continue;

            const cpu = Math.max(
                0,
                Math.min(
                    100,
                    Number(
                        entry.cpuInstant !== undefined
                        ? entry.cpuInstant
                        : entry.cpu || 0
                    )
                )
            );

            const key = "pid:" + String(pid);
            const history = Array.isArray(previous[key])
                            ? previous[key].slice() : [];
            history.push(cpu);
            while (history.length > presentationState.taskMiniHistoryLimit)
                history.shift();
            next[key] = history;

            const identity = persistentIdentity(entry);
            if (identity
                    && (
                        identitySamples[identity] === undefined
                        || cpu > identitySamples[identity]
                    ))
                identitySamples[identity] = cpu;
        }

        for (const identity in identitySamples) {
            const key = "identity:" + identity;
            const history =
                Array.isArray(previousIdentity[key])
                ? previousIdentity[key].slice() : [];
            history.push(identitySamples[identity]);
            while (history.length > presentationState.taskMiniHistoryLimit)
                history.shift();
            nextIdentity[key] = history;
        }

        presentationState.taskMiniCpuHistories = next;
        presentationState.taskMiniCpuIdentityHistories = nextIdentity;
    }

    function updateMiniHunterMetricHistories(rows) {
        const sourceRows = Array.isArray(rows) ? rows : [];
        const previous = presentationState.taskMiniHunterMetricHistories;
        const next = Object.assign({}, previous);
        const livePids = ({});

        function append(metric, pid, value) {
            const key = metric + ":pid:" + String(pid);
            const history = Array.isArray(previous[key])
                            ? previous[key].slice() : [];
            history.push(Math.max(0, Number(value || 0)));
            while (history.length > presentationState.taskMiniHistoryLimit)
                history.shift();
            next[key] = history;
        }

        for (let i = 0; i < sourceRows.length; i++) {
            const entry = sourceRows[i];
            const pid = Number(entry && entry.pid || 0);
            if (pid <= 0)
                continue;

            livePids[String(pid)] = true;

            const cpu = Math.max(
                0,
                Number(
                    entry.cpuInstant !== undefined
                    ? entry.cpuInstant
                    : entry.cpu || 0
                )
            );
            const memMiB =
                Math.max(0, Number(entry.rss || 0)) / 1024.0;
            const ioMiB =
                Math.max(0, Number(entry.ioRate || 0))
                / (1024.0 * 1024.0);
            const ageMinutes =
                Math.max(
                    0,
                    entry.ageSeconds !== undefined
                    ? Number(entry.ageSeconds || 0)
                    : hunterPresentation.elapsedSeconds(entry.elapsed)
                ) / 60.0;
            const combined =
                cpu
                + Math.max(0, Number(entry.mem || 0)) * 0.35
                + Math.log(1 + ioMiB) * 3.0;

            append("cpu", pid, cpu);
            append("mem", pid, memMiB);
            append("io", pid, ioMiB);
            append("age", pid, ageMinutes);
            append("combined", pid, combined);
        }

        const keys = Object.keys(next);
        for (let i = 0; i < keys.length; i++) {
            const key = String(keys[i]);
            const pieces = key.split(":pid:");
            if (pieces.length !== 2)
                continue;

            const pidText = pieces[1];
            if (!livePids[pidText]
                    && Number(pidText || 0)
                       !== presentationState.taskHistoryPid)
                delete next[key];
        }

        presentationState.taskMiniHunterMetricHistories = next;
    }

    function miniCpuHistoryByIdentity(identity, liveEntry) {
        const normalized = String(identity || "").trim().toLowerCase();
        const source = liveEntry || null;
        const pid = Number(source && source.pid || 0);

        if (pid > 0) {
            const pidHistory =
                presentationState.taskMiniCpuHistories[
                    "pid:" + String(pid)
                ];
            if (Array.isArray(pidHistory) && pidHistory.length >= 2)
                return pidHistory;
            if (Array.isArray(pidHistory) && pidHistory.length === 1)
                return [pidHistory[0], pidHistory[0]];
        }

        if (normalized) {
            const identityHistory =
                presentationState.taskMiniCpuIdentityHistories[
                    "identity:" + normalized
                ];
            if (Array.isArray(identityHistory)
                    && identityHistory.length >= 2)
                return identityHistory;
            if (Array.isArray(identityHistory)
                    && identityHistory.length === 1)
                return [identityHistory[0], identityHistory[0]];
        }

        const current = Math.max(
            0,
            Math.min(100, Number(source && source.cpu || 0))
        );
        return [current, current];
    }

    function miniHunterHistoryForMetric(entry, metric) {
        const pid = Number(entry && entry.pid || 0);
        if (pid <= 0)
            return [];

        const key = String(metric || "combined");
        const values =
            presentationState.taskMiniHunterMetricHistories[
                key + ":pid:" + String(pid)
            ];
        return Array.isArray(values) ? values : [];
    }

    function miniCpuHistory(entry) {
        const source =
            liveTaskForMiniGraph(entry)
            || sourceItem(entry)
            || entry;
        if (!source || !source._taskRecord)
            return [];

        return miniCpuHistoryByIdentity(
            identityForEntry(entry),
            source
        );
    }

    function miniHunterHistoryForEntry(entry) {
        let metric = "combined";

        if (hunterPresentation.metricMode
                === hunterPresentation.metricCpu)
            metric = "cpu";
        else if (hunterPresentation.metricMode
                 === hunterPresentation.metricMemory)
            metric = "mem";
        else if (hunterPresentation.metricMode
                 === hunterPresentation.metricIo)
            metric = "io";
        else if (hunterPresentation.metricMode
                 === hunterPresentation.metricAge)
            metric = "age";

        return miniHunterHistoryForMetric(entry, metric);
    }

}
