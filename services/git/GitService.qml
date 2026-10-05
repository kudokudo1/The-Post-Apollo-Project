import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: gitService

    property bool available: false
    property bool refreshing: false
    property bool refreshPending: false
    property string refreshRepoPath: ""
    property bool discoveringRepos: false
    property bool actionBusy: false

    property string pullMode: "ff-only"
    readonly property string pullModeLabel:
        pullMode === "ff-only" ? "FF" : "MRG"
    readonly property string pullModeIcon:
        pullMode === "ff-only" ? "⏭" : "⇄"

    property string pullSourceMode: "upstream"
    readonly property string pullSourceLabel:
        pullSourceMode === "upstream" ? "UP" : "TGT"
    readonly property string selectedLocalMatchingRemote:
        selectedLocalBranch
        && remoteIndexOf("origin/" + selectedLocalBranch) >= 0
        ? "origin/" + selectedLocalBranch
        : ""

    readonly property string pullSourceTarget:
        pullSourceMode === "upstream"
        ? (selectedLocalUpstream || selectedLocalMatchingRemote)
        : selectedRemoteBranch
    readonly property bool pullSourceTargetValid:
        isRemoteBranchTarget(pullSourceTarget)

    property string repoPath: ""
    property string repoLabel: "LIVE QUICKSHELL"
    property string preferredRepoQuery: ""
    property string repoRoot: ""
    property string repository: "NOT CONNECTED"
    property string branch: "NOT CONNECTED"
    property string head: "NOT CONNECTED"
    property string headFull: "NOT CONNECTED"
    property string worktree: "NOT CONNECTED"
    property string origin: "NOT CONNECTED"
    property string upstream: ""
    property int ahead: 0
    property int behind: 0

    // Selecting a local branch here is a target selection, not a checkout.
    // This keeps the self-hosted LIVE QUICKSHELL UI from replacing itself.
    property string selectedLocalBranch: ""
    property string selectedLocalHead: ""
    property string selectedLocalUpstream: ""
    property int selectedLocalIndex: -1

    property string selectedRemoteBranch: ""
    property bool selectedRemoteExists: false
    property int selectedRemoteIndex: -1

    readonly property bool selectedRemoteTargetValid:
        isRemoteBranchTarget(selectedRemoteBranch)

    property int maxLane: 0
    property int topologyRevision: 0
    property var activeLanes: []
    property var pendingLocalBranches: []
    property var pendingRemoteBranches: []
    property var pendingTopology: []
    property string pendingRepoRoot: ""
    property string pendingRepository: ""
    property string pendingBranch: ""
    property string pendingHead: ""
    property string pendingHeadFull: ""
    property string pendingWorktree: ""
    property string pendingOrigin: ""
    property string pendingUpstream: ""
    property int pendingAhead: 0
    property int pendingBehind: 0

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

    function localIndexOf(name) {
        const needle = String(name || "");
        for (let i = 0; i < localBranchRows.count; ++i) {
            if (String(localBranchRows.get(i).name) === needle)
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

    function isRemoteBranchTarget(value) {
        const target = String(value || "").trim();
        const slash = target.indexOf("/");

        return slash > 0 && slash < target.length - 1;
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

                if (index < 0 && preferredRepoQuery) {
                    const needle =
                        String(preferredRepoQuery || "").trim().toLowerCase();

                    for (let i = 0; i < repoRows.count; ++i) {
                        const row = repoRows.get(i);
                        const label = String(row.label || "").toLowerCase();
                        const pathValue = String(row.path || "").toLowerCase();

                        if (label === needle
                                || pathValue.endsWith("/" + needle)) {
                            index = i;
                            break;
                        }
                    }
                }

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
        selectedLocalBranch = "";
        selectedLocalHead = "";
        selectedLocalUpstream = "";
        selectedLocalIndex = -1;

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

    function setLocalSelection(index) {
        const row = localBranchAt(index);
        if (!row)
            return false;

        selectedLocalIndex = index;
        selectedLocalBranch = String(row.name || "");
        selectedLocalHead = String(row.head || "");
        selectedLocalUpstream = String(row.upstream || "");
        return true;
    }

    function ensureLocalSelection() {
        let index = localIndexOf(selectedLocalBranch);

        if (index < 0)
            index = localIndexOf(branch);

        if (index < 0 && localBranchRows.count > 0)
            index = 0;

        if (index >= 0)
            setLocalSelection(index);
        else {
            selectedLocalIndex = -1;
            selectedLocalBranch = "";
            selectedLocalHead = "";
            selectedLocalUpstream = "";
        }
    }

    function selectLocal(index) {
        if (actionBusy || refreshing)
            return false;

        if (!setLocalSelection(index))
            return false;

        actionTitle = "LOCAL TARGET";
        actionExitCode = 0;
        actionOutput =
            "SELECTED LOCAL TARGET // " + selectedLocalBranch
            + "\nNo checkout occurred. Working files were not changed.";
        return true;
    }

    function cycleLocal(delta) {
        if (localBranchRows.count <= 0 || actionBusy || refreshing)
            return;

        let index = selectedLocalIndex;

        if (index < 0)
            index = localIndexOf(branch);

        if (index < 0)
            index = 0;
        else
            index = (index + Number(delta || 0) + localBranchRows.count)
                    % localBranchRows.count;

        selectLocal(index);
    }

    function selectLocalText(query) {
        const needle = String(query || "").trim().toLowerCase();

        if (!needle)
            return false;

        let partialIndex = -1;

        for (let i = 0; i < localBranchRows.count; ++i) {
            const row = localBranchRows.get(i);
            const name = String(row.name || "");
            const lowerName = name.toLowerCase();

            if (lowerName === needle)
                return selectLocal(i);

            if (partialIndex < 0 && lowerName.indexOf(needle) >= 0)
                partialIndex = i;
        }

        if (partialIndex >= 0)
            return selectLocal(partialIndex);

        actionTitle = "LOCAL TARGET";
        actionExitCode = 1;
        actionOutput = "NO LOCAL BRANCH MATCH // " + String(query || "")
                     + "\nChoose an existing local branch.";
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

        if (value === "origin" && branch && branch !== "DETACHED")
            value = "origin/" + branch;
        else if (value.indexOf("/") < 0)
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
        repoRoot = pendingRepoRoot;
        repository = pendingRepository;
        branch = pendingBranch;
        head = pendingHead;
        headFull = pendingHeadFull;
        worktree = pendingWorktree;
        origin = pendingOrigin;
        upstream = pendingUpstream;
        ahead = pendingAhead;
        behind = pendingBehind;

        localBranchRows.clear();
        remoteBranchRows.clear();
        topologyRows.clear();

        for (let i = 0; i < pendingLocalBranches.length; ++i) {
            const localRow = pendingLocalBranches[i] || {};
            localBranchRows.append({
                name: String(localRow.name || ""),
                head: String(localRow.head || ""),
                upstream: String(localRow.upstream || "")
            });
        }

        for (let i = 0; i < pendingRemoteBranches.length; ++i) {
            const remoteName = String(pendingRemoteBranches[i] || "");

            if (!isRemoteBranchTarget(remoteName))
                continue;

            remoteBranchRows.append({ name: remoteName });
        }

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
        if (selectedRemoteBranch && isRemoteBranchTarget(selectedRemoteBranch)) {
            selectedRemoteExists = remoteIndexOf(selectedRemoteBranch) >= 0;

            if (selectedRemoteExists) {
                selectedRemoteIndex = remoteIndexOf(selectedRemoteBranch);
                return;
            }
        } else {
            selectedRemoteBranch = "";
            selectedRemoteExists = false;
            selectedRemoteIndex = -1;
        }

        if (upstream
                && isRemoteBranchTarget(upstream)
                && remoteIndexOf(upstream) >= 0) {
            selectedRemoteBranch = upstream;
            selectedRemoteExists = true;
            selectedRemoteIndex = remoteIndexOf(upstream);
            return;
        }

        const matching = branch && branch !== "DETACHED"
            ? "origin/" + branch
            : "";

        if (matching && remoteIndexOf(matching) >= 0) {
            selectedRemoteBranch = matching;
            selectedRemoteExists = true;
            selectedRemoteIndex = remoteIndexOf(matching);
            return;
        }

        if (remoteBranchRows.count > 0) {
            selectedRemoteIndex = 0;
            selectedRemoteBranch = String(remoteBranchRows.get(0).name || "");
            selectedRemoteExists = isRemoteBranchTarget(selectedRemoteBranch);
            return;
        }

        selectedRemoteBranch = matching;
        selectedRemoteExists = false;
        selectedRemoteIndex = -1;
    }

    function refresh() {
        if (refreshing)
            return;

        refreshing = true;
        refreshRepoPath = repoPath;
        lastError = "";
        pendingLocalBranches = [];
        pendingRemoteBranches = [];
        pendingRepoRoot = "";
        pendingRepository = "";
        pendingBranch = "";
        pendingHead = "";
        pendingHeadFull = "";
        pendingWorktree = "";
        pendingOrigin = "";
        pendingUpstream = "";
        pendingAhead = 0;
        pendingBehind = 0;
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
                'head_full="$(git -C "$root" rev-parse HEAD)"',
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
                'printf "HEADFULL\\t%s\\n" "$head_full"',
                'printf "WORKTREE\\t%s\\n" "$worktree"',
                'printf "ORIGIN\\t%s\\n" "$origin"',
                'printf "UPSTREAM\\t%s\\n" "$upstream"',
                'printf "AHEAD\\t%s\\n" "$ahead"',
                'printf "BEHIND\\t%s\\n" "$behind"',
                'while IFS=
                'while IFS= read -r ref; do',
                '  [ -z "$ref" ] && continue',
                '  [ "$ref" = "origin" ] && continue',
                '  [ "$ref" = "origin/HEAD" ] && continue',
                '  case "$ref" in */*) ;; *) continue ;; esac',
                '  printf "REMOTEBRANCH\\t%s\\n" "$ref"',
                'done < <(git -C "$root" for-each-ref --format="%(refname:short)" refs/remotes/origin 2>/dev/null)',
                'git -C "$root" log --all --topo-order --date-order -n 48 --pretty=format:"COMMIT%x09%H%x09%P%x09%D%x09%s"',
                'printf "\\nDONE\\t\\n"'
            ].join("\n"),
            "pa-git-refresh",
            refreshRepoPath
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

        if (key === "ROOT")
            pendingRepoRoot = value;
        else if (key === "REPO")
            pendingRepository = value;
        else if (key === "BRANCH")
            pendingBranch = value;
        else if (key === "HEAD")
            pendingHead = value;
        else if (key === "HEADFULL")
            pendingHeadFull = value;
        else if (key === "WORKTREE")
            pendingWorktree = value;
        else if (key === "ORIGIN")
            pendingOrigin = value;
        else if (key === "UPSTREAM")
            pendingUpstream = value;
        else if (key === "AHEAD")
            pendingAhead = Number(value || 0);
        else if (key === "BEHIND")
            pendingBehind = Number(value || 0);
        else if (key === "LOCALBRANCH")
            pendingLocalBranches.push({
                name: parts.length > 1 ? parts[1] : "",
                head: parts.length > 2 ? parts[2] : "",
                upstream: parts.length > 3 ? parts[3] : ""
            });
        else if (key === "REMOTEBRANCH")
            pendingRemoteBranches.push(value);
        else if (key === "ERROR") {
            available = false;
            lastError = value;
        } else if (key === "DONE") {
            const staleRead = refreshRepoPath !== repoPath;

            refreshing = false;
            refreshWatchdog.stop();

            if (!staleRead && !lastError) {
                publishPendingModels();
                ensureLocalSelection();
                ensureRemoteSelection();
                topologyRevision += 1;
                available = true;
                refreshed();
            }

            if (refreshPending || staleRead) {
                refreshPending = false;
                Qt.callLater(function() {
                    refresh();
                });
            }
        }
    }

    function describePullMode() {
        actionTitle = "PULL MODE";
        actionExitCode = 0;

        if (pullMode === "ff-only") {
            actionOutput =
                "PULL MODE // FF ONLY"
                + "\nFast-forward the selected LOCAL TARGET when history is clean."
                + "\nThis does not checkout that branch or replace the working files."
                + "\nIf Git would need a merge, Pull stops instead.";
        } else {
            actionOutput =
                "PULL MODE // MERGE"
                + "\nPull the selected remote branch and merge divergent history."
                + "\nThis mode can create a merge commit or leave conflicts to resolve."
                + "\nNothing was changed yet.";
        }
    }

    function cyclePullMode() {
        pullMode = pullMode === "ff-only" ? "merge" : "ff-only";
        describePullMode();
    }

    function cyclePullSource() {
        pullSourceMode =
            pullSourceMode === "upstream"
            ? "target"
            : "upstream";

        actionTitle = "PULL SOURCE";
        actionExitCode = 0;

        if (pullSourceMode === "upstream") {
            actionOutput =
                pullSourceTargetValid
                ? "PULL SOURCE // UPSTREAM\n" + pullSourceTarget
                : "PULL SOURCE // UPSTREAM\nNO MATCHING REMOTE FOR SELECTED LOCAL TARGET";
        } else {
            actionOutput =
                pullSourceTargetValid
                ? "PULL SOURCE // TARGET\n" + pullSourceTarget
                : "PULL SOURCE // TARGET\nCHOOSE A REMOTE TARGET ABOVE";
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
        const localTarget = selectedLocalBranch || branch;
        const syncTarget =
            action === "pull"
            ? pullSourceTarget
            : selectedRemoteBranch;

        if (allowed.indexOf(action) < 0)
            return;

        if (action === "pull" && !isRemoteBranchTarget(syncTarget)) {
            actionTitle = "PULL";
            actionOutput =
                pullSourceMode === "upstream"
                ? "PULL SOURCE // UPSTREAM\nNo matching remote is configured for the selected local target."
                : "PULL SOURCE // TARGET\nChoose a remote branch target first.";
            actionExitCode = 1;
            return;
        }

        if (action === "push" && !isRemoteBranchTarget(selectedRemoteBranch)) {
            actionTitle = "PUSH";
            actionOutput =
                "Choose a remote branch target first."
                + "\nExample // origin/" + String(localTarget || "main")
                + "\nA remote name by itself is not a branch.";
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
                'pull_mode="$4"',
                'local_target="$5"',
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
                '    current_branch="$(git -C "$repo" branch --show-current)"',
                '    git -C "$repo" fetch --prune "$remote" || rc=$?',
                '    if [ "$rc" -eq 0 ]; then',
                '      if [ "$local_target" = "$current_branch" ]; then',
                '        case "$pull_mode" in',
                '          ff-only)',
                '            printf "PULL // FF ONLY // %s -> checked-out %s\\n" "$target" "$local_target"',
                '            git -C "$repo" pull --ff-only "$remote" "$remote_branch" || rc=$?',
                '            ;;',
                '          merge)',
                '            printf "PULL // MERGE // %s -> checked-out %s\\n" "$target" "$local_target"',
                '            git -C "$repo" pull --no-rebase "$remote" "$remote_branch" || rc=$?',
                '            ;;',
                '        esac',
                '      elif [ "$pull_mode" = "ff-only" ]; then',
                '        printf "SYNC LOCAL TARGET // %s -> %s // NO CHECKOUT\\n" "$target" "$local_target"',
                '        if git -C "$repo" merge-base --is-ancestor "$local_target" "$target"; then',
                '          git -C "$repo" branch -f "$local_target" "$target" || rc=$?',
                '        else',
                '          printf "PULL STOPPED // %s cannot fast-forward to %s\\n" "$local_target" "$target"',
                '          rc=1',
                '        fi',
                '      else',
                '        printf "BACKGROUND MERGE REFUSED // %s is not checked out\\n" "$local_target"',
                '        printf "Use FF mode, or explicitly checkout the branch before a merge-mode pull.\\n"',
                '        rc=1',
                '      fi',
                '    fi',
                '    ;;',
                '  push)',
                '    remote="${target%%/*}"',
                '    remote_branch="${target#*/}"',
                '    if git -C "$repo" show-ref --verify --quiet "refs/remotes/$target"; then',
                '      printf "PUSH // %s -> %s\\n" "$local_target" "$target"',
                '    else',
                '      printf "CREATE REMOTE BRANCH // %s -> %s\\n" "$local_target" "$target"',
                '    fi',
                '    git -C "$repo" push -u "$remote" "$local_target:$remote_branch" || rc=$?',
                '    ;;',
                'esac',
                'printf "__PA_RC__\\t%s\\n" "$rc"',
                'printf "__PA_DONE__\\n"'
            ].join("\n"),
            "pa-git-action",
            repoPath,
            action,
            syncTarget,
            pullMode,
            localTarget
        ]);
    }

    function friendlyActionError(message) {
        const raw = String(message || "").trim();
        const lower = raw.toLowerCase();

        if (
            actionTitle === "PULL"
            && (
                lower.indexOf("not possible to fast-forward") >= 0
                || lower.indexOf("not possible to fast forward") >= 0
                || lower.indexOf("divergent") >= 0
                || lower.indexOf("non-fast-forward") >= 0
            )
        ) {
            return "PULL STOPPED // branches have diverged"
                 + "\nFAST-FORWARD ONLY // no merge was created"
                 + "\nOpen Lazygit or choose a deliberate merge/rebase operation.";
        }

        if (
            actionTitle === "PULL"
            && (
                lower.indexOf("couldn't find remote ref") >= 0
                || lower.indexOf("could not find remote ref") >= 0
            )
        ) {
            return "PULL STOPPED // remote branch was not found"
                 + "\nChoose an existing remote target and try again.";
        }

        return "ERR: " + raw;
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
                    ) + gitService.friendlyActionError(message);
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
\''\\t'\'' read -r ref ref_head ref_upstream; do',
                '  [ -n "$ref" ] && printf "LOCALBRANCH\\t%s\\t%s\\t%s\\n" "$ref" "$ref_head" "$ref_upstream"',
                'done < <(git -C "$root" for-each-ref --format="%(refname:short)%09%(objectname:short=10)%09%(upstream:short)" refs/heads 2>/dev/null)',
                'while IFS= read -r ref; do',
                '  [ -z "$ref" ] && continue',
                '  [ "$ref" = "origin" ] && continue',
                '  [ "$ref" = "origin/HEAD" ] && continue',
                '  case "$ref" in */*) ;; *) continue ;; esac',
                '  printf "REMOTEBRANCH\\t%s\\n" "$ref"',
                'done < <(git -C "$root" for-each-ref --format="%(refname:short)" refs/remotes/origin 2>/dev/null)',
                'git -C "$root" log --all --topo-order --date-order -n 48 --pretty=format:"COMMIT%x09%H%x09%P%x09%D%x09%s"',
                'printf "\\nDONE\\t\\n"'
            ].join("\n"),
            "pa-git-refresh",
            refreshRepoPath
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

        if (key === "ROOT")
            pendingRepoRoot = value;
        else if (key === "REPO")
            pendingRepository = value;
        else if (key === "BRANCH")
            pendingBranch = value;
        else if (key === "HEAD")
            pendingHead = value;
        else if (key === "HEADFULL")
            pendingHeadFull = value;
        else if (key === "WORKTREE")
            pendingWorktree = value;
        else if (key === "ORIGIN")
            pendingOrigin = value;
        else if (key === "UPSTREAM")
            pendingUpstream = value;
        else if (key === "AHEAD")
            pendingAhead = Number(value || 0);
        else if (key === "BEHIND")
            pendingBehind = Number(value || 0);
        else if (key === "LOCALBRANCH")
            pendingLocalBranches.push(value);
        else if (key === "REMOTEBRANCH")
            pendingRemoteBranches.push(value);
        else if (key === "ERROR") {
            available = false;
            lastError = value;
        } else if (key === "DONE") {
            const staleRead = refreshRepoPath !== repoPath;

            refreshing = false;
            refreshWatchdog.stop();

            if (!staleRead && !lastError) {
                publishPendingModels();
                ensureRemoteSelection();
                topologyRevision += 1;
                available = true;
                refreshed();
            }

            if (refreshPending || staleRead) {
                refreshPending = false;
                Qt.callLater(function() {
                    refresh();
                });
            }
        }
    }

    function describePullMode() {
        actionTitle = "PULL MODE";
        actionExitCode = 0;

        if (pullMode === "ff-only") {
            actionOutput =
                "PULL MODE // FF ONLY"
                + "\nFast-forward the current local branch when history is clean."
                + "\nIf Git would need a merge, Pull stops instead."
                + "\nNothing was changed.";
        } else {
            actionOutput =
                "PULL MODE // MERGE"
                + "\nPull the selected remote branch and merge divergent history."
                + "\nThis mode can create a merge commit or leave conflicts to resolve."
                + "\nNothing was changed yet.";
        }
    }

    function cyclePullMode() {
        pullMode = pullMode === "ff-only" ? "merge" : "ff-only";
        describePullMode();
    }

    function cyclePullSource() {
        pullSourceMode =
            pullSourceMode === "upstream"
            ? "target"
            : "upstream";

        actionTitle = "PULL SOURCE";
        actionExitCode = 0;

        if (pullSourceMode === "upstream") {
            actionOutput =
                pullSourceTargetValid
                ? "PULL SOURCE // UPSTREAM\n" + pullSourceTarget
                : "PULL SOURCE // UPSTREAM\nNO TRACKING BRANCH AVAILABLE";
        } else {
            actionOutput =
                pullSourceTargetValid
                ? "PULL SOURCE // TARGET\n" + pullSourceTarget
                : "PULL SOURCE // TARGET\nCHOOSE A REMOTE TARGET ABOVE";
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
        const syncTarget =
            action === "pull"
            ? pullSourceTarget
            : selectedRemoteBranch;

        if (allowed.indexOf(action) < 0)
            return;

        if (action === "pull" && !isRemoteBranchTarget(syncTarget)) {
            actionTitle = "PULL";
            actionOutput =
                pullSourceMode === "upstream"
                ? "PULL SOURCE // UPSTREAM\nNo tracking branch is configured for this local branch."
                : "PULL SOURCE // TARGET\nChoose a remote branch target first.";
            actionExitCode = 1;
            return;
        }

        if (action === "push" && !isRemoteBranchTarget(selectedRemoteBranch)) {
            actionTitle = "PUSH";
            actionOutput =
                "Choose a remote branch target first."
                + "\nExample // origin/" + String(branch || "main")
                + "\nA remote name by itself is not a branch.";
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
                'pull_mode="$4"',
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
                '    case "$pull_mode" in',
                '      ff-only)',
                '        printf "PULL // FF ONLY // %s -> current local branch\\n" "$target"',
                '        git -C "$repo" fetch --prune "$remote" || rc=$?',
                '        if [ "$rc" -eq 0 ]; then',
                '          git -C "$repo" pull --ff-only "$remote" "$remote_branch" || rc=$?',
                '        fi',
                '        ;;',
                '      merge)',
                '        printf "PULL // MERGE // %s -> current local branch\\n" "$target"',
                '        git -C "$repo" fetch --prune "$remote" || rc=$?',
                '        if [ "$rc" -eq 0 ]; then',
                '          git -C "$repo" pull --no-rebase "$remote" "$remote_branch" || rc=$?',
                '        fi',
                '        ;;',
                '      *)',
                '        printf "UNKNOWN PULL MODE // %s\\n" "$pull_mode"',
                '        rc=2',
                '        ;;',
                '    esac',
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
            syncTarget,
            pullMode
        ]);
    }

    function friendlyActionError(message) {
        const raw = String(message || "").trim();
        const lower = raw.toLowerCase();

        if (
            actionTitle === "PULL"
            && (
                lower.indexOf("not possible to fast-forward") >= 0
                || lower.indexOf("not possible to fast forward") >= 0
                || lower.indexOf("divergent") >= 0
                || lower.indexOf("non-fast-forward") >= 0
            )
        ) {
            return "PULL STOPPED // branches have diverged"
                 + "\nFAST-FORWARD ONLY // no merge was created"
                 + "\nOpen Lazygit or choose a deliberate merge/rebase operation.";
        }

        if (
            actionTitle === "PULL"
            && (
                lower.indexOf("couldn't find remote ref") >= 0
                || lower.indexOf("could not find remote ref") >= 0
            )
        ) {
            return "PULL STOPPED // remote branch was not found"
                 + "\nChoose an existing remote target and try again.";
        }

        if (
            actionTitle === "SWITCH"
            && (
                lower.indexOf("would be overwritten by checkout") >= 0
                || lower.indexOf("would be overwritten by switch") >= 0
                || lower.indexOf("please commit your changes") >= 0
                || lower.indexOf("please stash them") >= 0
            )
        ) {
            return "SWITCH STOPPED // LOCAL CHANGES WOULD BE AFFECTED"
                 + "\nCommit, stash, or discard those changes first.";
        }

        return "ERR: " + raw;
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
                    ) + gitService.friendlyActionError(message);
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
