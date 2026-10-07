import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property string repositorySlug: ""
    property string branchName: ""
    property int maxEntries: 100

    property bool busy: false
    property bool queueAvailable: false
    property string resolvedBranch: ""
    property string queueId: ""
    property string queueUrl: ""
    property int nextEntryEstimatedTimeToMerge: -1
    property var configuration: ({})
    property var entries: []
    property int totalCount: 0
    property string status: "READY"
    property string lastError: ""

    property bool refreshExitSeen: false
    property bool refreshStdoutSeen: false
    property bool refreshStderrSeen: false
    property int refreshExitCode: -1
    property string refreshStdoutText: ""
    property string refreshStderrText: ""

    signal refreshed()

    readonly property int queuedCount: countState("QUEUED")
    readonly property int awaitingChecksCount: countState("AWAITING_CHECKS")
    readonly property int mergeableCount: countState("MERGEABLE")
    readonly property int lockedCount: countState("LOCKED")
    readonly property int unmergeableCount: countState("UNMERGEABLE")

    function normalizeRepository(value) {
        const slug = String(value || "").trim();

        if (!/^[^/\s]+\/[^/\s]+$/.test(slug))
            return "";

        return slug;
    }

    function entryAt(index) {
        if (index < 0 || index >= entries.length)
            return null;
        return entries[index];
    }

    function entryForPullRequest(number) {
        const needle = Number(number || 0);

        for (let i = 0; i < entries.length; ++i) {
            const entry = entries[i] || {};
            const pullRequest = entry.pullRequest || {};

            if (Number(pullRequest.number || 0) === needle)
                return entry;
        }

        return null;
    }

    function countState(stateName) {
        const needle = String(stateName || "").toUpperCase();
        let count = 0;

        for (let i = 0; i < entries.length; ++i) {
            if (String((entries[i] || {}).state || "").toUpperCase()
                    === needle)
                count += 1;
        }

        return count;
    }

    function entryStateLabel(entry) {
        const state =
            String((entry || {}).state || "UNKNOWN").toUpperCase();

        if (state === "AWAITING_CHECKS")
            return "WAITING CHECKS";
        if (state === "MERGEABLE")
            return "READY";
        if (state === "UNMERGEABLE")
            return "BLOCKED";
        if (state === "LOCKED")
            return "LOCKED";
        if (state === "QUEUED")
            return "QUEUED";

        return state;
    }

    function normalizeEntry(entry) {
        const source = entry || {};
        const pullRequest = source.pullRequest || {};

        return {
            id: String(source.id || ""),
            position: Number(source.position || 0),
            state: String(source.state || "").toUpperCase(),
            stateLabel: entryStateLabel(source),
            enqueuedAt: String(source.enqueuedAt || ""),
            estimatedTimeToMerge:
                source.estimatedTimeToMerge === null
                || source.estimatedTimeToMerge === undefined
                ? -1
                : Number(source.estimatedTimeToMerge),
            jump: Boolean(source.jump),
            solo: Boolean(source.solo),
            enqueuer:
                String(((source.enqueuer || {}).login) || ""),
            baseCommit:
                String(((source.baseCommit || {}).oid) || ""),
            headCommit:
                String(((source.headCommit || {}).oid) || ""),
            pullRequest: {
                number: Number(pullRequest.number || 0),
                title: String(pullRequest.title || ""),
                url: String(pullRequest.url || ""),
                draft: Boolean(pullRequest.isDraft),
                headRefName: String(pullRequest.headRefName || ""),
                baseRefName: String(pullRequest.baseRefName || ""),
                headSha: String(pullRequest.headRefOid || ""),
                mergeStateStatus:
                    String(
                        pullRequest.mergeStateStatus || ""
                    ).toUpperCase(),
                mergeable:
                    String(pullRequest.mergeable || "").toUpperCase(),
                reviewDecision:
                    String(
                        pullRequest.reviewDecision || ""
                    ).toUpperCase()
            }
        };
    }

    function clearQueue() {
        queueAvailable = false;
        queueId = "";
        queueUrl = "";
        nextEntryEstimatedTimeToMerge = -1;
        configuration = {};
        entries = [];
        totalCount = 0;
    }

    function parseResponse(text) {
        const parsed = JSON.parse(String(text || "{}"));
        const repository = parsed.repository || {};
        const queue = repository.mergeQueue || null;
        const requested =
            String(parsed.requestedBranch || "").trim();
        const defaultBranch =
            String(
                ((repository.defaultBranchRef || {}).name) || ""
            );

        resolvedBranch =
            requested
            || defaultBranch;

        if (!queue) {
            clearQueue();
            return;
        }

        const connection = queue.entries || {};
        const sourceEntries =
            Array.isArray(connection.nodes)
            ? connection.nodes
            : [];
        const normalized = [];

        for (let i = 0; i < sourceEntries.length; ++i)
            normalized.push(normalizeEntry(sourceEntries[i]));

        queueAvailable = true;
        queueId = String(queue.id || "");
        queueUrl = String(queue.url || "");
        nextEntryEstimatedTimeToMerge =
            queue.nextEntryEstimatedTimeToMerge === null
            || queue.nextEntryEstimatedTimeToMerge === undefined
            ? -1
            : Number(queue.nextEntryEstimatedTimeToMerge);
        configuration = queue.configuration || {};
        entries = normalized;
        totalCount = Number(connection.totalCount || normalized.length);
    }

    function refresh(repository, branch) {
        const repo =
            normalizeRepository(
                repository === undefined || repository === null
                ? repositorySlug
                : repository
            );
        const requestedBranch =
            String(
                branch === undefined || branch === null
                ? branchName
                : branch
            ).trim();

        if (busy)
            return false;

        if (!repo) {
            clearQueue();
            resolvedBranch = "";
            lastError =
                "MERGE QUEUE UNAVAILABLE // REPOSITORY MISSING";
            status = lastError;
            refreshed();
            return false;
        }

        repositorySlug = repo;
        branchName = requestedBranch;
        busy = true;
        lastError = "";
        status =
            "MERGE QUEUE // READING // "
            + repo
            + (
                requestedBranch
                ? " // " + requestedBranch
                : " // DEFAULT BRANCH"
            );

        refreshExitSeen = false;
        refreshStdoutSeen = false;
        refreshStderrSeen = false;
        refreshExitCode = -1;
        refreshStdoutText = "";
        refreshStderrText = "";

        refreshProcess.exec([
            "bash",
            "-lc",
            [
                'repo="$1"',
                'branch="$2"',
                'limit="$3"',
                'owner="$(printf "%s" "$repo" | cut -d/ -f1)"',
                'name="$(printf "%s" "$repo" | cut -d/ -f2-)"',
                'if [ -z "$owner" ] || [ -z "$name" ] || [ "$owner" = "$name" ]; then',
                '  printf "INVALID REPOSITORY SLUG\\n" >&2',
                '  exit 21',
                'fi',
                'if [ -n "$branch" ]; then',
                "  query='query($owner:String!,$name:String!,$branch:String!,$limit:Int!){ repository(owner:$owner,name:$name){ defaultBranchRef{name} mergeQueue(branch:$branch){ id url nextEntryEstimatedTimeToMerge configuration{checkResponseTimeout maximumEntriesToBuild maximumEntriesToMerge mergeMethod mergingStrategy minimumEntriesToMerge minimumEntriesToMergeWaitTime} entries(first:$limit){totalCount nodes{id position state enqueuedAt estimatedTimeToMerge jump solo enqueuer{login} baseCommit{oid} headCommit{oid} pullRequest{number title url isDraft headRefName baseRefName headRefOid mergeStateStatus mergeable reviewDecision}}} } } }'",
                '  payload="$(gh api graphql -F owner="$owner" -F name="$name" -F branch="$branch" -F limit="$limit" -f query="$query")" || exit $?',
                'else',
                "  query='query($owner:String!,$name:String!,$limit:Int!){ repository(owner:$owner,name:$name){ defaultBranchRef{name} mergeQueue{ id url nextEntryEstimatedTimeToMerge configuration{checkResponseTimeout maximumEntriesToBuild maximumEntriesToMerge mergeMethod mergingStrategy minimumEntriesToMerge minimumEntriesToMergeWaitTime} entries(first:$limit){totalCount nodes{id position state enqueuedAt estimatedTimeToMerge jump solo enqueuer{login} baseCommit{oid} headCommit{oid} pullRequest{number title url isDraft headRefName baseRefName headRefOid mergeStateStatus mergeable reviewDecision}}} } } }'",
                '  payload="$(gh api graphql -F owner="$owner" -F name="$name" -F limit="$limit" -f query="$query")" || exit $?',
                'fi',
                'printf "%s" "$payload" | jq -c --arg requestedBranch "$branch" \'{requestedBranch:$requestedBranch,repository:(.data.repository // {})}\''
            ].join("\\n"),
            "pa-github-merge-queue",
            repo,
            requestedBranch,
            String(
                Math.max(
                    1,
                    Math.min(
                        100,
                        Number(maxEntries || 100)
                    )
                )
            )
        ]);

        refreshWatchdog.restart();
        return true;
    }

    function maybeFinishRefresh() {
        if (!busy
                || !refreshExitSeen
                || !refreshStdoutSeen
                || !refreshStderrSeen)
            return;

        busy = false;
        refreshWatchdog.stop();

        const output = String(refreshStdoutText || "").trim();
        const error = String(refreshStderrText || "").trim();

        if (refreshExitCode !== 0) {
            clearQueue();
            resolvedBranch = "";
            lastError =
                error
                || output
                || ("MERGE QUEUE EXIT " + refreshExitCode);
            status = "MERGE QUEUE // ERROR";
            refreshed();
            return;
        }

        try {
            parseResponse(output || "{}");
            lastError = "";

            if (!queueAvailable) {
                status =
                    "MERGE QUEUE // NOT CONFIGURED // "
                    + (resolvedBranch || "UNKNOWN BRANCH");
            } else {
                status =
                    "MERGE QUEUE // "
                    + String(totalCount)
                    + " ENTRIES // "
                    + String(mergeableCount)
                    + " READY // "
                    + String(awaitingChecksCount)
                    + " CHECKING // "
                    + String(unmergeableCount)
                    + " BLOCKED";
            }
        } catch (parseError) {
            clearQueue();
            resolvedBranch = "";
            lastError =
                "MERGE QUEUE RESPONSE PARSE // "
                + String(parseError);
            status = "MERGE QUEUE // ERROR";
        }

        refreshed();
    }

    Process {
        id: refreshProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.refreshStdoutText = this.text;
                root.refreshStdoutSeen = true;
                root.maybeFinishRefresh();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.refreshStderrText = this.text;
                root.refreshStderrSeen = true;
                root.maybeFinishRefresh();
            }
        }

        onExited: function(exitCode, exitStatus) {
            root.refreshExitCode = Number(exitCode);
            root.refreshExitSeen = true;
            root.maybeFinishRefresh();
        }
    }

    Timer {
        id: refreshWatchdog
        interval: 120000
        repeat: false

        onTriggered: {
            root.busy = false;
            clearQueue();
            root.lastError = "MERGE QUEUE REFRESH TIMEOUT";
            root.status = "MERGE QUEUE // TIMEOUT";

            if (refreshProcess.running)
                refreshProcess.running = false;

            root.refreshed();
        }
    }
}
