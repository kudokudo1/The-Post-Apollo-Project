import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: gitService

    // Diagnostic only. No extra polling, delayed initialization or changes
    // to repo discovery. The measurements are dormant unless opted in.
    readonly property bool syntagmaStartupTraceEnabled:
        String(Quickshell.env("POST_APOLLO_GIT_STARTUP_TRACE") || "").trim() === "1"
    property double traceRepoStartedMs: 0
    property int traceRepoLines: 0
    property double traceRepoSyncMs: 0
    property double traceRepoPeakMs: 0
    property double traceRepoSetupMs: 0
    property double traceRefreshStartedMs: 0
    property int traceRefreshLines: 0
    property double traceRefreshSyncMs: 0
    property double traceRefreshPeakMs: 0

    // Diagnostic is dormant unless explicitly enabled. Never changes
    // snapshot, journal, subprocess, or UI completion ordering.
    readonly property bool syncTimingEnabled:
        String(Quickshell.env("POST_APOLLO_GIT_SYNC_TRACE") || "").trim() === "1"
    property double syncStartedMs: 0
    property double syncPhaseMs: 0

    function traceSyncPhase(phase) {
        if (!syncTimingEnabled
                || (pendingProcessAction !== "fetch"
                    && pendingProcessAction !== "pull"))
            return;
        const now = Date.now();
        console.warn(
            "GIT_SYNC_TRACE // kind=" + pendingProcessAction
            + " phase=" + phase
            + " stage=" + (now - syncPhaseMs) + "ms"
            + " total=" + (now - syncStartedMs) + "ms"
        );
        syncPhaseMs = now;
    }

    // Normal-workload timestamps: wall time includes subprocess time, while
    // callback sum and peak approximate synchronous QML processing. Neither
    // metric is a function-stack profiler or CPU-time counter.
    function syntagmaTraceLabel() {
        return String(repoLabel || "GIT")
            + " :: " + String(preferredRepoQuery || repoPath || "DEFAULT");
    }

    property var operationJournal: null
    property var snapshotService: null

    property bool available: false
    property bool refreshing: false
    property bool refreshPending: false
    property string refreshRepoPath: ""
    property bool discoveringRepos: false
    property bool actionBusy: false
    property string actionStage: "IDLE"
    property bool actionProcessDoneSeen: false
    property double syncAfterSnapshotStartedMs: 0
    property double syncAfterRefreshStartedMs: 0
    // Git menu pipeline timing only. No changes to the journal safety gate.
    property double syncCommandStartedMs: 0
    property double syncCommandFinishedMs: 0
    // Read-only current Fetch/Pull timing. -1 means this phase has not
    // finished. The existing durable journal remains the source of truth.
    property string syncTimingAction: ""
    property int syncTimingPrepareMs: -1
    property int syncTimingGitMs: -1
    property int syncTimingFinalizeMs: -1
    property int syncTimingRefreshMs: -1
    property int syncTimingTotalMs: -1
    property bool actionOverdueNotified: false
    property string clonePendingQuery: ""
    property bool pendingCloneCreated: false
    property string pendingCloneDestination: ""
    property string pendingCloneHead: ""
    property string pendingCloneBranch: ""
    property string pendingCloneOrigin: ""
    property string pendingCloneFingerprint: ""

    readonly property string cloneDestinationPath: {
        const home = String(Quickshell.env("HOME") || "").trim();
        const label = String(repoLabel || "").trim();

        return home && label
            ? home + "/Projects/" + label
            : "";
    }

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

        const traceStart = syntagmaStartupTraceEnabled ? Date.now() : 0;
        discoveringRepos = true;
        repoRows.clear();

        if (syntagmaStartupTraceEnabled) {
            traceRepoStartedMs = traceStart;
            traceRepoLines = 0;
            traceRepoSyncMs = 0;
            traceRepoPeakMs = 0;
            traceRepoSetupMs = Date.now() - traceStart;
            console.warn(
                "SYNTAGMA_STARTUP_TRACE // git scan started // "
                + syntagmaTraceLabel()
                + " // setupSync=" + traceRepoSetupMs + "ms"
            );
        }

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
            if (syntagmaStartupTraceEnabled) {
                console.warn(
                    "SYNTAGMA_STARTUP_TRACE // git refresh queued // "
                    + syntagmaTraceLabel()
                    + " // reason=selectRepo during active refresh"
                );
            }
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

    // Preserve delegate identity across a refresh when commits are unchanged.
    // BranchMap subscribes to topologyModel through a Repeater: clear + append
    // destroys/recreates every glow/text delegate, even for identical data.
    // Reconcile by SHA instead; update only roles that actually changed.
    function reconcileTopologyRows() {
        const roles = [
            "shortSha", "parents", "refsText", "epoch",
            "author", "subject", "lane", "isHead"
        ];
        let inserted = 0;
        let moved = 0;
        let updated = 0;
        let removed = 0;
        let unchanged = 0;

        for (let i = 0; i < pendingTopology.length; ++i) {
            const incoming = pendingTopology[i];

            if (i >= topologyRows.count) {
                topologyRows.append(incoming);
                inserted += 1;
                continue;
            }

            if (String(topologyRows.get(i).sha) !== String(incoming.sha)) {
                let oldIndex = -1;
                for (let j = i + 1; j < topologyRows.count; ++j) {
                    if (String(topologyRows.get(j).sha) === String(incoming.sha)) {
                        oldIndex = j;
                        break;
                    }
                }

                if (oldIndex >= 0) {
                    topologyRows.move(oldIndex, i, 1);
                    moved += 1;
                } else {
                    topologyRows.insert(i, incoming);
                    inserted += 1;
                    continue;
                }
            }

            const current = topologyRows.get(i);
            let rowChanged = false;
            for (let r = 0; r < roles.length; ++r) {
                const role = roles[r];
                if (current[role] === incoming[role])
                    continue;

                topologyRows.setProperty(i, role, incoming[role]);
                rowChanged = true;
            }

            if (rowChanged)
                updated += 1;
            else
                unchanged += 1;
        }

        while (topologyRows.count > pendingTopology.length) {
            topologyRows.remove(topologyRows.count - 1);
            removed += 1;
        }

        return {
            inserted: inserted,
            moved: moved,
            updated: updated,
            removed: removed,
            unchanged: unchanged
        };
    }

    // Keep branch delegates intact when a no-op Fetch yields identical rows.
    // ListModel.clear() notifies every consumer even when values don't change.
    function branchModelMatches(model, rows, roles) {
        if (model.count !== rows.length)
            return false;
        for (let i = 0; i < rows.length; ++i) {
            const current = model.get(i);
            const next = rows[i];
            for (let j = 0; j < roles.length; ++j) {
                const role = roles[j];
                if (current[role] !== next[role])
                    return false;
            }
        }
        return true;
    }

    function publishPendingModels() {
        const trace = syntagmaStartupTraceEnabled;
        let started = trace ? Date.now() : 0;
        let metadataMs = 0;
        let clearsMs = 0;
        let localMs = 0;
        let remoteMs = 0;
        let topologyMs = 0;

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

        if (trace) {
            metadataMs = Date.now() - started;
            started = Date.now();
        }

        const nextLocalRows = [];
        for (let i = 0; i < pendingLocalBranches.length; ++i) {
            const row = pendingLocalBranches[i] || {};
            nextLocalRows.push({
                name: String(row.name || ""),
                head: String(row.head || ""),
                upstream: String(row.upstream || ""),
                unpulledCount: Number(row.unpulledCount || 0),
                lastChangedEpoch: Number(row.lastChangedEpoch || 0)
            });
        }
        const nextRemoteRows = [];
        for (let i = 0; i < pendingRemoteBranches.length; ++i) {
            const row = pendingRemoteBranches[i] || {};
            const remoteName = String(row.name || "");
            if (!isRemoteBranchTarget(remoteName))
                continue;
            nextRemoteRows.push({
                name: remoteName,
                unpulledCount: Number(row.unpulledCount || 0),
                remoteOnly: Boolean(row.remoteOnly),
                lastChangedEpoch: Number(row.lastChangedEpoch || 0)
            });
        }
        const localUnchanged = branchModelMatches(localBranchRows,
            nextLocalRows, ["name", "head", "upstream", "unpulledCount",
                "lastChangedEpoch"]);
        const remoteUnchanged = branchModelMatches(remoteBranchRows,
            nextRemoteRows, ["name", "unpulledCount", "remoteOnly",
                "lastChangedEpoch"]);

        // On a changed list, preserve the original full rebuild behavior.
        // On identical data, skip all ListModel mutation notifications.
        if (!localUnchanged)
            localBranchRows.clear();
        if (!remoteUnchanged)
            remoteBranchRows.clear();

        if (trace) {
            clearsMs = Date.now() - started;
            started = Date.now();
        }

        if (!localUnchanged) {
            for (let i = 0; i < nextLocalRows.length; ++i)
                localBranchRows.append(nextLocalRows[i]);
        }

        if (trace) {
            localMs = Date.now() - started;
            started = Date.now();
        }

        if (!remoteUnchanged) {
            for (let i = 0; i < nextRemoteRows.length; ++i)
                remoteBranchRows.append(nextRemoteRows[i]);
        }

        if (trace) {
            remoteMs = Date.now() - started;
            started = Date.now();
        }

        const topologyDelta = reconcileTopologyRows();

        if (trace) {
            topologyMs = Date.now() - started;
            return {
                metadataMs: metadataMs,
                clearsMs: clearsMs,
                localMs: localMs,
                remoteMs: remoteMs,
                topologyMs: topologyMs,
                topologyDelta: topologyDelta
            };
        }
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
        // Diagnostic only: capture the caller even if a scan is active.
        // In ordinary runs no error stack or logging is produced.
        if (syntagmaStartupTraceEnabled) {
            let caller = "unavailable";
            try {
                const frames = String((new Error()).stack || "").split("\n");
                caller = frames.slice(1, 5).join(" > ")
                    .replace(/\s+/g, " ").slice(0, 350) || "unavailable";
            } catch (ignored) {
                caller = "unavailable";
            }
            console.warn(
                "SYNTAGMA_STARTUP_TRACE // git refresh requested // "
                + syntagmaTraceLabel()
                + " // busy=" + refreshing
                + " pending=" + refreshPending
                + " // caller=" + caller
            );
        }

        if (refreshing)
            return;

        if (syntagmaStartupTraceEnabled) {
            traceRefreshStartedMs = Date.now();
            traceRefreshLines = 0;
            traceRefreshSyncMs = 0;
            traceRefreshPeakMs = 0;
        }

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
                // A ref already reachable from HEAD cannot produce a '+'
                // from git cherry. Compute merged tips in one Git invocation
                // and retain the original patch-equivalence check elsewhere.
                'merged_remote_refs="|"',
                'while IFS= read -r ref; do',
                '  [ -n "$ref" ] || continue',
                '  merged_remote_refs="${merged_remote_refs}${ref}|"',
                'done < <(git -C "$root" for-each-ref --merged=HEAD --format="%(refname:short)" refs/remotes/origin 2>/dev/null)',
                'pending_refs="|"',
                'pending_count=0',
                'while IFS="$(printf "\\t")" read -r ref changed; do',
                '  [ -z "$ref" ] && continue',
                '  [ "$ref" = "origin" ] && continue',
                '  [ "$ref" = "origin/HEAD" ] && continue',
                '  case "$ref" in */*) ;; *) continue ;; esac',
                '  case "$merged_remote_refs" in *"|$ref|"*) continue ;; esac',
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
            // Measure the individual synchronous stages of the DONE callback
            // only in the operator's opt-in diagnostic. Keep the ordering and
            // operations exactly the same in normal and traced modes.
            const trace = syntagmaStartupTraceEnabled;
            let started = trace ? Date.now() : 0;
            let publishMs = 0;
            let publishParts = null;
            let localSelectionMs = 0;
            let remoteSelectionMs = 0;
            let revisionMs = 0;
            let availableMs = 0;
            let refreshedSignalMs = 0;

            const staleRead = refreshRepoPath !== repoPath;
            const pendingAtDone = trace ? refreshPending : false;

            refreshing = false;
            refreshWatchdog.stop();
            const pipelineRefreshStartedMs = syncAfterRefreshStartedMs;
            if (syncAfterRefreshStartedMs > 0) {
                const refreshElapsed =
                    Math.max(0, Date.now() - syncAfterRefreshStartedMs);
                syncAfterRefreshStartedMs = 0;
                actionOutput += (actionOutput.length ? "\n" : "")
                    + "REFRESHED // repository view "
                    + refreshElapsed + " ms";
            }
            const stateMs = trace ? Date.now() - started : 0;

            if (!staleRead && !lastError) {
                if (trace) started = Date.now();
                publishParts = publishPendingModels();
                if (trace) {
                    publishMs = Date.now() - started;
                    started = Date.now();
                }
                ensureLocalSelection();
                if (trace) {
                    localSelectionMs = Date.now() - started;
                    started = Date.now();
                }
                ensureRemoteSelection();
                if (trace) {
                    remoteSelectionMs = Date.now() - started;
                    started = Date.now();
                }
                topologyRevision += 1;
                if (trace) {
                    revisionMs = Date.now() - started;
                    started = Date.now();
                }
                available = true;
                if (trace) {
                    availableMs = Date.now() - started;
                    started = Date.now();
                }
                refreshed();
                if (trace)
                    refreshedSignalMs = Date.now() - started;
            }

            // End-to-end timing is emitted only after refreshing the UI
            // models; unlike the legacy REFRESHED line it includes their
            // synchronous publication. Never uses the timing to unlock or
            // report a Git result, which remains journal-acknowledged above.
            if (pipelineRefreshStartedMs > 0
                    && syncCommandStartedMs >= syncStartedMs
                    && syncCommandFinishedMs >= syncCommandStartedMs
                    && pipelineRefreshStartedMs >= syncCommandFinishedMs) {
                const end = Date.now();
                const prepareMs = syncCommandStartedMs - syncStartedMs;
                const gitMs = syncCommandFinishedMs - syncCommandStartedMs;
                const finalizeMs = pipelineRefreshStartedMs - syncCommandFinishedMs;
                const refreshMs = end - pipelineRefreshStartedMs;
                // Publish into the existing output header, not a duplicate
                // log line. The journal's BEGIN/COMPLETE profiles remain in
                // the scrollable log because they measure different work.
                syncTimingPrepareMs = prepareMs;
                syncTimingGitMs = gitMs;
                syncTimingFinalizeMs = finalizeMs;
                syncTimingRefreshMs = refreshMs;
                syncTimingTotalMs = end - syncStartedMs;
                syncCommandStartedMs = 0;
                syncCommandFinishedMs = 0;
            }

            if (trace) started = Date.now();
            if (refreshPending || staleRead) {
                refreshPending = false;
                Qt.callLater(function() {
                    refresh();
                });
            }

            if (trace) {
                const followupMs = Date.now() - started;
                console.warn(
                    "SYNTAGMA_STARTUP_TRACE // git DONE phases // "
                    + syntagmaTraceLabel()
                    + " // state=" + stateMs + "ms"
                    + " publish=" + publishMs + "ms"
                    + " localSelection=" + localSelectionMs + "ms"
                    + " remoteSelection=" + remoteSelectionMs + "ms"
                    + " revision=" + revisionMs + "ms"
                    + " available=" + availableMs + "ms"
                    + " refreshedSignal=" + refreshedSignalMs + "ms"
                    + " followup=" + followupMs + "ms"
                    + " // localRows=" + pendingLocalBranches.length
                    + " remoteRows=" + pendingRemoteBranches.length
                    + " topologyRows=" + pendingTopology.length
                    + " stale=" + staleRead
                    + " pendingAtDone=" + pendingAtDone
                    + " followupQueued=" + (pendingAtDone || staleRead)
                );
                if (publishParts) {
                    console.warn(
                        "SYNTAGMA_STARTUP_TRACE // git publish phases // "
                        + syntagmaTraceLabel()
                        + " // metadata=" + publishParts.metadataMs + "ms"
                        + " clears=" + publishParts.clearsMs + "ms"
                        + " local=" + publishParts.localMs + "ms"
                        + " remote=" + publishParts.remoteMs + "ms"
                        + " topology=" + publishParts.topologyMs + "ms"
                        + " topologyDelta=" + JSON.stringify(publishParts.topologyDelta)
                        + " total=" + publishMs + "ms"
                        + " // localRows=" + pendingLocalBranches.length
                        + " remoteRows=" + pendingRemoteBranches.length
                        + " topologyRows=" + pendingTopology.length
                    );
                }
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
            "track-checkout",
            "clone"
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

    function journalProfileLine(stage, snapshotCloneMs) {
        const timing = operationJournal
            ? operationJournal.lastMutationProfile : null;
        if (!timing || timing.stage !== stage)
            return "";
        // Keep the breakdown inline with the existing Git Menu output.
        // The persistence phase includes both encoding and FileView writes.
        return "\nJOURNAL PROFILE // " + stage
            + " clone " + snapshotCloneMs + " ms"
            + " // record " + timing.recordMs + " ms"
            + " // entries " + timing.entriesMs + " ms"
            + " // persist " + timing.persistMs + " ms"
            + " // notify " + timing.notifyMs + " ms"
            + " // mutation " + timing.totalMs + " ms";
    }

    function clearPendingControlAction() {
        pendingJournalId = "";
        pendingSnapshotRequest = "";
        snapshotPhase = "";
        pendingProcessAction = "";
        pendingActionCommand = [];
        pendingActionSuccess = false;
        pendingActionDetail = "";
        pendingCloneCreated = false;
        pendingCloneDestination = "";
        pendingCloneHead = "";
        pendingCloneBranch = "";
        pendingCloneOrigin = "";
        pendingCloneFingerprint = "";
    }

    function cloneBoundaryBeforeSnapshot() {
        return {
            snapshotVersion: 1,
            repository: String(cloneDestinationPath || ""),
            capturedAt: new Date().toISOString(),
            externalBoundary: "CLONE",
            destinationPath: String(cloneDestinationPath || ""),
            destinationRequiredAbsent: true,
            recoveryClass: "EXTERNAL_RECOVERABLE",
            recoveryReason:
                "CLONE CREATION WILL PROVE DESTINATION ABSENCE"
        };
    }

    function cloneBoundaryAfterSnapshot() {
        const recoverable =
            pendingActionSuccess
            && pendingCloneCreated
            && pendingCloneDestination
            && pendingCloneHead
            && pendingCloneFingerprint;

        return {
            snapshotVersion: 1,
            repository:
                String(
                    pendingCloneDestination
                    || cloneDestinationPath
                    || ""
                ),
            capturedAt: new Date().toISOString(),
            externalBoundary: "CLONE",
            cloneCreated: Boolean(pendingCloneCreated),
            destinationPath:
                String(
                    pendingCloneDestination
                    || cloneDestinationPath
                    || ""
                ),
            head: String(pendingCloneHead || ""),
            branch: String(pendingCloneBranch || ""),
            origin: String(pendingCloneOrigin || ""),
            filesystemFingerprint:
                String(pendingCloneFingerprint || ""),
            recoveryClass:
                recoverable
                ? "EXTERNAL_RECOVERABLE"
                : "EVIDENCE_ONLY",
            recoveryReason:
                recoverable
                ? "EXACT CREATED CLONE DIRECTORY FINGERPRINT RECORDED"
                : "CLONE DID NOT CREATE A NEW EXACTLY RECOVERABLE DIRECTORY"
        };
    }

    function controlContext() {
        return {
            source: "GitService",
            snapshotProfile:
                pendingProcessAction === "fetch" ? "REFS_ONLY"
                : pendingProcessAction === "pull" ? "PULL_REF_SAFE"
                : "FULL",
            processAction: String(pendingProcessAction || ""),
            target:
                pendingProcessAction === "pull"
                || pendingProcessAction === "track-checkout"
                ? String(pullSourceTarget || selectedRemoteBranch || "")
                : String(selectedRemoteBranch || ""),
            pullMode: String(pullMode || ""),
            localTarget: String(selectedLocalBranch || branch || ""),
            repositorySlug: String(repoRemoteSlug || ""),
            destinationPath:
                pendingProcessAction === "clone"
                ? String(cloneDestinationPath || "")
                : "",
            remoteUrl:
                pendingProcessAction === "clone"
                ? String(repoRemoteUrl || "")
                : "",
            recoveryClass:
                pendingProcessAction === "clone"
                ? "EXTERNAL_RECOVERABLE"
                : pendingProcessAction === "push"
                ? "EVIDENCE_ONLY"
                : ""
        };
    }

    function failBeforeSnapshot(detail) {
        const message =
            "CONTROL BEFORE SNAPSHOT FAILED // "
            + String(detail || "SNAPSHOT UNAVAILABLE");

        actionBusy = false;
        actionStage = "IDLE";
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
        actionProcessDoneSeen = false;
        actionOverdueNotified = false;
        actionStage = "RUNNING";
        actionOutput += (actionOutput.length ? "\n" : "")
            + "RUNNING // Git subprocess started";
        traceSyncPhase("GIT_STARTED");
        actionWatchdog.restart();
        if (pendingProcessAction === "fetch"
                || pendingProcessAction === "pull") {
            syncCommandStartedMs = Date.now();
            syncTimingPrepareMs = syncCommandStartedMs - syncStartedMs;
        }
        actionProcess.exec(pendingActionCommand);
        return true;
    }

    function finalActionLine() {
        const lines = String(actionOutput || "").split("\n");

        for (let i = lines.length - 1; i >= 0; --i) {
            const value = String(lines[i] || "").trim();

            if (value.indexOf("PREPARING //") === 0
                    || value.indexOf("JOURNAL PROFILE //") === 0
                    || value.indexOf("PREPARED //") === 0
                    || value.indexOf("RUNNING // Git subprocess") === 0
                    || value.indexOf("FINALIZING //") === 0
                    || value.indexOf("STILL RUNNING //") === 0)
                continue;
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
        const finalizationStarted = Date.now();
        const afterSnapshotMs =
            syncAfterSnapshotStartedMs > 0
            ? Math.max(0, finalizationStarted - syncAfterSnapshotStartedMs)
            : 0;
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
        const snapshotCloneMs = Date.now() - finalizationStarted;

        let journalRecorded = true;
        if (pendingJournalId && operationJournal) {
            if (success)
                journalRecorded = operationJournal.completeOperation(
                    pendingJournalId,
                    snapshot,
                    warning
                    ? detail + " // " + warning
                    : detail
                );
            else
                journalRecorded = operationJournal.failOperation(
                    pendingJournalId,
                    snapshot,
                    warning
                    ? detail + " // " + warning
                    : detail
                );
        }

        if (processAction === "fetch" || processAction === "pull") {
            const metrics = operationJournal;
            actionOutput += (actionOutput.length ? "\n" : "")
                + "FINISHED // after snapshot "
                + afterSnapshotMs
                + " ms // journal "
                + (Date.now() - finalizationStarted)
                + " ms (encode "
                + (metrics ? metrics.lastPersistSerializationMs : 0)
                + " ms / disk "
                + (metrics ? metrics.lastPersistWriteMs : 0)
                + " ms)"
                + journalProfileLine(
                    success ? "COMPLETE" : "FAIL", snapshotCloneMs
                );
        }

        if (!journalRecorded) {
            // Git may have succeeded, but an unrecorded AFTER boundary is
            // not a successfully finalized CONTROL operation.
            actionExitCode = 1;
            actionOutput += (actionOutput.length ? "\n" : "")
                + "JOURNAL NOT RECORDED // Git subprocess "
                + (success ? "succeeded" : "failed")
                + "; AFTER journal save unconfirmed // "
                + String(operationJournal
                    ? operationJournal.storageError
                    : "JOURNAL SERVICE UNAVAILABLE");
        }

        actionBusy = false;
        actionStage = "IDLE";
        actionWatchdog.stop();
        traceSyncPhase("JOURNAL_FINALIZED");

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
        if (processAction === "fetch" || processAction === "pull") {
            syncAfterRefreshStartedMs = Date.now();
            if (syncCommandFinishedMs > 0)
                syncTimingFinalizeMs =
                    syncAfterRefreshStartedMs - syncCommandFinishedMs;
        }
        syncAfterSnapshotStartedMs = 0;
        refresh();
    }

    function finishActionProcess() {
        if (!actionBusy)
            return;

        if ((pendingProcessAction === "fetch"
                    || pendingProcessAction === "pull")
                && syncCommandStartedMs > 0) {
            syncCommandFinishedMs = Date.now();
            syncTimingGitMs = syncCommandFinishedMs - syncCommandStartedMs;
        }
        traceSyncPhase("GIT_PROCESS_COMPLETE");
        actionStage = "FINALIZING";
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
        actionOutput += (actionOutput.length ? "\n" : "")
            + "FINALIZING // collecting repository evidence";

        if (pendingProcessAction === "clone") {
            finalizeControlAction(
                cloneBoundaryAfterSnapshot(),
                ""
            );
            return;
        }

        if (!shouldJournalProcessAction(pendingProcessAction)
                || !operationJournal
                || !snapshotService) {
            finalizeControlAction(null, "");
            return;
        }

        if (pendingProcessAction === "fetch"
                || pendingProcessAction === "pull")
            syncAfterSnapshotStartedMs = Date.now();
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
        actionStage = "PREPARING";
        actionTitle =
            trackCheckout
            ? "TRACK // CHECKOUT"
            : action.toUpperCase();
        actionOutput = ["fetch", "pull"].indexOf(action) >= 0
            ? "PREPARING // capturing repository references and journal evidence"
            : "";
        actionExitCode = 0;

        if (action === "clone") {
            clonePendingQuery = repoRemoteSlug || repoLabel;
            pendingCloneDestination =
                String(cloneDestinationPath || "");
        }

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
                'fingerprint_tree() {',
                '  python3 - "$1" <<\'PY\'',
                'import hashlib, os, stat, sys',
                'root = os.path.realpath(sys.argv[1])',
                'h = hashlib.sha256()',
                'for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):',
                '    dirnames.sort(); filenames.sort()',
                '    for name in list(dirnames) + list(filenames):',
                '        path = os.path.join(dirpath, name)',
                '        rel = os.path.relpath(path, root)',
                '        st = os.lstat(path)',
                '        h.update(rel.encode("utf-8", "surrogateescape") + b"\\0")',
                '        h.update(str(stat.S_IFMT(st.st_mode)).encode() + b":" + str(stat.S_IMODE(st.st_mode)).encode() + b"\\0")',
                '        if stat.S_ISLNK(st.st_mode):',
                '            h.update(os.readlink(path).encode("utf-8", "surrogateescape"))',
                '        elif stat.S_ISREG(st.st_mode):',
                '            with open(path, "rb") as handle:',
                '                while True:',
                '                    chunk = handle.read(1024 * 1024)',
                '                    if not chunk:',
                '                        break',
                '                    h.update(chunk)',
                '        h.update(b"\\0")',
                'print(h.hexdigest())',
                'PY',
                '}',
                'if [ "$kind" = "clone" ]; then',
                '  projects="$HOME/Projects"',
                '  dest="$projects/$repo_label"',
                '  clone_created=0',
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
                '      clone_created=1',
                '      if git -C "$dest" rev-parse --is-inside-work-tree >/dev/null 2>&1; then',
                '        printf "CLONE VERIFIED // %s\\n" "$(git -C "$dest" rev-parse --show-toplevel)"',
                '      else',
                '        printf "CLONE FAILED VERIFICATION // no working tree at %s\\n" "$dest"',
                '        rc=1',
                '      fi',
                '    fi',
                '  fi',
                '  if [ "$rc" -eq 0 ] && git -C "$dest" rev-parse --is-inside-work-tree >/dev/null 2>&1; then',
                '    clone_top="$(git -C "$dest" rev-parse --show-toplevel 2>/dev/null || true)"',
                '    clone_head="$(git -C "$dest" rev-parse HEAD 2>/dev/null || true)"',
                '    clone_branch="$(git -C "$dest" branch --show-current 2>/dev/null || true)"',
                '    clone_origin="$(git -C "$dest" remote get-url origin 2>/dev/null || true)"',
                '    clone_fingerprint="$(fingerprint_tree "$dest" 2>/dev/null || true)"',
                '    if [ -z "$clone_top" ] || [ -z "$clone_head" ] || [ -z "$clone_fingerprint" ]; then',
                '      printf "CLONE FAILED EVIDENCE CAPTURE // %s\\n" "$dest"',
                '      rc=1',
                '    else',
                '      printf "__PA_CLONE_META__\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\n" "$clone_created" "$clone_top" "$clone_head" "$clone_branch" "$clone_origin" "$clone_fingerprint"',
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
                '    if [ "$local_target" = "$current_branch" ]; then',
                '      case "$pull_mode" in',
                '        ff-only)',
                '          printf "PULL // FF ONLY // %s -> checked-out %s\\n" "$target" "$local_target"',
                '          git -C "$repo" pull --ff-only --prune "$remote" "$remote_branch" || rc=$?',
                '          ;;',
                '        merge)',
                '          printf "PULL // MERGE // %s -> checked-out %s\\n" "$target" "$local_target"',
                '          git -C "$repo" pull --no-rebase --prune "$remote" "$remote_branch" || rc=$?',
                '          ;;',
                '      esac',
                '    else',
                '      git -C "$repo" fetch --prune "$remote" || rc=$?',
                '      if [ "$rc" -eq 0 ]; then',
                '        if [ "$pull_mode" = "ff-only" ]; then',
                '          printf "SYNC LOCAL TARGET // %s -> %s // NO CHECKOUT\\n" "$target" "$local_target"',
                '          if git -C "$repo" merge-base --is-ancestor "$local_target" "$target"; then',
                '            git -C "$repo" branch -f "$local_target" "$target" || rc=$?',
                '          else',
                '            printf "PULL STOPPED // %s cannot fast-forward to %s\\n" "$local_target" "$target"',
                '            rc=1',
                '          fi',
                '        else',
                '          printf "BACKGROUND MERGE REFUSED // %s is not checked out\\n" "$local_target"',
                '          printf "Use FF mode, or explicitly checkout the branch before a merge-mode pull.\\n"',
                '          rc=1',
                '        fi',
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
        ];

        if (processAction !== "clone"
                && shouldJournalProcessAction(processAction)
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

        if (processAction === "fetch" || processAction === "pull") {
            syncStartedMs = Date.now();
            syncPhaseMs = syncStartedMs;
            syncCommandStartedMs = 0;
            syncCommandFinishedMs = 0;
            syncTimingAction = processAction;
            syncTimingPrepareMs = -1;
            syncTimingGitMs = -1;
            syncTimingFinalizeMs = -1;
            syncTimingRefreshMs = -1;
            syncTimingTotalMs = -1;
            traceSyncPhase("REQUESTED");
        }

        if (processAction === "clone") {
            if (!operationJournal) {
                startPendingActionProcess();
                return;
            }

            if (!cloneDestinationPath) {
                actionBusy = false;
                actionExitCode = 1;
                actionOutput =
                    "CLONE JOURNAL DESTINATION UNAVAILABLE";
                clearPendingControlAction();
                return;
            }

            pendingJournalId =
                operationJournal.beginOperation(
                    "CONTROL/CLONE",
                    cloneBoundaryBeforeSnapshot(),
                    controlContext()
                );

            if (!pendingJournalId) {
                failBeforeSnapshot(
                    "CLONE JOURNAL RECORD COULD NOT START"
                );
                return;
            }

            startPendingActionProcess();
            return;
        }

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

        if (raw.indexOf("__PA_CLONE_META__\t") === 0) {
            const parts = raw.split("\t");
            pendingCloneCreated =
                parts.length > 1
                && parts[1] === "1";
            pendingCloneDestination =
                parts.length > 2 ? parts[2] : "";
            pendingCloneHead =
                parts.length > 3 ? parts[3] : "";
            pendingCloneBranch =
                parts.length > 4 ? parts[4] : "";
            pendingCloneOrigin =
                parts.length > 5 ? parts[5] : "";
            pendingCloneFingerprint =
                parts.length > 6 ? parts[6] : "";
            return;
        }

        if (raw.indexOf("__PA_RC__\t") === 0) {
            actionExitCode = Number(raw.slice("__PA_RC__\t".length) || 0);
            return;
        }

        if (raw === "__PA_DONE__") {
            actionProcessDoneSeen = true;
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
                gitService.traceSyncPhase("BEFORE_SNAPSHOT_COMPLETE");
                gitService.snapshotPhase = "";
                const syncPreparation =
                    gitService.pendingProcessAction === "fetch"
                    || gitService.pendingProcessAction === "pull";
                const snapshotMs = syncPreparation
                    ? Math.max(0, Date.now() - gitService.syncStartedMs)
                    : 0;
                const journalStartedMs = Date.now();
                const beforeSnapshot =
                    gitService.journalSnapshot(snapshot);
                const snapshotCloneMs = Date.now() - journalStartedMs;

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
                        "JOURNAL RECORD COULD NOT START // "
                        + String(gitService.operationJournal.storageError
                            || "NO DURABLE BEFORE RECORD")
                    );
                    return;
                }

                gitService.traceSyncPhase("JOURNAL_STARTED");
                if (syncPreparation) {
                    const metrics = gitService.operationJournal;
                    gitService.actionOutput += "\nPREPARED // snapshot "
                        + snapshotMs + " ms // journal "
                        + Math.max(0, Date.now() - journalStartedMs)
                        + " ms (encode "
                        + (metrics ? metrics.lastPersistSerializationMs : 0)
                        + " ms / disk "
                        + (metrics ? metrics.lastPersistWriteMs : 0)
                        + " ms)"
                        + gitService.journalProfileLine(
                            "BEGIN", snapshotCloneMs
                        );
                }
                gitService.startPendingActionProcess();
                return;
            }

            if (gitService.snapshotPhase === "AFTER") {
                gitService.traceSyncPhase("AFTER_SNAPSHOT_COMPLETE");
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
                if (!gitService.syntagmaStartupTraceEnabled) {
                    gitService.consumeRepoLine(line);
                    return;
                }

                const started = Date.now();
                gitService.consumeRepoLine(line);
                const duration = Date.now() - started;
                gitService.traceRepoLines += 1;
                gitService.traceRepoSyncMs += duration;
                gitService.traceRepoPeakMs = Math.max(
                    gitService.traceRepoPeakMs, duration
                );

                if (String(line || "").split("\t")[0] === "DONE") {
                    console.warn(
                        "SYNTAGMA_STARTUP_TRACE // git scan finished // "
                        + gitService.syntagmaTraceLabel()
                        + " // wall=" + (Date.now() - gitService.traceRepoStartedMs) + "ms"
                        + " lines=" + gitService.traceRepoLines
                        + " callbackSum=" + gitService.traceRepoSyncMs + "ms"
                        + " callbackMax=" + gitService.traceRepoPeakMs + "ms"
                    );
                }
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
                if (!gitService.syntagmaStartupTraceEnabled) {
                    gitService.consumeRefreshLine(line);
                    return;
                }

                const started = Date.now();
                gitService.consumeRefreshLine(line);
                const duration = Date.now() - started;
                gitService.traceRefreshLines += 1;
                gitService.traceRefreshSyncMs += duration;
                gitService.traceRefreshPeakMs = Math.max(
                    gitService.traceRefreshPeakMs, duration
                );

                // Report only the row *type*, never the raw Git payload.
                if (duration >= 100) {
                    console.warn(
                        "SYNTAGMA_STARTUP_TRACE // git slow refresh callback // "
                        + gitService.syntagmaTraceLabel()
                        + " // tag=" + String(line || "").split("\t")[0]
                        + " duration=" + duration + "ms"
                    );
                }

                if (String(line || "").split("\t")[0] === "DONE") {
                    console.warn(
                        "SYNTAGMA_STARTUP_TRACE // git refresh finished // "
                        + gitService.syntagmaTraceLabel()
                        + " // wall=" + (Date.now() - gitService.traceRefreshStartedMs) + "ms"
                        + " lines=" + gitService.traceRefreshLines
                        + " callbackSum=" + gitService.traceRefreshSyncMs + "ms"
                        + " callbackMax=" + gitService.traceRefreshPeakMs + "ms"
                    );
                }
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

        onExited: function(code, exitStatus) {
            // Broken protocol: finish only once the child has exited and
            // stdout has had time to emit the completion marker.
            if (!gitService.actionBusy || gitService.actionProcessDoneSeen)
                return;
            actionExitFallback.restart();
        }

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
        id: actionExitFallback
        interval: 200
        repeat: false
        onTriggered: {
            if (!gitService.actionBusy || gitService.actionProcessDoneSeen
                    || actionProcess.running)
                return;
            gitService.actionExitCode = 1;
            gitService.actionOutput += (gitService.actionOutput.length ? "\n" : "")
                + "GIT PROCESS EXITED WITHOUT COMPLETION MARKER // STATE UNCERTAIN";
            gitService.finishActionProcess();
        }
    }

    Timer {
        id: actionWatchdog
        interval: 15000
        repeat: false
        onTriggered: {
            if (!gitService.actionBusy || gitService.actionProcessDoneSeen)
                return;
            // Only warn. Never mark failed or unlock while Git may run.
            gitService.actionOverdueNotified = true;
            gitService.actionStage = "RUNNING (SLOW)";
            gitService.actionOutput += (gitService.actionOutput.length ? "\n" : "")
                + "STILL RUNNING // Git exceeded 15 seconds. Controls remain locked until process completion.";
            gitService.traceSyncPhase("GIT_OVERDUE");
        }
    }

    Component.onCompleted: discoverRepos()
}
