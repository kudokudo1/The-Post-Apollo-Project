pragma Singleton

import QtQuick
import Quickshell
import "../system"
import qs.services.favorites
import "../favorites/FavoritesAppControlIdentityPolicy.js" as FavoriteIdentity

// Authoritative runtime KILL store. No widget dependency, persistence,
// or extra polling loop. Mutation primitives retain existing guarded callers.
// Shell owns service admission;
// the original snapshot, mini and detail cadences live in this module.
Scope {
    id: root

    readonly property var telemetry: sampler
    readonly property var rows: sampler.rows

    // Shell enables collection only after both consumers are constructed.
    // Demand flags are presentation inputs, never a second collector.
    property bool collectionEnabled: false
    property bool cpuVisible: false
    onCpuVisibleChanged: if (!cpuVisible) cancelCpuBulkReview(cpuBulkReview)
    property bool donorResourceVisible: false
    property bool donorKillVisible: false
    property bool donorFavoritesVisible: false
    property bool donorFavoriteTasksVisible: false
    property bool donorCombiVisible: false
    property bool hasTaskFavorites: false

    readonly property bool miniProbeNeeded:
        cpuVisible || donorKillVisible || donorFavoritesVisible
    readonly property int snapshotInterval: snapshotCadence(cpuVisible,
        donorResourceVisible, donorKillVisible, donorFavoriteTasksVisible,
        donorCombiVisible, histories.taskMiniPreloadSnapshots,
        histories.taskMiniPreloadTarget, hasTaskFavorites)
    readonly property var refreshAfterActionTimer: afterAction

    // Single custody for existing runtime locks, process mutation primitives
    // and the serialized limit queue. No policy or execution changes in K3a.
    readonly property var safety: safetyState
    readonly property var control: controlBackend
    readonly property var limits: limitBackend
    // One long-lived execution lifecycle. Donor supplies legacy confirmation
    // presentation only; process policies and live rows belong to this store.
    property var donorHunterHost: null
    // Transitional compositor snapshot; null is unknown, not an empty desktop.
    property var hunterVisibleWindows: null
    readonly property var favoriteStore: FavoritesStore
    readonly property var hunterExecutor: hunterExecution
    readonly property var hunterOperation: hunterController
    HunterOperationController {
        id: hunterController
        host: root.donorHunterHost
        policyOwner: root
        favoriteStoreObject: root.favoriteStore
        executor: hunterExecution
        refreshTimer: afterAction
    }
    HunterExecutor {
        id: hunterExecution
        onResultReady: function(result) { hunterController.applyResult(result); }
        onFinished: hunterController.finish()
        onErrorRaised: function(message) {
            console.log("AppControl: HUNTER", String(message || ""));
        }
    }

    // Shared individual action authority. Only the transitional legacy
    // confirmation UI selects donorTask and contributes its bulk exclusion.
    property var donorTask: null
    // Legacy dialog exclusion only; the service owns bulk exclusion below.
    property bool donorActionBlocked: false
    readonly property var presentation: actionPresentation
    readonly property var actionGate: guardedActions
    ProcessPresentationController {
        id: actionPresentation
        safetyService: root.safety
        limitsService: root.limits
        controlService: root.control
        currentTask: root.donorTask
        taskRows: root.rows
        onRefreshRequested: afterAction.restart()
    }
    AppControlHubActionGate {
        id: guardedActions
        ownerRows: root.rows
        safetyOwner: root.safety
        presentationOwner: root.presentation
        controlOwner: root.control
        limitsOwner: root.limits
        refreshOwner: root.refreshAfterActionTimer
        bulkBlocked: root.donorActionBlocked || root.cpuBulkReview !== null
            || root.hunterOperation.phase !== "idle"
    }

    TaskSafety { id: safetyState }
    ProcessControl { id: controlBackend }
    ProcessLimits {
        id: limitBackend
        onRefreshRequested: afterAction.restart()
    }

    // CPU++ lock projection and toggles share the same in-memory TaskSafety.
    // Keep sticky/per-action methods off the Hub-facing gateway interface.
    function lockModeForIdentity(pid, birth, name, action, localOnly) {
        const row = actionGate.exactRow(pid, birth, name);
        if (!row) return "";
        if (!action) return localOnly ? "" : safety.dangerUnlockMode(row);
        return localOnly ? safety.dangerActionLocalUnlockMode(row, action)
                         : safety.dangerActionUnlockMode(row, action);
    }

    function toggleLockForIdentity(pid, birth, name, action, sticky) {
        if (actionGate.pending || actionGate.busy || actionGate.bulkBlocked)
            return false;
        const row = actionGate.exactRow(pid, birth, name);
        if (!row || !safety.requiresDangerUnlock(row) || typeof sticky !== "boolean")
            return false;
        if (action !== "" && ["kill", "restart", "freeze", "limit"].indexOf(action) === -1)
            return false;
        if (!action && !sticky) return actionGate.toggleOneShotUnlock(pid, birth, name);
        if (!action) safety.toggleDangerStickyUnlock(row);
        else if (sticky) safety.toggleDangerActionStickyUnlock(row, action);
        else safety.toggleDangerActionUnlock(row, action);
        return true;
    }

    // Recipient supplies only a metric and visibility. All captures and
    // one-use admission are service owned; legacy dialogs remain exclusive.
    function cpuBulkCandidates(kind, metric, visibility) {
        if (!cpuVisible || !Number.isInteger(metric) || metric < 0 || metric > 4
                || !Number.isInteger(visibility) || visibility < 0 || visibility > 2)
            return [];
        if (kind !== "kill-all" && visibility === 1) return [];
        const rows = kind === "kill-all" ? killAllEligibleTasks()
            : kind === "kill-hogs" ? hunterHogCandidates(metric)
            : kind === "kill-mice" ? hunterMouseCandidates() : [];
        return rows.filter(function(row) {
            const target = hunterOperation.targetsFromRows([row])[0];
            return target && Number.isSafeInteger(target.pid) && target.pid > 1
                && Number.isSafeInteger(target.startTicks) && target.startTicks > 0
                && !!target.name && !!target.identity && !hunterOperation.targetIsFavorite(target);
        });
    }

    function prepareCpuBulkReview(kind, metric, visibility) {
        if (!cpuVisible || cpuBulkReview || donorActionBlocked
                || hunterOperationPhase !== "idle" || actionGate.pending
                || actionGate.busy) return null;
        const rows = cpuBulkCandidates(kind, metric, visibility);
        const captures = hunterOperation.targetsFromRows(rows);
        return captureCpuBulkReview(kind, metric, visibility, captures);
    }

    function cancelCpuBulkReview(review) {
        return releaseCpuBulkReview(review);
    }

    function confirmCpuBulkReview(review) {
        if (!review || cpuBulkReview !== review || !cpuVisible
                || donorActionBlocked || hunterOperationPhase !== "idle"
                || actionGate.pending || actionGate.busy
                || !hunterOperation.policyReady) return false;
        // Consume the exact review once; never recompute or broaden it.
        if (!releaseCpuBulkReview(review)) return false;
        hunterOperation.start(review.kind, review.targets, true);
        return true;
    }

    function acknowledgeCpuBulkReport() {
        if (!cpuBulkOperation || hunterOperationPhase !== "report") return false;
        hunterOperation.phase = "idle";
        hunterOperation.kind = "";
        hunterOperation.targets = [];
        hunterOperation.results = [];
        hunterOperation.completed = 0;
        hunterOperation.total = 0;
        return true;
    }

    // One immutable recipient review.
    property var cpuBulkReview: null
    readonly property bool cpuBulkOperation: hunterOperation.recipientOwned
        && hunterOperation.phase !== "idle"
    readonly property string cpuBulkMessage: cpuBulkOperation ? hunterOperation.message : ""
    readonly property string hunterOperationPhase: hunterOperation.phase
    readonly property string hunterOperationKind: hunterOperation.kind

    function captureCpuBulkReview(kind, metric, visibility, captures) {
        if (cpuBulkReview || actionGate.pending || actionGate.busy || actionGate.bulkBlocked)
            return null;
        if (!Array.isArray(captures) || !captures.length
                || new Set(captures.map(t => t.pid)).size !== captures.length)
            return null;
        const targets = Object.freeze(captures.map(t => Object.freeze(t)));
        const label = kind === "kill-all" ? "ALL ELIGIBLE PROCESSES"
            : kind === "kill-mice" ? "DETACHED IDLE LEAVES"
            : ["COMBI","CPU","MEMORY","I/O","AGE"][metric] + " HOGS";
        cpuBulkReview = Object.freeze({kind:kind, metric:metric, visibility:visibility,
            label:label, targets:targets});
        return cpuBulkReview;
    }

    function releaseCpuBulkReview(review) {
        if (!review || cpuBulkReview !== review) return false;
        cpuBulkReview = null;
        return true;
    }

    // K4c: canonical candidate rules; no selection or process mutation.
    function hunterTaskActive(entry, requestedMetric) {
        const metric = requestedMetric;
        if (!entry || !entry._taskRecord)
            return false;

        if (metric === hunterPresentation.metricMemory)
            return hunterPresentation.taskMemoryMiB(entry) >= 16;

        if (metric === hunterPresentation.metricIo)
            return hunterPresentation.taskIoRate(entry) >= 1024;

        if (metric === hunterPresentation.metricAge)
            return hunterPresentation.elapsedSeconds(entry.elapsed) > 0;

        // COMBI's memory threshold independently admits a row.
        // Avoid scanning CPU history when it already qualifies.
        if (metric === hunterPresentation.metricCombined
                && hunterPresentation.taskMemoryMiB(entry) >= 128)
            return true;

        return hunterPresentation.taskPeak(entry) >= 0.35
               || hunterPresentation.taskAverage(entry) >= 0.15;
    }

    function hunterHogCandidates(requestedMetric) {
        const metric = requestedMetric;
        // Bulk HOG execution always excludes protected/session-critical rows,
        // even when PROTECTED or ALL is selected for inspection.
        const rows = root.rows.filter(function(entry) {
            return taskEligibleForKillAll(entry)
                   && hunterTaskActive(entry, metric)
                   && !isTaskFavorite(entry);
        });
        rows.sort(function(a, b) {
            return hunterPresentation.taskMetricScore(b, metric) - hunterPresentation.taskMetricScore(a, metric);
        });
        if (rows.length === 0)
            return [];

        const topScore = Math.max(0.01, hunterPresentation.taskMetricScore(rows[0], metric));
        let minimum = 0;
        let ratio = 0.48;
        if (metric === hunterPresentation.metricCpu)
            minimum = 8.0;
        else if (metric === hunterPresentation.metricMemory)
            minimum = 128.0; // MiB RSS
        else if (metric === hunterPresentation.metricIo)
            minimum = 1024 * 1024; // 1 MiB/s
        else if (metric === hunterPresentation.metricAge) {
            minimum = 3600;
            ratio = 0.72;
        } else
            minimum = 8.0;

        const threshold = Math.max(minimum, topScore * ratio);
        return rows.filter(function(entry) {
            return hunterPresentation.taskMetricScore(entry, metric) >= threshold;
        }).slice(0, 8);
    }

    function hunterVisibleWindowPidSet() {
        const visible = ({});
        const windows = Array.isArray(hunterVisibleWindows) ? hunterVisibleWindows : [];
        for (let i = 0; i < windows.length; i++) {
            const pid = Number(windows[i] && windows[i].pid || 0);
            if (pid > 1)
                visible[String(pid)] = true;
        }
        return visible;
    }

    function hunterTaskPidMap() {
        const byPid = ({});
        for (let i = 0; i < root.rows.length; i++) {
            const row = root.rows[i];
            const pid = Number(row && row.pid || 0);
            if (pid > 1)
                byPid[String(pid)] = row;
        }
        return byPid;
    }

    function hunterInteractiveTask(entry) {
        if (!entry)
            return false;

        const tty = String(entry.tty || "?").trim();
        if (tty.length > 0 && tty !== "?" && tty !== "-")
            return true;

        const name = String(entry.comm || entry.name || "")
                     .trim().toLowerCase();
        const args = String(entry.args || "").trim().toLowerCase();
        const haystack = name + " " + args;
        const interactiveTokens = [
            // Interactive shells / multiplexers / terminal emulators.
            "zsh", "bash", "fish", "nushell", " nu ", "dash", "ksh",
            "zellij", "tmux", "screen", "kitty", "foot", "alacritty",
            "wezterm", "ghostty", "konsole", "gnome-terminal",

            // Prompt/status helpers and keyboard-heavy interactive tools.
            "gitstatusd", "starship", "oh-my-posh", "powerlevel10k",
            "nvim", "neovim", "vim", "helix", "hx ", "emacs", "yazi",
            "btop", "htop", "top ", "less", "fzf", "ranger"
        ];

        for (let i = 0; i < interactiveTokens.length; i++) {
            if (haystack.indexOf(interactiveTokens[i]) !== -1)
                return true;
        }
        return false;
    }

    function hunterDescendsFromVisibleWindow(entry) {
        if (!entry)
            return false;

        const visible = hunterVisibleWindowPidSet();
        const byPid = hunterTaskPidMap();
        let pid = Number(entry.pid || 0);
        let guard = 0;

        while (pid > 1 && guard < 48) {
            if (visible[String(pid)])
                return true;

            const row = byPid[String(pid)];
            if (!row)
                break;

            const parent = Number(row.ppid || 0);
            if (parent <= 1 || parent === pid)
                break;

            pid = parent;
            guard++;
        }

        return false;
    }

    function hunterDescendsFromInteractiveTask(entry) {
        if (!entry)
            return false;
        const byPid = hunterTaskPidMap();
        let current = entry;
        let guard = 0;
        while (current && guard < 48) {
            if (hunterInteractiveTask(current))
                return true;
            const parentPid = Number(current.ppid || 0);
            if (parentPid <= 1 || parentPid === Number(current.pid || 0))
                break;
            current = byPid[String(parentPid)];
            guard++;
        }
        return false;
    }

    function hunterTaskHasChildren(entry) {
        if (!entry)
            return false;
        const pid = Number(entry.pid || 0);
        if (pid <= 1)
            return true;
        for (let i = 0; i < root.rows.length; i++) {
            if (Number(root.rows[i] && root.rows[i].ppid || 0) === pid)
                return true;
        }
        return false;
    }

    function hunterMouseProtectedReason(entry) {
        if (!entry)
            return "INVALID";

        if (!Array.isArray(hunterVisibleWindows))
            return "WINDOW INVENTORY UNAVAILABLE";

        if (isTaskFavorite(entry))
            return "FAVORITE";

        if (!taskEligibleForKillAll(entry))
            return "SESSION/PROTECTED";

        // Never let the low-activity heuristic dismantle a currently visible
        // GUI application. Chromium/Electron in particular split downloads,
        // networking, rendering and utility work across quiet child processes.
        if (hunterDescendsFromVisibleWindow(entry))
            return "ACTIVE APP TREE";

        if (hunterDescendsFromInteractiveTask(entry))
            return "INTERACTIVE/TTY TREE";

        // MICE only hunts detached leaves. Parents are intentionally retained:
        // killing a quiet parent can orphan or destabilize still-useful children.
        if (hunterTaskHasChildren(entry))
            return "PROCESS TREE";

        // PPID 1/user-service leaves are ambiguous (systemd --user services,
        // daemons, agents). Treat them as infrastructure rather than mice.
        if (Number(entry.ppid || 0) <= 1)
            return "USER SERVICE/ORPHAN";

        const name = String(entry.comm || entry.name || "")
                     .trim().toLowerCase();
        const args = String(entry.args || "").trim().toLowerCase();
        const haystack = name + " " + args;

        const protectedTokens = [
            // Browsers / web runtimes and their helper processes.
            "brave", "chromium", "chrome", "firefox", "vivaldi",
            "opera", "electron", "qtwebengine", "webkit", "webprocess",
            "code", "codium",

            // File transfer / download / sync tools.
            "curl", "wget", "aria2", "rclone", "rsync", "scp", "sftp",
            "syncthing", "megasync", "dropbox", "onedrive",

            // Interactive shells / terminals / prompt helpers. These can be
            // nearly idle for hours and are still absolutely user-owned state.
            "zsh", "bash", "fish", "nushell", "zellij", "tmux", "screen",
            "kitty", "foot", "alacritty", "wezterm", "ghostty",
            "gitstatusd", "starship", "oh-my-posh", "powerlevel10k",
            "nvim", "neovim", "vim", "helix", "emacs", "yazi",

            // Desktop/session/portal/file-service infrastructure.
            "xdg-desktop-portal", "xdg-document-portal", "xdg-permission-store",
            "gvfs", "fuse", "dconf", "dbus", "pipewire", "wireplumber",
            "at-spi", "ssh-agent", "gpg-agent", "polkit", "keyring",
            "systemd", "systemd-oomd", "systemd-resolved", "systemd-timesyncd",

            // Sandboxes, containers and transactional package operations.
            "flatpak", "bwrap", "bubblewrap", "xdg-dbus-proxy", "toolbox",
            "podman", "conmon", "rpm-ostree", "ostree"
        ];

        for (let i = 0; i < protectedTokens.length; i++) {
            if (haystack.indexOf(protectedTokens[i]) !== -1)
                return "IMPORTANT HELPER";
        }

        // Do not hunt a process that is already explicitly stopped/frozen;
        // that state is intentional and managed by the per-process controls.
        if (String(entry.state || "").indexOf("T") !== -1)
            return "FROZEN";

        return "";
    }

    function hunterMouseCandidates() {
        const rows = root.rows.filter(function(entry) {
            if (hunterMouseProtectedReason(entry).length > 0)
                return false;

            // MICE is intentionally conservative. A process must have been
            // around for a while AND remain tiny/quiet across the recent graph,
            // rather than merely being momentarily idle.
            const oldEnough = hunterPresentation.elapsedSeconds(entry.elapsed) >= 45 * 60;
            const quiet = hunterPresentation.taskPeak(entry) <= 0.20
                          && hunterPresentation.taskAverage(entry) <= 0.08
                          && Number(entry.cpu || 0) <= 0.20;
            const small = Number(entry.mem || 0) <= 0.50;
            const tty = String(entry.tty || "?").trim();
            const detached = tty === "?" || tty === "-" || tty.length === 0;
            return oldEnough && quiet && small && detached;
        });
        rows.sort(function(a, b) {
            const rssDelta = Number(a.rss || 0) - Number(b.rss || 0);
            if (Math.abs(rssDelta) > 1)
                return rssDelta;
            return hunterPresentation.elapsedSeconds(b.elapsed) - hunterPresentation.elapsedSeconds(a.elapsed);
        });
        return rows.slice(0, 10);
    }

    // Read the original Favorites membership; never create or mutate keys here.
    function taskPersistentIdentity(entry) {
        return FavoriteIdentity.taskIdentity(entry);
    }

    function isTaskFavorite(entry) {
        if (!favoriteStore || !favoriteStore.favoriteKeys) return true;
        const key = FavoriteIdentity.taskKey(entry);
        return !!key && favoriteStore.favoriteKeys.indexOf(key) !== -1;
    }

    // Preserve the donor's existing eligibility rules and current snapshot.
    function taskEligibleForKillAll(entry) {
        if (!entry || !entry._taskRecord || Number(entry.pid || 0) <= 1)
            return false;

        const currentUser = String(Quickshell.env("USER") || "").trim();
        const taskUser = String(entry.user || "").trim();

        if (currentUser.length > 0
                && taskUser.length > 0
                && taskUser !== currentUser)
            return false;

        if (String(entry.state || "").indexOf("Z") !== -1)
            return false;

        return !safety.protectedFromKillAll(entry);
    }

    function killAllEligibleTasks() {
        const eligible = [];
        for (let i = 0; i < rows.length; i++) {
            if (taskEligibleForKillAll(rows[i]))
                eligible.push(rows[i]);
        }
        return eligible;
    }

    function snapshotCadence(cpu, resource, kill, taskFavorites, combi,
                             preload, target, favorites) {
        if (cpu) return 600;
        if (resource) return 900;
        if (kill || taskFavorites) return 600;
        if (combi) return 1800;
        if (preload < target) return 700;
        return favorites ? 1400 : 3200;
    }

    function refreshSnapshot() {
        if (collectionEnabled) sampler.refreshSnapshot();
    }

    function miniRequestForRows(sourceRows) {
        const request = [];
        for (let i = 0; i < sourceRows.length; i++) {
            const entry = sourceRows[i];
            const pid = Number(entry && entry.pid || 0);
            if (pid <= 1) continue;
            request.push({
                pid: pid,
                comm: String(entry.comm || entry.name || entry.label || "PROCESS"),
                fallbackCpu: Number(entry.cpuInstant !== undefined
                    ? entry.cpuInstant : entry.cpu || 0)
            });
        }
        return request;
    }

    function refreshMiniProbe() {
        if (!collectionEnabled || !miniProbeNeeded || sampler.miniProbeLoading)
            return;
        sampler.refreshMiniProbe(miniRequestForRows(rows));
    }

    Timer {
        id: taskManagerRefreshTimer
        interval: root.snapshotInterval
        repeat: true
        running: root.collectionEnabled
        triggeredOnStart: true
        onTriggered: root.refreshSnapshot()
    }

    Timer {
        id: taskMiniDisplayTimer
        interval: 1200
        repeat: true
        running: root.collectionEnabled && root.miniProbeNeeded
        triggeredOnStart: true
        onTriggered: root.refreshMiniProbe()
    }

    Timer {
        id: afterAction
        interval: 320
        repeat: false
        onTriggered: root.refreshSnapshot()
    }

    // Both consumers read the authoritative graph-history state.
    // Transitional donor bindings select visibility and its legacy detail mode.
    property bool graphVisible: false
    property int graphMetricMode: 0
    readonly property var graphState: histories
    readonly property var graphController: graph
    readonly property var hunterPresentation: hunter
    readonly property var detailSession: selectedDetail

    ProcessPresentationState {
        id: histories
        taskMiniHistoryKeepImmutable: root.graphVisible
    }

    HunterPresentation {
        id: hunter
        presentationState: histories
        metricMode: root.graphMetricMode
    }

    TaskGraphController {
        id: graph
        presentationState: histories
        telemetry: sampler
        hunterPresentation: hunter
        taskRows: root.rows
    }

    KillDetailSession {
        id: selectedDetail
        graph: root.graphController
        state: histories
        rows: root.rows
    }

    // Publication never requires a widget. Transitional observers preserve
    // the donor's ordering, selection and opt-in diagnostic stage markers.
    property bool snapshotTraceEnabled: false
    property bool miniTraceEnabled: false
    property int snapshotTraceSequence: 0
    signal snapshotStarted(var rows)
    signal snapshotOrdering(var rows)
    signal snapshotStage(string stage, int sequence, double startMs, int rowCount)
    signal snapshotPublished(var rows, int sequence)
    signal miniStage(string stage, double startMs)

    function publishSnapshot(input) {
        const snapshotRows = Array.isArray(input) ? input : [];
        const sequence = snapshotTraceEnabled ? ++snapshotTraceSequence : 0;
        const count = snapshotRows.length;
        snapshotStarted(snapshotRows);

        if (!miniProbeNeeded) {
            let started = sequence ? Date.now() : 0;
            graph.updateMiniCpuHistories(snapshotRows);
            if (sequence) snapshotStage("cpu-history", sequence, started, count);
            started = sequence ? Date.now() : 0;
            graph.updateMiniHunterMetricHistories(snapshotRows);
            if (sequence) snapshotStage("hunter-history", sequence, started, count);
            started = sequence ? Date.now() : 0;
            histories.taskMiniHistoryRevision += 1;
            histories.taskMiniDisplayRevision += 1;
            if (sequence) snapshotStage("history-revisions", sequence, started, count);
        }

        let started = sequence ? Date.now() : 0;
        snapshotOrdering(snapshotRows);
        if (sequence) snapshotStage("task-order", sequence, started, count);
        started = sequence ? Date.now() : 0;
        sampler.rows = snapshotRows;
        if (sequence) snapshotStage("task-rows", sequence, started, count);
        histories.taskMiniPreloadSnapshots = Math.min(
            histories.taskMiniPreloadTarget, histories.taskMiniPreloadSnapshots + 1);
        snapshotPublished(snapshotRows, sequence);
    }

    function publishMiniSamples(input) {
        const samples = Array.isArray(input) ? input : [];
        if (!samples.length) return;
        const timed = miniTraceEnabled;
        let started = timed ? Date.now() : 0;
        graph.updateMiniCpuHistories(samples);
        if (timed) miniStage("mini-cpu-history", started);
        started = timed ? Date.now() : 0;
        graph.updateMiniHunterMetricHistories(samples);
        if (timed) miniStage("mini-hunter-history", started);
        started = timed ? Date.now() : 0;
        histories.taskMiniHistoryRevision += 1;
        histories.taskMiniDisplayRevision += 1;
        if (timed) miniStage("mini-history-revisions", started);
    }

    ProcessTelemetry {
        id: sampler
        onSnapshotReady: function(rows) { root.publishSnapshot(rows); }
        onMiniProbeReady: function(rows) { root.publishMiniSamples(rows); }
        onDetailProbeReady: function(sample) { selectedDetail.accept(sample); }
    }
}
