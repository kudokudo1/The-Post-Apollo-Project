import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: gitService

    property var operationJournal: null
    property var snapshotService: null

    property bool available: false
    property bool refreshing: false
    property bool refreshPending: false
    property string refreshRepoPath: ""
    property bool discoveringRepos: false
    property bool actionBusy: false
    property string clonePendingQuery: ""

    property string pullMode: "ff-only"
    readonly property string pullModeLabel:
        pullMode === "ff-only" ? "FF" : "MRG"
    readonly property string pullModeIcon:
        pullMode === "ff-only" ? "⏭" : "⇄"

    property string pullSourceMode: "upstream"
    readonly property string pullSourceLabel:
        localTrackCheckoutMode
        ? "TRACK"
        : pullSourceMode === "upstream" ? "UP" : "TGT"
    readonly property string selectedLocalMatchingRemote:
        selectedLocalBranch
        && remoteIndexOf("origin/" + selectedLocalBranch) >= 0
        ? "origin/" + selectedLocalBranch
        : ""

    readonly property string pullSourceTarget:
        localTrackCheckoutMode
        ? selectedRemoteBranch
        : pullSourceMode === "upstream"
        ? (selectedLocalUpstream || selectedLocalMatchingRemote)
        : selectedRemoteBranch
    readonly property bool pullSourceTargetValid:
        isRemoteBranchTarget(pullSourceTarget)

    property string repoPath: ""
    property string repoLabel: "LIVE QUICKSHELL"
    property string repoRemoteUrl: ""
    property string repoRemoteSlug: ""
    property bool repoIsLocal: true
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
    property bool localTrackCheckoutMode: false

    readonly property string localTargetDisplay:
        localTrackCheckoutMode
        ? "TRACK // CHECKOUT REMOTE"
        : selectedLocalBranch

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

    property string pendingJournalId: ""
    property string pendingSnapshotRequest: ""
    property string snapshotPhase: ""
    property string pendingProcessAction: ""
    property var pendingActionCommand: []
    property bool pendingActionSuccess: false
    property string pendingActionDetail: ""

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

    // BranchMap Canvas resolves graph parents through these accessors.
    // They are runtime dependencies even though static call-site scans may miss
    // them, so keep both methods paired with topologyRows.
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

    function githubSlugFromUrl(urlValue) {
        let value = String(urlValue || "").trim();

        if (!value)
            return "";

        if (value.indexOf("git@github.com:") === 0)
            value = value.slice("git@github.com:".length);
        else if (value.indexOf("ssh://git@github.com/") === 0)
            value = value.slice("ssh://git@github.com/".length);
        else if (value.indexOf("https://github.com/") === 0)
            value = value.slice("https://github.com/".length);
        else if (value.indexOf("http://github.com/") === 0)
            value = value.slice("http://github.com/".length);
        else
            return "";

        if (value.endsWith(".git"))
            value = value.slice(0, -4);

        return value;
    }

    function repoIndexOfSlug(slugValue) {
        const needle = String(slugValue || "").trim().toLowerCase();

        if (!needle)
            return -1;

        for (let i = 0; i < repoRows.count; ++i) {
            if (String(repoRows.get(i).remoteSlug || "").toLowerCase() === needle)
                return i;
        }

        return -1;
    }

    function applyRepoRow(row) {
        if (!row)
            return;

        repoPath = String(row.path || "");
        repoLabel = String(row.label || "REPOSITORY");
        repoRemoteUrl = String(row.remoteUrl || "");
        repoRemoteSlug = String(row.remoteSlug || "");
        repoIsLocal = Boolean(row.isLocal);
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

    function branchSearchKey(value) {
        let text = String(value || "").trim().toLowerCase();

        text = text.replace(/^refs\/remotes\//, "");
        text = text.replace(/^origin\//, "");
        text = text.replace(/[._\/-]+/g, " ");

        const ignored = {
            "origin": true,
            "feature": true,
            "features": true,
            "integration": true,
            "integrate": true,
            "fix": true,
            "bugfix": true,
            "hotfix": true,
            "style": true,
            "styles": true,
            "test": true,
            "tests": true,
            "docs": true,
            "doc": true,
            "chore": true,
            "refactor": true,
            "release": true,
            "branch": true
        };

        const pieces = text.split(/\s+/);
        const meaningful = [];

        for (let i = 0; i < pieces.length; ++i) {
            const piece = String(pieces[i] || "");
            if (piece && !ignored[piece])
                meaningful.push(piece);
        }

        return meaningful.join("");
    }

    function fuzzyBranchScore(query, branchName) {
        const needle = branchSearchKey(query);
        const haystack = branchSearchKey(branchName);

        if (!needle || !haystack)
            return needle ? -1 : 0;

        if (needle === haystack)
            return 10000;

        if (haystack.indexOf(needle) === 0)
            return 8000 - Math.max(0, haystack.length - needle.length);

        const substring = haystack.indexOf(needle);
        if (substring >= 0)
            return 6500 - substring * 12
                         - Math.max(0, haystack.length - needle.length);

        let cursor = 0;
        let previous = -2;
        let score = 1600;
        let consecutive = 0;
        let gaps = 0;

        for (let i = 0; i < needle.length; ++i) {
            const character = needle.charAt(i);
            const found = haystack.indexOf(character, cursor);

            if (found < 0)
                return -1;

            if (found === previous + 1) {
                consecutive += 1;
                score += 55 + consecutive * 4;
            } else {
                consecutive = 0;
                gaps += Math.max(0, found - cursor);
                score -= Math.max(0, found - cursor) * 8;
            }

            previous = found;
            cursor = found + 1;
        }

        score -= Math.max(0, haystack.length - needle.length) * 2;
        score -= gaps * 3;
        return score;
    }

    function fuzzyLocalMatches(query, limit) {
        const matches = [];
        const maxResults = Math.max(1, Number(limit || localBranchRows.count));

        for (let i = 0; i < localBranchRows.count; ++i) {
            const row = localBranchRows.get(i);
            const score = fuzzyBranchScore(query, row.name);

            if (String(query || "").trim() && score < 0)
                continue;

            matches.push({
                originalIndex: i,
                name: String(row.name || ""),
                head: String(row.head || ""),
                upstream: String(row.upstream || ""),
                unpulledCount: Number(row.unpulledCount || 0),
                lastChangedEpoch: Number(row.lastChangedEpoch || 0),
                score: score
            });
        }

        if (String(query || "").trim()) {
            matches.sort(function(a, b) {
                if (a.score !== b.score)
                    return b.score - a.score;
                return a.name.localeCompare(b.name);
            });
        }

        return matches.slice(0, maxResults);
    }

    function fuzzyRemoteMatches(query, limit) {
        const matches = [];
        const maxResults = Math.max(1, Number(limit || remoteBranchRows.count));

        for (let i = 0; i < remoteBranchRows.count; ++i) {
            const row = remoteBranchRows.get(i);
            const score = fuzzyBranchScore(query, row.name);

            if (String(query || "").trim() && score < 0)
                continue;

            matches.push({
                originalIndex: i,
                name: String(row.name || ""),
                unpulledCount: Number(row.unpulledCount || 0),
                remoteOnly: Boolean(row.remoteOnly),
                lastChangedEpoch: Number(row.lastChangedEpoch || 0),
                score: score
            });
        }

        if (String(query || "").trim()) {
            matches.sort(function(a, b) {
                if (a.score !== b.score)
                    return b.score - a.score;
                return a.name.localeCompare(b.name);
            });
        }

        return matches.slice(0, maxResults);
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
                '  root="$(git -C "$live" rev-parse --show-toplevel)"',
                '  origin="$(git -C "$root" remote get-url origin 2>/dev/null || true)"',
                '  printf "REPO\\tLIVE QUICKSHELL\\t%s\\t%s\\n" "$root" "$origin"',
                'fi',
                'for gitdir in "$HOME"/Projects/*/.git; do',
                '  [ -e "$gitdir" ] || continue',
                '  root="${gitdir%/.git}"',
                '  if git -C "$root" rev-parse --is-inside-work-tree >/dev/null 2>&1; then',
                '    name="$(basename "$root")"',
                '    root="$(git -C "$root" rev-parse --show-toplevel)"',
                '    origin="$(git -C "$root" remote get-url origin 2>/dev/null || true)"',
                '    printf "REPO\\t%s\\t%s\\t%s\\n" "$name" "$root" "$origin"',
                '  fi',
                'done',
                'if command -v gh >/dev/null 2>&1; then',
                '  while IFS="$(printf "\\t")" read -r name slug url; do',
                '    [ -n "$slug" ] && printf "REMOTE\\t%s\\t%s\\t%s\\n" "$name" "$slug" "$url"',
                "  done < <(gh repo list --limit 200 --json name,nameWithOwner,url --jq '.[] | [.name, .nameWithOwner, .url] | @tsv')",
                'fi',
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
            const pathValue = parts.length > 2 ? parts[2] : "";
            const remoteUrl = parts.length > 3 ? parts.slice(3).join("\t") : "";
            const remoteSlug = githubSlugFromUrl(remoteUrl);

            if (pathValue && repoIndexOfPath(pathValue) < 0) {
                repoRows.append({
                    label: label,
                    path: pathValue,
                    localPath: pathValue,
                    remoteUrl: remoteUrl,
                    remoteSlug: remoteSlug,
                    isLocal: true
                });
            }
            return;
        }

        if (key === "REMOTE") {
            const label = parts.length > 1 ? parts[1] : "GITHUB REPOSITORY";
            const remoteSlug = parts.length > 2 ? parts[2] : "";
            const remoteUrl = parts.length > 3 ? parts.slice(3).join("\t") : "";
            let index = repoIndexOfSlug(remoteSlug);

            if (index < 0) {
                const lowerLabel = label.toLowerCase();

                for (let i = 0; i < repoRows.count; ++i) {
                    const row = repoRows.get(i);
                    if (String(row.label || "").toLowerCase() === lowerLabel) {
                        index = i;
                        break;
                    }
                }
            }

            if (index >= 0) {
                repoRows.setProperty(index, "remoteUrl", remoteUrl);
                repoRows.setProperty(index, "remoteSlug", remoteSlug);
            } else if (remoteSlug) {
                repoRows.append({
                    label: label,
                    path: "remote://" + remoteSlug,
                    localPath: "",
                    remoteUrl: remoteUrl,
                    remoteSlug: remoteSlug,
                    isLocal: false
                });
            }
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
                        const remoteSlug =
                            String(row.remoteSlug || "").toLowerCase();

                        if (label === needle
                                || pathValue.endsWith("/" + needle)
                                || remoteSlug === needle
                                || remoteSlug.endsWith("/" + needle)) {
                            index = i;
                            break;
                        }
                    }
                }

                if (index < 0)
                    index = 0;

                const row = repoRows.get(index);
                applyRepoRow(row);
            }
            repositoriesChanged();
            refresh();
        }
    }

    function selectRepo(index) {
        const row = repoAt(index);
        if (!row)
            return;

        applyRepoRow(row);
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
            const remoteSlug = String(row.remoteSlug || "");
            const lowerLabel = label.toLowerCase();
            const lowerPath = pathValue.toLowerCase();
            const lowerSlug = remoteSlug.toLowerCase();

            if (lowerLabel === needle
                    || lowerPath === needle
                    || lowerSlug === needle) {
                selectRepo(i);
                return true;
            }

            if (
                partialIndex < 0
                && (
                    lowerLabel.indexOf(needle) >= 0
                    || lowerPath.indexOf(needle) >= 0
                    || lowerSlug.indexOf(needle) >= 0
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

        localTrackCheckoutMode = false;
        selectedLocalIndex = index;
        selectedLocalBranch = String(row.name || "");
        selectedLocalHead = String(row.head || "");
        selectedLocalUpstream = String(row.upstream || "");
        return true;
    }

    function selectTrackCheckoutRemote() {
        if (actionBusy || refreshing)
            return false;

        localTrackCheckoutMode = true;
        selectedLocalIndex = -1;
        selectedLocalBranch = "";
        selectedLocalHead = "";
        selectedLocalUpstream = "";

        actionTitle = "LOCAL TARGET";
        actionExitCode = 0;
        actionOutput =
            "TRACK // CHECKOUT REMOTE"
            + "\nChoose a REMOTE TARGET, then press PULL."
            + "\nPULL will create a matching local tracking branch"
            + " and switch the LIVE checkout onto it.";
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

    function selectLocalText(query) {
        const needle = String(query || "").trim().toLowerCase();

        if (!needle)
            return false;

        if (needle === "track"
                || needle === "checkout"
                || needle === "track checkout"
                || needle === "track // checkout remote")
            return selectTrackCheckoutRemote();

        const matches = fuzzyLocalMatches(query, 1);

        if (matches.length > 0)
            return selectLocal(Number(matches[0].originalIndex));

        actionTitle = "LOCAL TARGET";
        actionExitCode = 1;
        actionOutput = "NO FUZZY LOCAL MATCH // " + String(query || "")
                     + "\nTry any recognizable part of the branch name.";
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

        const exactCandidate =
            value.indexOf("/") >= 0
            ? value
            : "origin/" + value;
        const exactIndex = remoteIndexOf(exactCandidate);

        if (exactIndex >= 0) {
            selectRemote(exactIndex);
            actionTitle = "REMOTE TARGET";
            actionExitCode = 0;
            actionOutput = "SELECTED EXISTING REMOTE // "
                         + selectedRemoteBranch;
            return true;
        }

        const matches = fuzzyRemoteMatches(value, 1);

        if (matches.length > 0) {
            selectRemote(Number(matches[0].originalIndex));
            actionTitle = "REMOTE TARGET";
            actionExitCode = 0;
            actionOutput = "FUZZY REMOTE MATCH // " + value
                         + "\n→ " + selectedRemoteBranch;
            return true;
        }

        if (value === "origin" && branch && branch !== "DETACHED")
            value = "origin/" + branch;
        else if (value.indexOf("/") < 0)
            value = "origin/" + value;

        selectedRemoteBranch = value;
        selectedRemoteExists = false;
        actionTitle = "REMOTE TARGET";
        actionExitCode = 0;
        actionOutput = "REMOTE DOES NOT EXIST YET // " + value
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
                upstream: String(localRow.upstream || ""),
                unpulledCount: Number(localRow.unpulledCount || 0),
                lastChangedEpoch: Number(localRow.lastChangedEpoch || 0)
            });
        }

        for (let i = 0; i < pendingRemoteBranches.length; ++i) {
            const remoteRow = pendingRemoteBranches[i] || {};
            const remoteName = String(remoteRow.name || "");

            if (!isRemoteBranchTarget(remoteName))
                continue;

            remoteBranchRows.append({
                name: remoteName,
                unpulledCount: Number(remoteRow.unpulledCount || 0),
                remoteOnly: Boolean(remoteRow.remoteOnly),
                lastChangedEpoch: Number(remoteRow.lastChangedEpoch || 0)
            });
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

    function appendCommit(sha, parentField, refs, epoch, author, subject) {
        const parentText = String(parentField || "").trim();
        const parents = parentText ? parentText.split(/\s+/) : [];
        const lane = allocateLane(sha, parents);
        const decorated = String(refs || "");

        pendingTopology.push({
            sha: sha,
            shortSha: String(sha).slice(0, 8),
            parents: parents.join(" "),
            refsText: cleanRefs(decorated),
            epoch: Number(epoch || 0),
            author: String(author || ""),
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

        if (!repoIsLocal || String(repoPath || "").indexOf("remote://") === 0) {
            available = false;
            refreshing = false;
            refreshPending = false;
            refreshRepoPath = repoPath;
            lastError = "";
            repoRoot = "REMOTE ONLY";
            repository = repoRemoteSlug
                ? repoRemoteSlug.split("/").pop()
                : repoLabel;
            branch = "NO LOCAL BRANCH";
            head = "NO LOCAL HEAD";
            headFull = "NO LOCAL HEAD";
            worktree = "NO LOCAL BED";
            origin = repoRemoteUrl || (
                repoRemoteSlug
                ? "https://github.com/" + repoRemoteSlug
                : "NO ORIGIN"
            );
            upstream = "";
            ahead = 0;
            behind = 0;
            selectedLocalBranch = "";
            selectedLocalHead = "";
            selectedLocalUpstream = "";
            selectedLocalIndex = -1;
            selectedRemoteBranch = "";
            selectedRemoteExists = false;
            selectedRemoteIndex = -1;
            localBranchRows.clear();
            remoteBranchRows.clear();
            topologyRows.clear();
            topologyRevision += 1;
            actionTitle = "REMOTE REPOSITORY";
            actionExitCode = 0;
            actionOutput =
                "GITHUB REPOSITORY // " + (repoRemoteSlug || repoLabel)
                + "\nNo local checkout is registered on this machine."
                + "\nGitHub controls remain available.";
            refreshed();
            return;
        }

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
                'pending_refs="|"',
                'pending_count=0',
                'while IFS="$(printf "\\t")" read -r ref changed; do',
                '  [ -z "$ref" ] && continue',
                '  [ "$ref" = "origin" ] && continue',
                '  [ "$ref" = "origin/HEAD" ] && continue',
                '  case "$ref" in */*) ;; *) continue ;; esac',
                '  if git -C "$root" cherry HEAD "$ref" 2>/dev/null | grep -q "^+"; then',
                '    pending_refs="${pending_refs}${ref}|"',
                '    pending_count=$((pending_count + 1))',
                '    [ "$pending_count" -ge 5 ] && break',
                '  fi',
                'done < <(git -C "$root" for-each-ref --sort=-committerdate --count=24 --format="%(refname:short)%09%(committerdate:unix)" refs/remotes/origin 2>/dev/null)',
                'while IFS="$(printf "\\t")" read -r ref ref_head ref_upstream; do',
                '  [ -z "$ref" ] && continue',
                '  compare="$ref_upstream"',
                '  if [ -z "$compare" ] && git -C "$root" show-ref --verify --quiet "refs/remotes/origin/$ref"; then compare="origin/$ref"; fi',
                '  unpulled=0',
                '  changed=0',
                '  if [ -n "$compare" ]; then',
                '    case "$pending_refs" in *"|$compare|"*) unpulled=1 ;; esac',
                '    if [ "$unpulled" -gt 0 ]; then changed="$(git -C "$root" show -s --format=%ct "$compare" 2>/dev/null || printf "0")"; fi',
                '  fi',
                '  printf "LOCALBRANCH\\t%s\\t%s\\t%s\\t%s\\t%s\\n" "$ref" "$ref_head" "$ref_upstream" "$unpulled" "$changed"',
                'done < <(git -C "$root" for-each-ref --format="%(refname:short)%09%(objectname:short=10)%09%(upstream:short)" refs/heads 2>/dev/null)',
                'while IFS="$(printf "\\t")" read -r ref changed; do',
                '  [ -z "$ref" ] && continue',
                '  [ "$ref" = "origin" ] && continue',
                '  [ "$ref" = "origin/HEAD" ] && continue',
                '  case "$ref" in */*) ;; *) continue ;; esac',
                '  local_branch="${ref#origin/}"',
                '  remote_only=0',
                '  if ! git -C "$root" show-ref --verify --quiet "refs/heads/$local_branch"; then remote_only=1; fi',
                '  unpulled=0',
                '  case "$pending_refs" in *"|$ref|"*) unpulled=1 ;; esac',
                '  if [ "$unpulled" -eq 0 ]; then changed=0; fi',
                '  printf "REMOTEBRANCH\\t%s\\t%s\\t%s\\t%s\\n" "$ref" "$unpulled" "$remote_only" "$changed"',
                'done < <(git -C "$root" for-each-ref --format="%(refname:short)%09%(committerdate:unix)" refs/remotes/origin 2>/dev/null)',
                'git -C "$root" log --all --topo-order --date-order -n 48 --pretty=format:"COMMIT%x09%H%x09%P%x09%D%x09%ct%x09%an%x09%s"',
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
                parts.length > 4 ? Number(parts[4] || 0) : 0,
                parts.length > 5 ? parts[5] : "",
                parts.length > 6 ? parts.slice(6).join("\t") : ""
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
                upstream: parts.length > 3 ? parts[3] : "",
                unpulledCount: parts.length > 4 ? Number(parts[4] || 0) : 0,
                lastChangedEpoch: parts.length > 5 ? Number(parts[5] || 0) : 0
            });
        else if (key === "REMOTEBRANCH")
            pendingRemoteBranches.push({
                name: parts.length > 1 ? parts[1] : "",
                unpulledCount: parts.length > 2 ? Number(parts[2] || 0) : 0,
                remoteOnly: parts.length > 3 ? Number(parts[3] || 0) === 1 : false,
                lastChangedEpoch: parts.length > 4 ? Number(parts[4] || 0) : 0
            });
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
        if (localTrackCheckoutMode) {
            actionTitle = "PULL MODE";
            actionExitCode = 0;
            actionOutput =
                "TRACK MODE // checkout is an exact remote tracking operation"
                + "\nFF / MRG does not apply until the local branch exists.";
            return;
        }

        pullMode = pullMode === "ff-only" ? "merge" : "ff-only";
        describePullMode();
    }

    function cyclePullSource() {
        if (localTrackCheckoutMode) {
            actionTitle = "PULL SOURCE";
            actionExitCode = 0;
            actionOutput =
                "TRACK MODE // REMOTE TARGET IS THE SOURCE"
                + "\nChoose the remote branch above, then press PULL.";
            return;
        }

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

    function shouldJournalProcessAction(processAction) {
        return [
            "fetch",
            "pull",
            "push",
            "track-checkout"
        ].indexOf(String(processAction || "")) >= 0;
    }

    function cloneSnapshot(snapshot) {
        try {
            return JSON.parse(JSON.stringify(snapshot || {}));
        } catch (error) {
            return {};
        }
    }

    function journalSnapshot(snapshot) {
        const out = cloneSnapshot(snapshot);

        if (pendingProcessAction === "push") {
            out.recoveryClass = "EVIDENCE_ONLY";
            out.recoveryReason =
                "CONTROL PUSH MUTATES REMOTE REF STATE";
        }

        return out;
    }

    function clearPendingControlAction() {
        pendingJournalId = "";
        pendingSnapshotRequest = "";
        snapshotPhase = "";
        pendingProcessAction = "";
        pendingActionCommand = [];
        pendingActionSuccess = false;
        pendingActionDetail = "";
    }

    function controlContext() {
        return {
            source: "GitService",
            processAction: String(pendingProcessAction || ""),
            target:
                pendingProcessAction === "pull"
                || pendingProcessAction === "track-checkout"
                ? String(pullSourceTarget || selectedRemoteBranch || "")
                : String(selectedRemoteBranch || ""),
            pullMode: String(pullMode || ""),
            localTarget: String(selectedLocalBranch || branch || ""),
            repositorySlug: String(repoRemoteSlug || ""),
            recoveryClass:
                pendingProcessAction === "push"
                ? "EVIDENCE_ONLY"
                : ""
        };
    }

    function failBeforeSnapshot(detail) {
        const message =
            "CONTROL BEFORE SNAPSHOT FAILED // "
            + String(detail || "SNAPSHOT UNAVAILABLE");

        actionBusy = false;
        actionExitCode = 1;
        actionOutput =
            (actionOutput.length > 0 ? actionOutput + "\n" : "")
            + message;
        actionWatchdog.stop();
        clearPendingControlAction();
    }

    function startPendingActionProcess() {
        if (!actionBusy
                || !Array.isArray(pendingActionCommand)
                || pendingActionCommand.length === 0)
            return false;

        actionWatchdog.interval =
            pendingProcessAction === "clone"
            ? 120000
            : 15000;
        actionWatchdog.restart();
        actionProcess.exec(pendingActionCommand);
        return true;
    }

    function finalActionLine() {
        const lines = String(actionOutput || "").split("\n");

        for (let i = lines.length - 1; i >= 0; --i) {
            const value = String(lines[i] || "").trim();

            if (value)
                return value;
        }

        return "";
    }

    function finalizeControlAction(afterSnapshot, snapshotWarning) {
        const processAction = String(pendingProcessAction || "");
        const warning = String(snapshotWarning || "");
        const detail =
            String(
                pendingActionDetail
                || finalActionLine()
                || (
                    actionTitle
                    + (
                        pendingActionSuccess
                        ? " COMPLETE"
                        : " FAILED"
                      )
                  )
            );
        const success = pendingActionSuccess;
        const snapshot =
            afterSnapshot
            ? journalSnapshot(afterSnapshot)
            : {
                snapshotVersion: 1,
                repository: String(repoRoot || repoPath || ""),
                capturedAt: new Date().toISOString(),
                captureFailed: true,
                recoveryClass: "EVIDENCE_ONLY",
                recoveryReason:
                    warning
                    || "CONTROL AFTER SNAPSHOT UNAVAILABLE"
            };

        if (pendingJournalId && operationJournal) {
            if (success)
                operationJournal.completeOperation(
                    pendingJournalId,
                    snapshot,
                    warning
                    ? detail + " // " + warning
                    : detail
                );
            else
                operationJournal.failOperation(
                    pendingJournalId,
                    snapshot,
                    warning
                    ? detail + " // " + warning
                    : detail
                );
        }

        actionBusy = false;
        actionWatchdog.stop();

        if (warning) {
            actionOutput +=
                (actionOutput.length > 0 ? "\n" : "")
                + "SNAPSHOT WARNING // "
                + warning;
        }

        if (processAction === "track-checkout") {
            if (success) {
                localTrackCheckoutMode = false;
                selectedLocalBranch = "";
                selectedLocalHead = "";
                selectedLocalUpstream = "";
                selectedLocalIndex = -1;
            }

            clearPendingControlAction();
            refresh();
            return;
        }

        if (processAction === "clone") {
            const query = clonePendingQuery;
            clonePendingQuery = "";

            if (success) {
                preferredRepoQuery = query;
                discoverRepos();
            } else {
                actionOutput += (
                    actionOutput.length > 0 ? "\n" : ""
                ) + "CLONE DID NOT CREATE A LOCAL BED";
            }

            clearPendingControlAction();
            return;
        }

        clearPendingControlAction();
        refresh();
    }

    function finishActionProcess() {
        if (!actionBusy)
            return;

        actionWatchdog.stop();
        pendingActionSuccess = actionExitCode === 0;
        pendingActionDetail =
            finalActionLine()
            || (
                actionTitle
                + (
                    pendingActionSuccess
                    ? " COMPLETE"
                    : " FAILED // EXIT "
                        + String(actionExitCode)
                  )
              );

        if (!shouldJournalProcessAction(pendingProcessAction)
                || !operationJournal
                || !snapshotService) {
            finalizeControlAction(null, "");
            return;
        }

        snapshotPhase = "AFTER";
        pendingSnapshotRequest = snapshotService.capture(
            "CONTROL AFTER // " + actionTitle,
            controlContext()
        );

        if (!pendingSnapshotRequest) {
            finalizeControlAction(
                null,
                "AFTER SNAPSHOT COULD NOT START"
            );
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
        const trackCheckout =
            action === "pull" && localTrackCheckoutMode;
        const processAction =
            trackCheckout ? "track-checkout" : action;
        const remoteOnly =
            !repoIsLocal
            || String(repoPath || "").indexOf("remote://") === 0;
        const allowed = [
            "status",
            "diff",
            "log",
            "fetch",
            "pull",
            "push",
            "clone"
        ];

        if (allowed.indexOf(action) < 0)
            return;

        if (remoteOnly && action !== "clone") {
            actionTitle = String(kind || "GIT").toUpperCase();
            actionExitCode = 1;
            actionOutput =
                "LOCAL CHECKOUT REQUIRED // " + (repoRemoteSlug || repoLabel)
                + "\nClone this repository first.";
            return;
        }

        if (action === "clone" && !remoteOnly) {
            actionTitle = "CLONE";
            actionExitCode = 0;
            actionOutput =
                "ALREADY LOCAL // " + repoRoot
                + "\nThis repository already has a local working tree.";
            return;
        }

        if (action === "clone" && !repoRemoteSlug) {
            actionTitle = "CLONE";
            actionExitCode = 1;
            actionOutput =
                "CLONE STOPPED // GitHub repository identity is unavailable.";
            return;
        }

        const localTarget = selectedLocalBranch || branch;
        const syncTarget =
            action === "pull"
            ? pullSourceTarget
            : selectedRemoteBranch;

        if (action === "pull" && !isRemoteBranchTarget(syncTarget)) {
            actionTitle = trackCheckout
                ? "TRACK // CHECKOUT"
                : "PULL";
            actionOutput =
                trackCheckout
                ? "TRACK // CHECKOUT NEEDS AN EXISTING REMOTE TARGET"
                : pullSourceMode === "upstream"
                ? "PULL SOURCE // UPSTREAM\nNo matching remote is configured for the selected local target."
                : "PULL SOURCE // TARGET\nChoose a remote branch target first.";
            actionExitCode = 1;
            return;
        }

        if (action === "push" && localTrackCheckoutMode) {
            actionTitle = "PUSH";
            actionExitCode = 1;
            actionOutput =
                "PUSH DISABLED // TRACK // CHECKOUT REMOTE IS SELECTED"
                + "\nCreate the local tracking branch with PULL first.";
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
        actionTitle =
            trackCheckout
            ? "TRACK // CHECKOUT"
            : action.toUpperCase();
        actionOutput = "";
        actionExitCode = 0;

        if (action === "clone")
            clonePendingQuery = repoRemoteSlug || repoLabel;

        const command = [
            "bash",
            "-lc",
            [
                'repo="$1"',
                'kind="$2"',
                'target="$3"',
                'pull_mode="$4"',
                'local_target="$5"',
                'remote_slug="$6"',
                'repo_label="$7"',
                'remote_url="$8"',
                'rc=0',
                'if [ "$kind" = "clone" ]; then',
                '  projects="$HOME/Projects"',
                '  dest="$projects/$repo_label"',
                '  mkdir -p "$projects" || rc=$?',
                '  if [ "$rc" -eq 0 ] && [ -e "$dest" ]; then',
                '    if git -C "$dest" rev-parse --is-inside-work-tree >/dev/null 2>&1; then',
                '      printf "ALREADY LOCAL // %s\\n" "$dest"',
                '    else',
                '      printf "CLONE STOPPED // destination already exists // %s\\n" "$dest"',
                '      rc=1',
                '    fi',
                '  elif [ "$rc" -eq 0 ]; then',
                '    printf "CLONE // %s -> %s\\n" "$remote_slug" "$dest"',
                '    if command -v gh >/dev/null 2>&1; then',
                '      GH_PROMPT_DISABLED=1 gh repo clone "$remote_slug" "$dest" || rc=$?',
                '    elif [ -n "$remote_url" ]; then',
                '      GIT_TERMINAL_PROMPT=0 git clone "$remote_url" "$dest" || rc=$?',
                '    else',
                '      printf "CLONE STOPPED // no GitHub CLI or clone URL available\\n"',
                '      rc=1',
                '    fi',
                '    if [ "$rc" -eq 0 ]; then',
                '      if git -C "$dest" rev-parse --is-inside-work-tree >/dev/null 2>&1; then',
                '        printf "CLONE VERIFIED // %s\\n" "$(git -C "$dest" rev-parse --show-toplevel)"',
                '      else',
                '        printf "CLONE FAILED VERIFICATION // no working tree at %s\\n" "$dest"',
                '        rc=1',
                '      fi',
                '    fi',
                '  fi',
                '  printf "__PA_RC__\\t%s\\n" "$rc"',
                '  printf "__PA_DONE__\\n"',
                '  exit 0',
                'fi',
                'if [ -z "$repo" ]; then repo="$HOME/.config/quickshell"; fi',
                'if ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then',
                '  printf "NOT A GIT REPOSITORY\\n"',
                '  printf "__PA_RC__\\t1\\n"',
                '  printf "__PA_DONE__\\n"',
                '  exit 0',
                'fi',
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
                '  track-checkout)',
                '    remote="${target%%/*}"',
                '    remote_branch="${target#*/}"',
                '    local_branch="$remote_branch"',
                '    printf "TRACK // CHECKOUT // %s -> %s\n" "$target" "$local_branch"',
                '    git -C "$repo" fetch --prune "$remote" || rc=$?',
                '    if [ "$rc" -eq 0 ] && ! git -C "$repo" show-ref --verify --quiet "refs/remotes/$target"; then',
                '      printf "TRACK STOPPED // remote branch not found // %s\n" "$target"',
                '      rc=1',
                '    fi',
                '    if [ "$rc" -eq 0 ] && git -C "$repo" show-ref --verify --quiet "refs/heads/$local_branch"; then',
                '      printf "TRACK STOPPED // local branch already exists // %s\n" "$local_branch"',
                '      printf "Select it as LOCAL TARGET instead.\n"',
                '      rc=1',
                '    fi',
                '    if [ "$rc" -eq 0 ]; then',
                '      dirty="$(git -C "$repo" status --porcelain=v1 2>/dev/null)"',
                '      if [ -n "$dirty" ]; then',
                '        printf "TRACK STOPPED // LIVE checkout is dirty\n"',
                '        printf "Commit or stash changes before switching branches.\n"',
                '        rc=1',
                '      fi',
                '    fi',
                '    if [ "$rc" -eq 0 ]; then',
                '      git -C "$repo" switch --track -c "$local_branch" "$target" || rc=$?',
                '    fi',
                '    if [ "$rc" -eq 0 ]; then',
                '      printf "TRACKED // %s\n" "$local_branch"',
                '      printf "LIVE CHECKOUT // %s\n" "$(git -C "$repo" branch --show-current)"',
                '    fi',
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
            processAction,
            syncTarget,
            pullMode,
            localTarget,
            repoRemoteSlug,
            repoLabel,
            repoRemoteUrl
        ]);

        if (shouldJournalProcessAction(processAction)
                && ((operationJournal && !snapshotService)
                    || (snapshotService && !operationJournal))) {
            actionBusy = false;
            actionExitCode = 1;
            actionOutput =
                "JOURNAL + SNAPSHOT SERVICES MUST BE PAIRED";
            return;
        }

        clearPendingControlAction();
        pendingProcessAction = processAction;
        pendingActionCommand = command;

        if (!shouldJournalProcessAction(processAction)
                || (!operationJournal && !snapshotService)) {
            startPendingActionProcess();
            return;
        }

        snapshotPhase = "BEFORE";
        pendingSnapshotRequest = snapshotService.capture(
            "CONTROL BEFORE // " + actionTitle,
            controlContext()
        );

        if (!pendingSnapshotRequest) {
            failBeforeSnapshot("SNAPSHOT SERVICE BUSY OR UNAVAILABLE");
            return;
        }
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
            finishActionProcess();
            return;
        }

        if (actionOutput.length > 12000)
            return;

        actionOutput += (actionOutput.length > 0 ? "\n" : "") + raw;
    }

    function launchLazygit() {
        if (!repoIsLocal || String(repoPath || "").indexOf("remote://") === 0) {
            actionTitle = "LAZYGIT";
            actionExitCode = 1;
            actionOutput =
                "LOCAL CHECKOUT REQUIRED // " + (repoRemoteSlug || repoLabel)
                + "\nLazygit needs a local working tree.";
            return;
        }

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

    Connections {
        target: gitService.snapshotService
        enabled: gitService.snapshotService !== null
        ignoreUnknownSignals: true

        function onSnapshotReady(requestId, snapshot) {
            if (String(requestId || "")
                    !== String(gitService.pendingSnapshotRequest || ""))
                return;

            gitService.pendingSnapshotRequest = "";

            if (gitService.snapshotPhase === "BEFORE") {
                gitService.snapshotPhase = "";
                const beforeSnapshot =
                    gitService.journalSnapshot(snapshot);

                gitService.pendingJournalId =
                    gitService.operationJournal
                    ? gitService.operationJournal.beginOperation(
                        "CONTROL/"
                            + String(
                                gitService.pendingProcessAction || ""
                              ).toUpperCase(),
                        beforeSnapshot,
                        gitService.controlContext()
                    )
                    : "";

                if (gitService.operationJournal
                        && !gitService.pendingJournalId) {
                    gitService.failBeforeSnapshot(
                        "JOURNAL RECORD COULD NOT START"
                    );
                    return;
                }

                gitService.startPendingActionProcess();
                return;
            }

            if (gitService.snapshotPhase === "AFTER") {
                gitService.snapshotPhase = "";
                gitService.finalizeControlAction(snapshot, "");
            }
        }

        function onSnapshotFailed(requestId, detail) {
            if (String(requestId || "")
                    !== String(gitService.pendingSnapshotRequest || ""))
                return;

            gitService.pendingSnapshotRequest = "";

            if (gitService.snapshotPhase === "BEFORE") {
                gitService.snapshotPhase = "";
                gitService.failBeforeSnapshot(detail);
                return;
            }

            if (gitService.snapshotPhase === "AFTER") {
                gitService.snapshotPhase = "";
                gitService.finalizeControlAction(
                    null,
                    "AFTER SNAPSHOT FAILED // "
                        + String(detail || "UNKNOWN ERROR")
                );
            }
        }
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
            if (!gitService.actionBusy)
                return;

            const detail =
                "ACTION TIMEOUT // VERIFY REPOSITORY / REMOTE STATE";

            if (gitService.pendingJournalId
                    && gitService.operationJournal) {
                gitService.operationJournal.failOperation(
                    gitService.pendingJournalId,
                    {
                        snapshotVersion: 1,
                        repository:
                            String(
                                gitService.repoRoot
                                || gitService.repoPath
                                || ""
                            ),
                        capturedAt: new Date().toISOString(),
                        captureFailed: true,
                        recoveryClass: "EVIDENCE_ONLY",
                        recoveryReason:
                            "CONTROL ACTION TIMEOUT // STATE UNCERTAIN"
                    },
                    detail
                );
            }

            gitService.actionBusy = false;
            gitService.actionExitCode = 1;
            gitService.actionOutput += (
                gitService.actionOutput.length > 0 ? "\n" : ""
            ) + detail;
            gitService.clearPendingControlAction();
        }
    }

    Component.onCompleted: discoverRepos()
}
