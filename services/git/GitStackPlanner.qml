import QtQuick
import Quickshell
import Quickshell.Io

// Read-only restack planner.
//
// It converts Post-Apollo stack metadata into an ordered rebase plan and
// inspects Git ancestry. It NEVER rewrites refs or runs rebase.
Scope {
    id: root

    required property var branchStackStore
    required property var branchWorkspaceService

    property string repositoryPath: ""
    property bool busy: false
    property string startBranch: ""
    property var plan: []
    property string stateText: "RESTACK PREVIEW // READY"
    property string lastError: ""

    property bool stdoutSeen: false
    property bool stderrSeen: false
    property bool exitSeen: false
    property int exitCode: -1
    property string stdoutText: ""
    property string stderrText: ""

    signal planned(var plan)

    readonly property int stepCount: plan.length

    readonly property int requiredCount:
        plan.filter(function(step) {
            return String((step || {}).status || "") === "RESTACK_REQUIRED";
        }).length

    readonly property int upToDateCount:
        plan.filter(function(step) {
            return String((step || {}).status || "") === "UP_TO_DATE";
        }).length

    readonly property int invalidCount:
        plan.filter(function(step) {
            const status = String((step || {}).status || "");
            return status === "MISSING_BRANCH"
                || status === "MISSING_PARENT"
                || status === "NO_MERGE_BASE"
                || status === "NON_LINEAR"
                || status === "PARENT_INVALID"
                || status === "ERROR";
        }).length

    readonly property bool executable:
        plan.length > 0 && invalidCount === 0

    function clear() {
        busy = false;
        startBranch = "";
        plan = [];
        stateText = "RESTACK PREVIEW // READY";
        lastError = "";
        plannerWatchdog.stop();
    }

    function branchExists(name) {
        return branchWorkspaceService
            && branchWorkspaceService.branchForName(String(name || "")) !== null;
    }

    function structuralSteps(branch, includeStart) {
        const selected = String(branch || "").trim();
        const rows = [];

        if (!selected || !branchStackStore)
            return rows;

        function appendNode(node, depth, includeNode) {
            const name = String(node || "");
            const parent = branchStackStore.parentOf(name);

            if (includeNode && parent) {
                rows.push({
                    branch: name,
                    parent: parent,
                    depth: depth
                });
            }

            const children = branchStackStore.childrenOf(name);

            for (let i = 0; i < children.length; ++i) {
                const child = String(children[i] || "");

                rows.push({
                    branch: child,
                    parent: name,
                    depth: depth + 1
                });

                appendNode(child, depth + 1, false);
            }
        }

        appendNode(selected, 0, Boolean(includeStart));
        return rows;
    }

    function buildPlan(branch, includeStart) {
        if (busy)
            return false;

        const repo = String(repositoryPath || "").trim();
        const selected = String(branch || "").trim();

        if (!repo || !selected) {
            lastError = !repo
                ? "RESTACK PREVIEW // NO REPOSITORY"
                : "RESTACK PREVIEW // NO BRANCH";
            stateText = lastError;
            plan = [];
            return false;
        }

        const steps = structuralSteps(selected, includeStart);

        startBranch = selected;
        plan = [];

        if (steps.length === 0) {
            stateText = "RESTACK PREVIEW // NOTHING TO RESTACK";
            lastError = "";
            planned(plan);
            return true;
        }

        const args = [
            "bash",
            "-lc",
            [
                'repo="$1"',
                'shift',
                'if ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then',
                '  printf "ERROR\\tNOT A GIT WORKTREE\\n"',
                '  exit 21',
                'fi',
                'declare -A moves',
                'declare -A invalid',
                'while [ "$#" -ge 3 ]; do',
                '  child="$1"',
                '  parent="$2"',
                '  depth="$3"',
                '  shift 3',
                '  if ! git -C "$repo" show-ref --verify --quiet "refs/heads/$child"; then',
                '    invalid["$child"]=1',
                '    printf "STEP\\t%s\\t%s\\t%s\\t\\t\\t\\t0\\t0\\tMISSING_BRANCH\\n" "$child" "$parent" "$depth"',
                '    continue',
                '  fi',
                '  if ! git -C "$repo" show-ref --verify --quiet "refs/heads/$parent"; then',
                '    invalid["$child"]=1',
                '    printf "STEP\\t%s\\t%s\\t%s\\t\\t\\t\\t0\\t0\\tMISSING_PARENT\\n" "$child" "$parent" "$depth"',
                '    continue',
                '  fi',
                '  child_head="$(git -C "$repo" rev-parse "$child" 2>/dev/null || true)"',
                '  parent_head="$(git -C "$repo" rev-parse "$parent" 2>/dev/null || true)"',
                '  base="$(git -C "$repo" merge-base "$parent" "$child" 2>/dev/null || true)"',
                '  unique_count=0',
                '  merge_count=0',
                '  if [ -n "${invalid[$parent]:-}" ]; then',
                '    status="PARENT_INVALID"',
                '  elif [ -z "$base" ]; then',
                '    status="NO_MERGE_BASE"',
                '  else',
                '    unique_count="$(git -C "$repo" rev-list --count "$base..$child" 2>/dev/null || printf "0")"',
                '    merge_count="$(git -C "$repo" rev-list --count --merges "$base..$child" 2>/dev/null || printf "0")"',
                '    if [ "$merge_count" -gt 0 ]; then',
                '      status="NON_LINEAR"',
                '    elif [ -n "${moves[$parent]:-}" ]; then',
                '      status="RESTACK_REQUIRED"',
                '    elif git -C "$repo" merge-base --is-ancestor "$parent" "$child" >/dev/null 2>&1; then',
                '      status="UP_TO_DATE"',
                '    else',
                '      status="RESTACK_REQUIRED"',
                '    fi',
                '  fi',
                '  if [ "$status" = "RESTACK_REQUIRED" ]; then moves["$child"]=1; fi',
                '  case "$status" in MISSING_BRANCH|MISSING_PARENT|NO_MERGE_BASE|NON_LINEAR|PARENT_INVALID|ERROR) invalid["$child"]=1 ;; esac',
                '  printf "STEP\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\n" "$child" "$parent" "$depth" "$child_head" "$parent_head" "$base" "$unique_count" "$merge_count" "$status"',
                'done'
            ].join("\n"),
            "git-restack-preview",
            repo
        ];

        for (let i = 0; i < steps.length; ++i) {
            args.push(String(steps[i].branch || ""));
            args.push(String(steps[i].parent || ""));
            args.push(String(steps[i].depth || 0));
        }

        busy = true;
        stateText = "RESTACK PREVIEW // READING";
        lastError = "";

        stdoutSeen = false;
        stderrSeen = false;
        exitSeen = false;
        exitCode = -1;
        stdoutText = "";
        stderrText = "";

        plannerWatchdog.restart();
        plannerProcess.exec(args);
        return true;
    }

    function parsePlan(text) {
        const rows = [];
        const lines = String(text || "").split("\n");

        for (let i = 0; i < lines.length; ++i) {
            const raw = String(lines[i] || "");

            if (!raw)
                continue;

            const parts = raw.split("\t");
            const kind = parts.length > 0 ? parts[0] : "";

            if (kind === "ERROR") {
                lastError = parts.length > 1
                    ? parts.slice(1).join("\t")
                    : "RESTACK PREVIEW FAILED";
                continue;
            }

            if (kind !== "STEP")
                continue;

            rows.push({
                branch: parts.length > 1 ? parts[1] : "",
                parent: parts.length > 2 ? parts[2] : "",
                depth: parts.length > 3 ? Number(parts[3] || 0) : 0,
                head: parts.length > 4 ? parts[4] : "",
                parentHead: parts.length > 5 ? parts[5] : "",
                mergeBase: parts.length > 6 ? parts[6] : "",
                uniqueCommits: parts.length > 7 ? Number(parts[7] || 0) : 0,
                mergeCommits: parts.length > 8 ? Number(parts[8] || 0) : 0,
                status: parts.length > 9 ? parts[9] : "ERROR"
            });
        }

        plan = rows;
    }

    function maybeFinish() {
        if (!busy || !stdoutSeen || !stderrSeen || !exitSeen)
            return;

        busy = false;
        plannerWatchdog.stop();

        if (exitCode !== 0) {
            lastError = String(
                stderrText
                || stdoutText
                || ("RESTACK PREVIEW EXIT " + exitCode)
            ).trim();

            stateText = "RESTACK PREVIEW // ERROR";
            plan = [];
            return;
        }

        parsePlan(stdoutText);

        if (lastError) {
            stateText = "RESTACK PREVIEW // ERROR";
            return;
        }

        if (invalidCount > 0) {
            stateText =
                "RESTACK PREVIEW // "
                + String(invalidCount)
                + " INVALID";
        } else if (requiredCount > 0) {
            stateText =
                "RESTACK PREVIEW // "
                + String(requiredCount)
                + " MOVE"
                + (requiredCount === 1 ? "" : "S")
                + " REQUIRED";
        } else {
            stateText = "RESTACK PREVIEW // UP TO DATE";
        }

        planned(plan);
    }

    Process {
        id: plannerProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.stdoutText = this.text;
                root.stdoutSeen = true;
                root.maybeFinish();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.stderrText = this.text;
                root.stderrSeen = true;
                root.maybeFinish();
            }
        }

        onExited: function(code, exitStatus) {
            root.exitCode = Number(code);
            root.exitSeen = true;
            root.maybeFinish();
        }
    }

    Timer {
        id: plannerWatchdog
        interval: 10000
        repeat: false

        onTriggered: {
            if (!root.busy)
                return;

            root.busy = false;
            root.lastError = "RESTACK PREVIEW // TIMEOUT";
            root.stateText = root.lastError;
            root.plan = [];
        }
    }
}
