import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: gitService

    property bool available: false
    property bool refreshing: false
    property bool refreshPending: false
    property bool discoveringRepos: false
    property bool actionBusy: false

    property string repoPath: ""
    property string repoLabel: "LIVE QUICKSHELL"
    property string repoRoot: ""
    property string repository: "NOT CONNECTED"
    property string branch: "NOT CONNECTED"
    property string head: "NOT CONNECTED"
    property string worktree: "NOT CONNECTED"
    property string origin: "NOT CONNECTED"
    property string upstream: ""
    property int ahead: 0
    property int behind: 0

    property string selectedRemoteBranch: ""
    property bool selectedRemoteExists: false
    property int selectedRemoteIndex: -1

    property int maxLane: 0
    property int topologyRevision: 0
    property var activeLanes: []
    property var pendingLocalBranches: []
    property var pendingRemoteBranches: []
    property var pendingTopology: []

    property string lastError: ""
    property string actionTitle: "READY"
    property string actionOutput: "Select STATUS, DIFF, LOG, FETCH, PULL, or PUSH."
    property int actionExitCode: 0

    property alias repoModel: repoRows
    property alias localBranchModel: localBranchRows
    property alias remoteBranchModel: remoteBranchRows
    property alias topologyModel: topologyRows

    readonly property int repoCount: repoRows.count
    readonly property int localBranchCount: localBranchRows.count
    readonly property int remoteBranchCount: remoteBranchRows.count
    readonly property int branchCount: localBranchRows.count + remoteBranchRows.count
    readonly property int commitCount: topologyRows.count

    signal refreshed()
    signal repositoriesChanged()

    ListModel { id: repoRows }
    ListModel { id: localBranchRows }
    ListModel { id: remoteBranchRows }
    ListModel { id: topologyRows }

    function repoAt(index) {
        if (index < 0 || index >= repoRows.count)
            return null;
        return repoRows.get(index);
    }

    function localBranchAt(index) {
        if (index < 0 || index >= localBranchRows.count)
            return null;
        return localBranchRows.get(index);
    }

    function remoteBranchAt(index) {
        if (index < 0 || index >= remoteBranchRows.count)
            return null;
        return remoteBranchRows.get(index);
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

    function repoIndexOfPath(pathValue) {
        const needle = String(pathValue || "");
        for (let i = 0; i < repoRows.count; ++i) {
            if (String(repoRows.get(i).path) === needle)
                return i;
        }
        return -1;
    }

    function remoteIndexOf(name) {
        const needle = String(name || "");
        for (let i = 0; i < remoteBranchRows.count; ++i) {
            if (String(remoteBranchRows.get(i).name) === needle)
                return i;
        }
        return -1;
    }

    function discoverRepos() {
        if (discoveringRepos)
            return;

        discoveringRepos = true;
        repoRows.clear();

        repoScanProcess.exec([
            "bash",
            "-lc",
            [
                'live="$HOME/.config/quickshell"',
                'if git -C "$live" rev-parse --is-inside-work-tree >/dev/null 2>&1; then',
                '  printf "REPO\\tLIVE QUICKSHELL\\t%s\\n" "$(git -C "$live" rev-parse --show-toplevel)"',
                'fi',
                'for gitdir in "$HOME"/Projects/*/.git; do',
                '  [ -e "$gitdir" ] || continue',
                '  root="${gitdir%/.git}"',
                '  if git -C "$root" rev-parse --is-inside-work-tree >/dev/null 2>&1; then',
                '    name="$(basename "$root")"',
                '    printf "REPO\\t%s\\t%s\\n" "$name" "$(git -C "$root" rev-parse --show-toplevel)"',
                '  fi',
                'done',
                'printf "DONE\\t\\n"'
            ].join("\n")
        ]);
    }

    function consumeRepoLine(line) {
        const raw = String(line || "");
        const parts = raw.split("\t");
        const key = parts.length > 0 ? parts[0] : "";

        if (key === "REPO") {
            const label = parts.length > 1 ? parts[1] : "REPOSITORY";
            const pathValue = parts.length > 2 ? parts.slice(2).join("\t") : "";
            if (pathValue && repoIndexOfPath(pathValue) < 0)
                repoRows.append({ label: label, path: pathValue });
            return;
        }

        if (key === "DONE") {
            discoveringRepos = false;
            if (repoRows.count > 0) {
                let index = repoIndexOfPath(repoPath);
                if (index < 0)
                    index = 0;
                const row = repoRows.get(index);
                repoPath = String(row.path || "");
                repoLabel = String(row.label || "REPOSITORY");
            }
            repositoriesChanged();
            refresh();
        }
    }

    function selectRepo(index) {
        const row = repoAt(index);
        if (!row)
            return;

        repoPath = String(row.path || "");
        repoLabel = String(row.label || "REPOSITORY");

        if (refreshing) {
            refreshPending = true;
            return;
        }

        refresh();
    }

    function cycleRepo(delta) {
        if (repoRows.count <= 0)
            return;

        let index = repoIndexOfPath(repoPath);
        if (index < 0)
            index = 0;

        index = (index + Number(delta || 0) + repoRows.count) % repoRows.count;
        selectRepo(index);
    }

    function selectRepoText(query) {
        const needle = String(query || "").trim().toLowerCase();

        if (!needle)
            return false;

        let partialIndex = -1;

        for (let i = 0; i < repoRows.count; ++i) {
            const row = repoRows.get(i);
            const label = String(row.label || "");
            const pathValue = String(row.path || "");
            const lowerLabel = label.toLowerCase();
            const lowerPath = pathValue.toLowerCase();

            if (lowerLabel === needle || lowerPath === needle) {
                selectRepo(i);
                return true;
            }

            if (
                partialIndex < 0
                && (
                    lowerLabel.indexOf(needle) >= 0
                    || lowerPath.indexOf(needle) >= 0
                )
            )
                partialIndex = i;
        }

        if (partialIndex >= 0) {
            selectRepo(partialIndex);
            return true;
        }

        actionTitle = "REPOSITORY";
        actionExitCode = 1;
        actionOutput = "NO MATCH // " + String(query || "")
                     + "\nType part of a repo name already registered on this machine.";
        return false;
    }

    function selectRemote(index) {
        const row = remoteBranchAt(index);
        if (!row)
            return;

        selectedRemoteBranch = String(row.name || "");
        selectedRemoteExists = true;
        selectedRemoteIndex = index;
    }

    function cycleRemote(delta) {
        if (remoteBranchRows.count <= 0)
            return;

        let index = selectedRemoteIndex;
        if (index < 0)
            index = 0;
        else
            index = (index + Number(delta || 0) + remoteBranchRows.count)
                    % remoteBranchRows.count;

        selectRemote(index);
    }

    function selectRemoteText(query) {
        let value = String(query || "").trim();

        if (!value)
            return false;

        value = value.replace(/^refs\/remotes\//, "");

        if (value.indexOf("/") < 0)
            value = "origin/" + value;

        selectedRemoteBranch = value;
        selectedRemoteExists = remoteIndexOf(value) >= 0;
        selectedRemoteIndex = selectedRemoteExists
            ? remoteIndexOf(value)
            : selectedRemoteIndex;
        actionTitle = "REMOTE TARGET";
        actionExitCode = 0;
        actionOutput = selectedRemoteExists
            ? "SELECTED EXISTING REMOTE // " + value
            : "REMOTE DOES NOT EXIST YET // " + value
              + "\nPUSH will create it. Nothing has been changed yet.";

        return true;
    }

    function resetTopologyBuild() {
        activeLanes = [];
        maxLane = 0;
        pendingTopology = [];
    }

    function publishPendingModels() {
        localBranchRows.clear();
        remoteBranchRows.clear();
        topologyRows.clear();

        for (let i = 0; i < pendingLocalBranches.length; ++i)
            localBranchRows.append({ name: pendingLocalBranches[i] });

        for (let i = 0; i < pendingRemoteBranches.length; ++i)
            remoteBranchRows.append({ name: pendingRemoteBranches[i] });

        for (let i = 0; i < pendingTopology.length; ++i)
            topologyRows.append(pendingTopology[i]);
    }

    function allocateLane(sha, parents) {
        let lanes = activeLanes.slice();
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

        activeLanes = lanes;
        maxLane = Math.max(maxLane, lane);
        return lane;
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

        return cleaned.slice(0, 4).join(" • ");
    }

    function appendCommit(sha, parentField, refs, subject) {
        const parentText = String(parentField || "").trim();
        const parents = parentText ? parentText.split(/\s+/) : [];
        const lane = allocateLane(sha, parents);
        const decorated = String(refs || "");

        pendingTopology.push({
            sha: sha,
            shortSha: String(sha).slice(0, 8),
            parents: parents.join(" "),
            refsText: cleanRefs(decorated),
            subject: String(subject || ""),
            lane: lane,
            isHead: decorated.indexOf("HEAD ->") >= 0
        });
    }

    function ensureRemoteSelection() {
        if (selectedRemoteBranch) {
            selectedRemoteExists = remoteIndexOf(selectedRemoteBranch) >= 0;
            return;
        }

        if (upstream && remoteIndexOf(upstream) >= 0) {
            selectedRemoteBranch = upstream;
            selectedRemoteExists = true;
            selectedRemoteIndex = remoteIndexOf(upstream);
            return;
        }

        const matching = branch && branch !== "DETACHED"
            ? "origin/" + branch
            : "";

        selectedRemoteBranch = matching;
        selectedRemoteExists = matching
            ? remoteIndexOf(matching) >= 0
            : false;
        selectedRemoteIndex = selectedRemoteExists
            ? remoteIndexOf(matching)
            : -1;
    }

    function refresh() {
        if (refreshing)
            return;

        refreshing = true;
        lastError = "";
        pendingLocalBranches = [];
        pendingRemoteBranches = [];
        resetTopologyBuild();
        refreshWatchdog.restart();

        refreshProcess.exec([
            "bash",
            "-lc",
            [
                'repo="$1"',
                'if [ -z "$repo" ]; then repo="$HOME/.config/quickshell"; fi',
                'if ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then',
                '  printf "ERROR\\tNOT A GIT REPOSITORY\\n"',
                '  printf "DONE\\t\\n"',
                '  exit 0',
                'fi',
                'root="$(git -C "$repo" rev-parse --show-toplevel)"',
                'name="$(basename "$root")"',
                'branch="$(git -C "$root" branch --show-current)"',
                'if [ -z "$branch" ]; then branch="DETACHED"; fi',
                'head="$(git -C "$root" rev-parse --short=10 HEAD)"',
                'count="$(git -C "$root" status --porcelain=v1 | wc -l | tr -d " ")"',
                'if [ "$count" -eq 0 ]; then worktree="CLEAN"; else worktree="DIRTY • $count CHANGES"; fi',
                'origin="$(git -C "$root" remote get-url origin 2>/dev/null || true)"',
                'if [ -z "$origin" ]; then origin="NO ORIGIN"; fi',
                'upstream="$(git -C "$root" rev-parse --abbrev-ref --symbolic-full-name "@{u}" 2>/dev/null || true)"',
                'ahead=0',
                'behind=0',
                'if [ -n "$upstream" ]; then',
                '  counts="$(git -C "$root" rev-list --left-right --count HEAD..."$upstream" 2>/dev/null || printf "0 0")"',
                '  ahead="$(printf "%s" "$counts" | cut -f1)"',
                '  behind="$(printf "%s" "$counts" | cut -f2)"',
                'fi',
                'printf "ROOT\\t%s\\n" "$root"',
                'printf "REPO\\t%s\\n" "$name"',
                'printf "BRANCH\\t%s\\n" "$branch"',
                'printf "HEAD\\t%s\\n" "$head"',
                'printf "WORKTREE\\t%s\\n" "$worktree"',
                'printf "ORIGIN\\t%s\\n" "$origin"',
                'printf "UPSTREAM\\t%s\\n" "$upstream"',
                'printf "AHEAD\\t%s\\n" "$ahead"',
                'printf "BEHIND\\t%s\\n" "$behind"',
                'while IFS= read -r ref; do',
                '  [ -n "$ref" ] && printf "LOCALBRANCH\\t%s\\n" "$ref"',
                'done < <(git -C "$root" for-each-ref --format="%(refname:short)" refs/heads 2>/dev/null)',
                'while IFS= read -r ref; do',
                '  [ -z "$ref" ] && continue',
                '  [ "$ref" = "origin/HEAD" ] && continue',
                '  printf "REMOTEBRANCH\\t%s\\n" "$ref"',
                'done < <(git -C "$root" for-each-ref --format="%(refname:short)" refs/remotes/origin 2>/dev/null)',
                'git -C "$root" log --all --topo-order --date-order -n 48 --pretty=format:"COMMIT%x09%H%x09%P%x09%D%x09%s"',
                'printf "\\nDONE\\t\\n"'
            ].join("\n"),
            "pa-git-refresh",
            repoPath
        ]);
    }

    function consumeRefreshLine(line) {
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

        if (key === "ROOT") {
            repoRoot = value;
            if (!repoPath)
                repoPath = value;
        } else if (key === "REPO")
            repository = value;
        else if (key === "BRANCH")
            branch = value;
        else if (key === "HEAD")
            head = value;
        else if (key === "WORKTREE")
            worktree = value;
        else if (key === "ORIGIN")
            origin = value;
        else if (key === "UPSTREAM")
            upstream = value;
        else if (key === "AHEAD")
            ahead = Number(value || 0);
        else if (key === "BEHIND")
            behind = Number(value || 0);
        else if (key === "LOCALBRANCH")
            pendingLocalBranches.push(value);
        else if (key === "REMOTEBRANCH")
            pendingRemoteBranches.push(value);
        else if (key === "ERROR") {
            available = false;
            lastError = value;
        } else if (key === "DONE") {
            refreshing = false;
            refreshWatchdog.stop();
            publishPendingModels();
            ensureRemoteSelection();
            topologyRevision += 1;

            if (!lastError) {
                available = true;
                refreshed();
            }

            if (refreshPending) {
                refreshPending = false;
                Qt.callLater(function() {
                    refresh();
                });
            }
        }
    }

    function runReadAction(kind) {
        runAction(String(kind || "").toLowerCase());
    }

    function runSyncAction(kind) {
        runAction(String(kind || "").toLowerCase());
    }

    function runAction(kind) {
        if (actionBusy)
            return;

        const action = String(kind || "").toLowerCase();
        const allowed = ["status", "diff", "log", "fetch", "pull", "push"];

        if (allowed.indexOf(action) < 0)
            return;

        if ((action === "pull" || action === "push") && !selectedRemoteBranch) {
            actionTitle = action.toUpperCase();
            actionOutput = "Choose a remote branch first.";
            actionExitCode = 1;
            return;
        }

        actionBusy = true;
        actionTitle = action.toUpperCase();
        actionOutput = "";
        actionExitCode = 0;
        actionWatchdog.restart();

        actionProcess.exec([
            "bash",
            "-lc",
            [
                'repo="$1"',
                'kind="$2"',
                'target="$3"',
                'if [ -z "$repo" ]; then repo="$HOME/.config/quickshell"; fi',
                'if ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then',
                '  printf "NOT A GIT REPOSITORY\\n"',
                '  printf "__PA_RC__\\t1\\n"',
                '  printf "__PA_DONE__\\n"',
                '  exit 0',
                'fi',
                'rc=0',
                'case "$kind" in',
                '  status)',
                '    git -C "$repo" status --short --branch || rc=$?',
                '    ;;',
                '  diff)',
                '    output="$(git -C "$repo" diff --stat; git -C "$repo" diff --name-status)"',
                '    if [ -n "$output" ]; then printf "%s\\n" "$output"; else printf "NO UNSTAGED DIFF\\n"; fi',
                '    ;;',
                '  log)',
                '    git -C "$repo" log --oneline --decorate -n 20 || rc=$?',
                '    ;;',
                '  fetch)',
                '    printf "FETCH // updating remote branch map from origin\\n"',
                '    git -C "$repo" fetch --prune origin || rc=$?',
                '    ;;',
                '  pull)',
                '    remote="${target%%/*}"',
                '    remote_branch="${target#*/}"',
                '    printf "PULL // %s -> current local branch\\n" "$target"',
                '    git -C "$repo" fetch --prune "$remote" || rc=$?',
                '    if [ "$rc" -eq 0 ]; then',
                '      git -C "$repo" pull --ff-only "$remote" "$remote_branch" || rc=$?',
                '    fi',
                '    ;;',
                '  push)',
                '    remote="${target%%/*}"',
                '    remote_branch="${target#*/}"',
                '    if git -C "$repo" show-ref --verify --quiet "refs/remotes/$target"; then',
                '      printf "PUSH // current local branch -> %s\\n" "$target"',
                '    else',
                '      printf "CREATE REMOTE BRANCH // %s\\n" "$target"',
                '    fi',
                '    git -C "$repo" push -u "$remote" "HEAD:$remote_branch" || rc=$?',
                '    ;;',
                'esac',
                'printf "__PA_RC__\\t%s\\n" "$rc"',
                'printf "__PA_DONE__\\n"'
            ].join("\n"),
            "pa-git-action",
            repoPath,
            action,
            selectedRemoteBranch
        ]);
    }

    function consumeActionLine(line) {
        const raw = String(line || "");

        if (raw.indexOf("__PA_RC__\t") === 0) {
            actionExitCode = Number(raw.slice("__PA_RC__\t".length) || 0);
            return;
        }

        if (raw === "__PA_DONE__") {
            actionBusy = false;
            actionWatchdog.stop();
            refresh();
            return;
        }

        if (actionOutput.length > 12000)
            return;

        actionOutput += (actionOutput.length > 0 ? "\n" : "") + raw;
    }

    function launchLazygit() {
        Quickshell.execDetached([
            "bash",
            "-lc",
            [
                'repo="$1"',
                'if [ -z "$repo" ]; then repo="$HOME/.config/quickshell"; fi',
                'cd "$repo" || exit 1',
                'exec kitty --directory "$PWD" toolbox run -c fedora-toolbox-44 lazygit'
            ].join("\n"),
            "pa-lazygit",
            repoPath
        ]);
    }

    Process {
        id: repoScanProcess

        stdout: SplitParser {
            onRead: function(line) {
                gitService.consumeRepoLine(line);
            }
        }

        stderr: SplitParser {
            onRead: function(line) {
                const message = String(line || "").trim();
                if (message)
                    gitService.lastError = message;
            }
        }
    }

    Process {
        id: refreshProcess

        stdout: SplitParser {
            onRead: function(line) {
                gitService.consumeRefreshLine(line);
            }
        }

        stderr: SplitParser {
            onRead: function(line) {
                const message = String(line || "").trim();
                if (message.length > 0)
                    gitService.lastError = message;
            }
        }
    }

    Process {
        id: actionProcess

        stdout: SplitParser {
            onRead: function(line) {
                gitService.consumeActionLine(line);
            }
        }

        stderr: SplitParser {
            onRead: function(line) {
                const message = String(line || "").trim();

                if (message.length > 0)
                    gitService.actionOutput += (
                        gitService.actionOutput.length > 0 ? "\n" : ""
                    ) + "ERR: " + message;
            }
        }
    }

    Timer {
        id: refreshWatchdog
        interval: 6000
        repeat: false

        onTriggered: {
            gitService.refreshing = false;
            gitService.available = false;
            gitService.lastError = "GIT READ TIMEOUT";
            gitService.topologyRevision += 1;
        }
    }

    Timer {
        id: actionWatchdog
        interval: 15000
        repeat: false

        onTriggered: {
            gitService.actionBusy = false;
            gitService.actionExitCode = 1;
            gitService.actionOutput += (
                gitService.actionOutput.length > 0 ? "\n" : ""
            ) + "ACTION TIMEOUT";
        }
    }

    Component.onCompleted: discoverRepos()
}
