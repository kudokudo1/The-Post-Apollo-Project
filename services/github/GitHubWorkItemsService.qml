import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property string repoSlug: ""

    property bool issuesBusy: false
    property bool pullsBusy: false

    property var issues: []
    property var pulls: []

    property string issuesStateText: "ISSUES // READY"
    property string pullsStateText: "PULLS // READY"
    property string issuesError: ""
    property string pullsError: ""

    property bool issuesStdoutSeen: false
    property bool issuesStderrSeen: false
    property bool issuesExitSeen: false
    property int issuesExitCode: -1
    property string issuesStdout: ""
    property string issuesStderr: ""

    property bool pullsStdoutSeen: false
    property bool pullsStderrSeen: false
    property bool pullsExitSeen: false
    property int pullsExitCode: -1
    property string pullsStdout: ""
    property string pullsStderr: ""

    signal issuesRefreshed()
    signal pullsRefreshed()

    function rowNumber(row) {
        return Number((row || {}).number || 0);
    }

    function rowTitle(row) {
        return String((row || {}).title || "UNTITLED");
    }

    function rowState(row) {
        return String((row || {}).state || "UNKNOWN").toUpperCase();
    }

    function rowUrl(row) {
        return String((row || {}).url || "");
    }

    function rowAuthor(row) {
        const author = (row || {}).author || {};
        return String(author.login || author.name || "");
    }

    function rowUpdated(row) {
        return String((row || {}).updatedAt || "");
    }

    function issueLabels(row) {
        const labels = Array.isArray((row || {}).labels)
            ? row.labels
            : [];
        const out = [];

        for (let i = 0; i < labels.length; ++i) {
            const label = labels[i] || {};
            const name = String(label.name || "").trim();

            if (name)
                out.push(name);
        }

        return out;
    }

    function pullBranches(row) {
        const source = String((row || {}).headRefName || "");
        const target = String((row || {}).baseRefName || "");

        if (!source && !target)
            return "";

        return (source || "?") + " → " + (target || "?");
    }

    function pullIsDraft(row) {
        return !!((row || {}).isDraft);
    }

    function pullStatusCheckRollup(row) {
        const commits = (((row || {}).commits || {}).nodes || []);

        if (!Array.isArray(commits) || commits.length === 0)
            return null;

        const commit = (commits[0] || {}).commit || {};
        return commit.statusCheckRollup || null;
    }

    function pullCheckContexts(row) {
        const rollup = pullStatusCheckRollup(row);

        if (!rollup)
            return [];

        const contexts = (rollup.contexts || {}).nodes || [];
        return Array.isArray(contexts) ? contexts : [];
    }

    function pullCheckRollupState(row) {
        const rollup = pullStatusCheckRollup(row);
        return String((rollup || {}).state || "").toUpperCase();
    }

    function pullCheckCounts(row) {
        const checks = pullCheckContexts(row);
        let passed = 0;
        let failed = 0;
        let cancelled = 0;
        let pending = 0;

        for (let i = 0; i < checks.length; ++i) {
            const check = checks[i] || {};
            const type = String(check.__typename || "");
            const status = String(check.status || "").toUpperCase();
            const conclusion = String(
                type === "StatusContext"
                ? check.state
                : check.conclusion
            ).toUpperCase();

            if (conclusion === "CANCELLED") {
                cancelled += 1;
            } else if ([
                           "FAILURE",
                           "ERROR",
                           "TIMED_OUT",
                           "ACTION_REQUIRED",
                           "STARTUP_FAILURE",
                           "STALE"
                       ].indexOf(conclusion) >= 0) {
                failed += 1;
            } else if ([
                           "SUCCESS",
                           "NEUTRAL",
                           "SKIPPED"
                       ].indexOf(conclusion) >= 0) {
                passed += 1;
            } else if ([
                           "QUEUED",
                           "IN_PROGRESS",
                           "WAITING",
                           "REQUESTED",
                           "PENDING",
                           "EXPECTED"
                       ].indexOf(status) >= 0
                       || [
                              "PENDING",
                              "EXPECTED"
                          ].indexOf(conclusion) >= 0) {
                pending += 1;
            } else {
                pending += 1;
            }
        }

        return {
            total: checks.length,
            passed: passed,
            failed: failed,
            cancelled: cancelled,
            pending: pending
        };
    }

    function pullCheckState(row) {
        const state = pullCheckRollupState(row);

        if (state === "SUCCESS")
            return "PASS";

        if (state === "FAILURE" || state === "ERROR")
            return "FAIL";

        if (state === "PENDING" || state === "EXPECTED")
            return "PENDING";

        const counts = pullCheckCounts(row);

        if (counts.total === 0)
            return "NONE";

        if (counts.failed > 0 || counts.cancelled > 0)
            return "FAIL";

        if (counts.pending > 0)
            return "PENDING";

        return "PASS";
    }

    function pullCheckSummary(row) {
        const rollupState = pullCheckRollupState(row);
        const counts = pullCheckCounts(row);

        if (!rollupState && counts.total === 0)
            return "NONE";

        const parts = [];

        if (counts.passed > 0)
            parts.push(String(counts.passed) + " PASS");

        if (counts.failed > 0)
            parts.push(String(counts.failed) + " FAIL");

        if (counts.cancelled > 0)
            parts.push(String(counts.cancelled) + " CANCELLED");

        if (counts.pending > 0)
            parts.push(String(counts.pending) + " PENDING");

        const stateText =
            rollupState
            || (
                counts.failed > 0 || counts.cancelled > 0
                ? "FAILURE"
                : counts.pending > 0
                ? "PENDING"
                : "SUCCESS"
               );

        return (
            stateText
            + (parts.length > 0 ? " // " + parts.join(" · ") : "")
        );
    }

    function pullReviewNodes(row) {
        const nodes = (((row || {}).reviews || {}).nodes || []);
        return Array.isArray(nodes) ? nodes : [];
    }

    function pullApprovalCount(row) {
        const reviews = pullReviewNodes(row);
        const latestByAuthor = ({});

        for (let i = 0; i < reviews.length; ++i) {
            const review = reviews[i] || {};
            const author = (review.author || {}).login;
            const key = String(author || "");

            if (!key)
                continue;

            latestByAuthor[key] = String(
                review.state || ""
            ).toUpperCase();
        }

        let count = 0;
        const authors = Object.keys(latestByAuthor);

        for (let i = 0; i < authors.length; ++i) {
            if (latestByAuthor[authors[i]] === "APPROVED")
                count += 1;
        }

        return count;
    }

    function pullReviewState(row) {
        const source = row || {};
        const decision = String(
            source.reviewDecision || ""
        ).toUpperCase();

        if (decision)
            return decision;

        if (pullApprovalCount(source) > 0)
            return "APPROVED";

        const requestCount = Number(
            ((source.reviewRequests || {}).totalCount) || 0
        );

        return requestCount > 0
            ? "REVIEW_REQUIRED"
            : "NONE";
    }

    function pullReviewSummary(row) {
        const state = pullReviewState(row);
        const approvals = pullApprovalCount(row);
        const countText =
            String(approvals)
            + " APPROVAL"
            + (approvals === 1 ? "" : "S");

        if (state === "REVIEW_REQUIRED")
            return "REQUIRED // " + countText;

        return state + " // " + countText;
    }

    function pullMergeState(row) {
        return String(
            (row || {}).mergeStateStatus || "UNKNOWN"
        ).toUpperCase();
    }

    function pullMergeSummary(row) {
        const state = pullMergeState(row);
        const mergeable = String(
            (row || {}).mergeable || ""
        ).toUpperCase();

        return (
            state
            + (
                mergeable
                ? " · " + mergeable
                : ""
              )
        );
    }

    function refreshIssues(repo) {
        const cleanRepo = String(repo || repoSlug || "").trim();

        if (issuesBusy)
            return false;

        if (!cleanRepo) {
            issuesError = "ISSUES UNAVAILABLE // ACTIVE REPOSITORY MISSING";
            issuesStateText = issuesError;
            issues = [];
            return false;
        }

        issuesBusy = true;
        issuesError = "";
        issuesStateText = "READING ISSUES";
        issuesStdoutSeen = false;
        issuesStderrSeen = false;
        issuesExitSeen = false;
        issuesExitCode = -1;
        issuesStdout = "";
        issuesStderr = "";

        issuesProcess.exec([
            "bash",
            "-lc",
            'exec gh issue list --repo "$1" --state all --limit 1000 --json number,title,state,url,labels,author,updatedAt',
            "pa-github-issues",
            cleanRepo
        ]);
        issuesWatchdog.restart();
        return true;
    }

    function refreshPulls(repo) {
        const cleanRepo = String(repo || repoSlug || "").trim();

        if (pullsBusy)
            return false;

        if (!cleanRepo) {
            pullsError = "PULLS UNAVAILABLE // ACTIVE REPOSITORY MISSING";
            pullsStateText = pullsError;
            pulls = [];
            return false;
        }

        pullsBusy = true;
        pullsError = "";
        pullsStateText = "READING PULL REQUESTS";
        pullsStdoutSeen = false;
        pullsStderrSeen = false;
        pullsExitSeen = false;
        pullsExitCode = -1;
        pullsStdout = "";
        pullsStderr = "";

        pullsProcess.exec([
            "bash",
            "-lc",
            [
                'repo="$1"',
                'owner="${repo%%/*}"',
                'name="${repo#*/}"',
                "query='query($owner:String!,$name:String!){repository(owner:$owner,name:$name){pullRequests(first:100,orderBy:{field:UPDATED_AT,direction:DESC}){nodes{number title state url isDraft updatedAt author{login} headRefName baseRefName headRefOid reviewDecision mergeStateStatus mergeable reviewRequests(first:20){totalCount} reviews(first:100){nodes{state author{login}}} commits(last:1){nodes{commit{statusCheckRollup{state contexts(first:100){nodes{__typename ... on CheckRun{name status conclusion} ... on StatusContext{context state}}}}}}}}}}}}}'",
                'exec gh api graphql -F owner="$owner" -F name="$name" -f query="$query" --jq ".data.repository.pullRequests.nodes"'
            ].join("\n"),
            "pa-github-pulls-graphql",
            cleanRepo
        ]);
        pullsWatchdog.restart();
        return true;
    }

    function maybeFinishIssues() {
        if (!issuesBusy
                || !issuesStdoutSeen
                || !issuesStderrSeen
                || !issuesExitSeen)
            return;

        issuesBusy = false;
        issuesWatchdog.stop();

        const output = String(issuesStdout || "").trim();
        const error = String(issuesStderr || "").trim();

        if (issuesExitCode !== 0) {
            issuesError = error || output || "ISSUE LIST FAILED";
            issuesStateText = "ERROR // " + issuesError;
            issues = [];
            issuesRefreshed();
            return;
        }

        try {
            const parsed = JSON.parse(output || "[]");
            issues = Array.isArray(parsed) ? parsed : [];
            issuesStateText =
                "ISSUES READY // "
                + String(issues.length);
            issuesError = "";
        } catch (parseError) {
            issues = [];
            issuesError = "ISSUE RESPONSE PARSE // " + String(parseError);
            issuesStateText = "ERROR // " + issuesError;
        }

        issuesRefreshed();
    }

    function maybeFinishPulls() {
        if (!pullsBusy
                || !pullsStdoutSeen
                || !pullsStderrSeen
                || !pullsExitSeen)
            return;

        pullsBusy = false;
        pullsWatchdog.stop();

        const output = String(pullsStdout || "").trim();
        const error = String(pullsStderr || "").trim();

        if (pullsExitCode !== 0) {
            pullsError = error || output || "PULL REQUEST LIST FAILED";
            pullsStateText = "ERROR // " + pullsError;
            pulls = [];
            pullsRefreshed();
            return;
        }

        try {
            const parsed = JSON.parse(output || "[]");
            pulls = Array.isArray(parsed) ? parsed : [];
            pullsStateText =
                "PULLS READY // "
                + String(pulls.length);
            pullsError = "";
        } catch (parseError) {
            pulls = [];
            pullsError = "PULL RESPONSE PARSE // " + String(parseError);
            pullsStateText = "ERROR // " + pullsError;
        }

        pullsRefreshed();
    }

    Process {
        id: issuesProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.issuesStdout = this.text;
                root.issuesStdoutSeen = true;
                root.maybeFinishIssues();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.issuesStderr = this.text;
                root.issuesStderrSeen = true;
                root.maybeFinishIssues();
            }
        }

        onExited: function(exitCode, exitStatus) {
            root.issuesExitCode = Number(exitCode);
            root.issuesExitSeen = true;
            root.maybeFinishIssues();
        }
    }

    Process {
        id: pullsProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.pullsStdout = this.text;
                root.pullsStdoutSeen = true;
                root.maybeFinishPulls();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.pullsStderr = this.text;
                root.pullsStderrSeen = true;
                root.maybeFinishPulls();
            }
        }

        onExited: function(exitCode, exitStatus) {
            root.pullsExitCode = Number(exitCode);
            root.pullsExitSeen = true;
            root.maybeFinishPulls();
        }
    }

    Timer {
        id: issuesWatchdog
        interval: 120000
        repeat: false

        onTriggered: {
            root.issuesBusy = false;
            root.issuesError = "ISSUE LIST TIMEOUT";
            root.issuesStateText = "ERROR // " + root.issuesError;

            if (issuesProcess.running)
                issuesProcess.running = false;

            root.issuesRefreshed();
        }
    }

    Timer {
        id: pullsWatchdog
        interval: 120000
        repeat: false

        onTriggered: {
            root.pullsBusy = false;
            root.pullsError = "PULL REQUEST LIST TIMEOUT";
            root.pullsStateText = "ERROR // " + root.pullsError;

            if (pullsProcess.running)
                pullsProcess.running = false;

            root.pullsRefreshed();
        }
    }
}
