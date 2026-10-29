import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: hospitalService

    // Opt-in, static-label source attribution for synchronous completion work.
    // No process output, repository paths, or command arguments are logged.
    readonly property bool subprocessLagProbeEnabled:
        String(Quickshell.env("POST_APOLLO_SUBPROCESS_LAG_PROBE") || "").trim() === "1"

    function traceSubprocessLag(stage, size) {
        if (!subprocessLagProbeEnabled)
            return;
        console.warn("SYNTAGMA_SUBPROCESS_PROBE // service=hospital-topology"
                     + " stage=" + stage + " size=" + Number(size || 0)
                     + " tsMs=" + Date.now());
    }

    // Opt-in, low-volume attribution of the existing SplitParser.onRead work.
    // Every 64th ordinary line and every >=2 KiB line gets paired markers.
    // Slow callbacks always get a completion marker; raw data is never logged.
    property int splitReadProbeSequence: 0

    function beginSplitRead(slot, line) {
        if (!subprocessLagProbeEnabled)
            return null;
        const size = String(line || "").length;
        const sequence = ++splitReadProbeSequence;
        const now = Date.now();
        const sampled = size >= 2048 || sequence % 64 === 1;
        if (sampled)
            console.warn("SYNTAGMA_SPLIT_READ_PROBE // service=hospital-topology"
                         + " stage=" + slot + ":begin"
                         + " size=" + size + " seq=" + sequence
                         + " tsMs=" + now);
        return { startedAtMs: now, size: size, seq: sequence, sampled: sampled };
    }

    function endSplitRead(slot, trace) {
        if (!trace)
            return;
        const now = Date.now();
        const elapsedMs = now - trace.startedAtMs;
        if (trace.sampled || elapsedMs >= 25)
            console.warn("SYNTAGMA_SPLIT_READ_PROBE // service=hospital-topology"
                         + " stage=" + slot + ":end"
                         + " size=" + trace.size + " seq=" + trace.seq
                         + " elapsedMs=" + elapsedMs + " tsMs=" + now);
    }

    // The selected Hospital floor supplies the repository path.
    property string repoPath: ""

    property bool available: false
    property bool refreshing: false

    property string repoRoot: ""
    property string repository: "NOT CONNECTED"
    property string branch: "NOT CONNECTED"
    property string head: "NOT CONNECTED"
    property string worktree: "NOT CONNECTED"
    property string origin: "NOT CONNECTED"

    property int branchCount: 0
    property int maxLane: 0
    property int topologyRevision: 0
    property string lastError: ""

    property alias topologyModel: topologyRows
    readonly property int commitCount: topologyRows.count

    property var activeLanes: []

    // Refresh into a staging snapshot so the visible topology never blanks
    // while local Git is being reread.
    property var pendingTopologyRows: []
    property var pendingActiveLanes: []
    property int pendingMaxLane: 0

    signal refreshed()

    ListModel {
        id: topologyRows
    }

    function resetTopology() {
        topologyRows.clear();
        activeLanes = [];
        maxLane = 0;
    }

    function resetPendingTopology() {
        pendingTopologyRows = [];
        pendingActiveLanes = [];
        pendingMaxLane = 0;
    }

    function cleanRefs(rawRefs) {
        const pieces = String(rawRefs || "").split(",");
        const cleaned = [];

        for (let i = 0; i < pieces.length; ++i) {
            let value = pieces[i].trim();

            if (!value || value === "origin/HEAD")
                continue;

            value = value.replace(/^HEAD -> /, "");
            value = value.replace(/^tag: /, "TAG ");

            if (value === "origin/HEAD")
                continue;

            cleaned.push(value);
        }

        return cleaned.slice(0, 3).join(" • ");
    }

    function allocateLane(sha, parents) {
        let lanes = pendingActiveLanes.slice();
        let lane = lanes.indexOf(sha);

        if (lane < 0) {
            lane = lanes.length;
            lanes.push(sha);
        }

        const primary = parents.length > 0 ? parents[0] : "";

        if (!primary) {
            lanes.splice(lane, 1);
        } else {
            const existingPrimary = lanes.indexOf(primary);

            if (existingPrimary >= 0 && existingPrimary !== lane) {
                lanes.splice(lane, 1);
            } else {
                lanes[lane] = primary;
            }

            let insertionLane = Math.min(lane + 1, lanes.length);

            for (let i = 1; i < parents.length; ++i) {
                const parent = parents[i];

                if (!parent || lanes.indexOf(parent) >= 0)
                    continue;

                lanes.splice(insertionLane, 0, parent);
                insertionLane += 1;
            }
        }

        pendingActiveLanes = lanes;
        pendingMaxLane = Math.max(pendingMaxLane, lane);

        return lane;
    }

    function appendCommit(sha, parentField, refs, subject) {
        traceSubprocessLag("commit-copy:begin", pendingTopologyRows.length);
        const parentText = String(parentField || "").trim();
        const parents = parentText ? parentText.split(/\s+/) : [];
        const lane = allocateLane(sha, parents);
        const decorated = String(refs || "");

        const rows = pendingTopologyRows.slice();

        rows.push({
            sha: sha,
            shortSha: String(sha).slice(0, 8),
            parents: parents.join(" "),
            refsText: cleanRefs(decorated),
            subject: String(subject || ""),
            lane: lane,
            isHead: decorated.indexOf("HEAD ->") >= 0
        });

        pendingTopologyRows = rows;
        traceSubprocessLag("commit-copy:end", pendingTopologyRows.length);
    }

    function commitAt(index) {
        if (index < 0 || index >= topologyRows.count)
            return null;

        return topologyRows.get(index);
    }

    function indexOfSha(sha) {
        const needle = String(sha || "");

        for (let i = 0; i < topologyRows.count; ++i) {
            if (String(topologyRows.get(i).sha) === needle)
                return i;
        }

        return -1;
    }

    function refresh() {
        if (refreshing)
            return;

        refreshing = true;
        lastError = "";
        resetPendingTopology();
        watchdog.restart();

        refreshProcess.exec([
            "bash",
            "-lc",
            [
                'repo="$1"',
                'if [ -z "$repo" ]; then',
                '  printf "ERROR\\tNO LOCAL BED SELECTED\\n"',
                '  printf "DONE\\t\\n"',
                '  exit 0',
                'fi',
                'if ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then',
                '  printf "ERROR\\tBED CHECKOUT NOT FOUND\\n"',
                '  printf "DONE\\t\\n"',
                '  exit 0',
                'fi',
                'root="$(git -C "$repo" rev-parse --show-toplevel)"',
                'name="$(basename "$root")"',
                'branch="$(git -C "$repo" branch --show-current)"',
                'if [ -z "$branch" ]; then branch="DETACHED"; fi',
                'head="$(git -C "$repo" rev-parse --short=10 HEAD)"',
                'count="$(git -C "$repo" status --porcelain=v1 | wc -l | tr -d " ")"',
                'if [ "$count" -eq 0 ]; then worktree="CLEAN"; else worktree="DIRTY • $count CHANGES"; fi',
                'origin="$(git -C "$repo" remote get-url origin 2>/dev/null || true)"',
                'if [ -z "$origin" ]; then origin="NO ORIGIN"; fi',
                'branches="$(git -C "$repo" for-each-ref --format="%(refname:short)" refs/heads refs/remotes/origin 2>/dev/null | grep -v "^origin/HEAD$" | wc -l | tr -d " ")"',
                'printf "ROOT\\t%s\\n" "$root"',
                'printf "REPO\\t%s\\n" "$name"',
                'printf "BRANCH\\t%s\\n" "$branch"',
                'printf "HEAD\\t%s\\n" "$head"',
                'printf "WORKTREE\\t%s\\n" "$worktree"',
                'printf "ORIGIN\\t%s\\n" "$origin"',
                'printf "BRANCHCOUNT\\t%s\\n" "$branches"',
                'git -C "$repo" log --all --topo-order --date-order -n 36 --pretty=format:"COMMIT%x09%H%x09%P%x09%D%x09%s"',
                'printf "\\nDONE\\t\\n"'
            ].join("\n"),
            "hospital-patient-refresh",
            repoPath
        ]);
    }

    function consumeLine(line) {
        const raw = String(line || "");
        const parts = raw.split("\t");
        const key = parts.length > 0 ? parts[0] : "";

        if (key === "COMMIT") {
            appendCommit(
                parts.length > 1 ? parts[1] : "",
                parts.length > 2 ? parts[2] : "",
                parts.length > 3 ? parts[3] : "",
                parts.length > 4 ? parts.slice(4).join("\t") : ""
            );
            return;
        }

        const value = parts.length > 1 ? parts.slice(1).join("\t") : "";

        if (key === "ROOT")
            repoRoot = value;
        else if (key === "REPO")
            repository = value;
        else if (key === "BRANCH")
            branch = value;
        else if (key === "HEAD")
            head = value;
        else if (key === "WORKTREE")
            worktree = value;
        else if (key === "ORIGIN")
            origin = value;
        else if (key === "BRANCHCOUNT")
            branchCount = Number(value || 0);
        else if (key === "ERROR") {
            available = false;
            lastError = value;
        } else if (key === "DONE") {
            traceSubprocessLag("topology-publish:begin", pendingTopologyRows.length);
            refreshing = false;
            watchdog.stop();

            if (!lastError) {
                topologyRows.clear();

                for (let i = 0; i < pendingTopologyRows.length; ++i)
                    topologyRows.append(pendingTopologyRows[i]);

                activeLanes = pendingActiveLanes.slice();
                maxLane = pendingMaxLane;
                topologyRevision += 1;
                available = true;
                refreshed();
            }

            resetPendingTopology();
            traceSubprocessLag("topology-publish:end", topologyRows.count);
        }
    }

    Process {
        id: refreshProcess

        stdout: SplitParser {
            onRead: function(line) {
                const splitReadTrace = hospitalService.beginSplitRead("topology-stdout", line);
                hospitalService.consumeLine(line);
                hospitalService.endSplitRead("topology-stdout", splitReadTrace);
            }
        }

        stderr: SplitParser {
            onRead: function(line) {
                const splitReadTrace = hospitalService.beginSplitRead("topology-stderr", line);
                const message = String(line || "").trim();

                if (message.length > 0)
                    hospitalService.lastError = message;
                hospitalService.endSplitRead("topology-stderr", splitReadTrace);
            }
        }
    }

    Timer {
        id: watchdog
        interval: 6000
        repeat: false

        onTriggered: {
            hospitalService.refreshing = false;
            hospitalService.lastError = "PATIENT GIT READ TIMEOUT";
            hospitalService.resetPendingTopology();
        }
    }
}
