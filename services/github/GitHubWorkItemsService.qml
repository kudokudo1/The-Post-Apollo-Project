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

    function pullCheckCounts(row) {
        const source = row || {};
        const directChecks = Array.isArray(source.checks)
            ? source.checks
            : [];
        const listedChecks = Array.isArray(source.statusCheckRollup)
            ? source.statusCheckRollup
            : [];
        const checks =
            directChecks.length > 0
            ? directChecks
            : listedChecks;
        let passed = 0;
        let failed = 0;
        let pending = 0;

        for (let i = 0; i < checks.length; ++i) {
            const check = checks[i] || {};
            const status = String(check.status || "").toUpperCase();
            const conclusion = String(
                check.conclusion
                || check.state
                || ""
            ).toUpperCase();

            if ([
                    "FAILURE",
                    "ERROR",
                    "CANCELLED",
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
                           "PENDING"
                       ].indexOf(status) >= 0) {
                pending += 1;
            } else if (status === "COMPLETED"
                       && !conclusion) {
                passed += 1;
            } else {
                pending += 1;
            }
        }

        return {
            total: checks.length,
            passed: passed,
            failed: failed,
            pending: pending
        };
    }

    function pullCheckState(row) {
        if (String((row || {}).checksError || "").trim())
            return "ERROR";

        const counts = pullCheckCounts(row);

        if (counts.total === 0)
            return "NONE";

        if (counts.failed > 0)
            return "FAIL";

        if (counts.pending > 0)
            return "PENDING";

        return "PASS";
    }

    function pullCheckSummary(row) {
        const counts = pullCheckCounts(row);
        const state = pullCheckState(row);

        if (state === "ERROR")
            return "ERROR";

        if (state === "NONE")
            return "NONE";

        if (state === "FAIL")
            return "FAIL // " + String(counts.failed) + " FAILED";

        if (state === "PENDING")
            return (
                "PENDING // "
                + String(counts.passed)
                + "/"
                + String(counts.total)
            );

        return (
            "PASS // "
            + String(counts.passed)
            + "/"
            + String(counts.total)
        );
    }

    function pullApprovalCount(row) {
        const source = row || {};
        const directReviews = Array.isArray(source.reviews)
            ? source.reviews
            : [];
        const listedReviews = Array.isArray(source.latestReviews)
            ? source.latestReviews
            : [];
        const reviews =
            directReviews.length > 0
            ? directReviews
            : listedReviews;
        let count = 0;

        for (let i = 0; i < reviews.length; ++i) {
            const review = reviews[i] || {};
            const state = String(review.state || "").toUpperCase();

            if (state === "APPROVED")
                count += 1;
        }

        return count;
    }

    function pullReviewState(row) {
        const source = row || {};

        if (String(source.reviewError || "").trim())
            return "ERROR";

        const directReviews = Array.isArray(source.reviews)
            ? source.reviews
            : [];

        for (let i = 0; i < directReviews.length; ++i) {
            const state = String(
                (directReviews[i] || {}).state || ""
            ).toUpperCase();

            if (state === "CHANGES_REQUESTED")
                return "CHANGES REQUESTED";
        }

        const decision = String(
            source.reviewDecision || ""
        ).toUpperCase();

        if (decision === "APPROVED")
            return "APPROVED";

        if (decision === "CHANGES_REQUESTED")
            return "CHANGES REQUESTED";

        if (decision === "REVIEW_REQUIRED")
            return "REVIEW REQUIRED";

        if (pullApprovalCount(row) > 0)
            return "APPROVED";

        const requests = Array.isArray(source.reviewRequests)
            ? source.reviewRequests
            : [];

        return requests.length > 0
            ? "REVIEW REQUIRED"
            : "NO REVIEW";
    }

    function pullReviewSummary(row) {
        const state = pullReviewState(row);
        const approvals = pullApprovalCount(row);

        return (
            state
            + " // "
            + String(approvals)
            + " APPROVAL"
            + (approvals === 1 ? "" : "S")
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
                'rows="$(gh pr list --repo "$repo" --state all --limit 1000 --json number,title,state,url,isDraft,author,headRefName,baseRefName,headRefOid,updatedAt,reviewDecision)" || exit $?',
                'tmpdir="$(mktemp -d)"',
                'printf "%s" "$rows" | jq -c ".[]" > "$tmpdir/rows.ndjson"',
                'while IFS= read -r row; do',
                '  number="$(printf "%s" "$row" | jq -r ".number")"',
                '  sha="$(printf "%s" "$row" | jq -r ".headRefOid")"',
                '  (',
                '    checks_error=""',
                '    review_error=""',
                '    checks="$(gh api -H "Accept: application/vnd.github+json" "repos/$repo/commits/$sha/check-runs?per_page=100" --jq "[.check_runs[]? | {name:(.name // \\\"\\\"),status:(.status // \\\"\\\"),conclusion:(.conclusion // \\\"\\\")}]" 2>"$tmpdir/checks-$number.err")" || { checks="[]"; checks_error="$(tr "\\n" " " < "$tmpdir/checks-$number.err")"; }',
                '    reviews="$(gh api "repos/$repo/pulls/$number/reviews?per_page=100" --jq "[.[]? | select(.user.login != null) | {user:.user.login,state:(.state // \\\"\\\"),submittedAt:(.submitted_at // \\\"\\\")}] | sort_by([.user,.submittedAt]) | group_by(.user) | map(last)" 2>"$tmpdir/reviews-$number.err")" || { reviews="[]"; review_error="$(tr "\\n" " " < "$tmpdir/reviews-$number.err")"; }',
                '    requests="$(gh api "repos/$repo/pulls/$number/requested_reviewers" --jq "[.users[]?.login, .teams[]?.slug] | map(select(. != null and . != \\\"\\\"))" 2>/dev/null || printf "[]")"',
                "    jq -nc --argjson number \"$number\" --argjson checks \"$checks\" --argjson reviews \"$reviews\" --argjson requests \"$requests\" --arg checksError \"$checks_error\" --arg reviewError \"$review_error\" '{number:$number,checks:$checks,reviews:$reviews,reviewRequests:$requests,checksError:$checksError,reviewError:$reviewError}' > \"$tmpdir/detail-$number.json\"",
                '  ) &',
                '  while [ "$(jobs -rp | wc -l)" -ge 8 ]; do',
                '    wait -n || true',
                '  done',
                'done < "$tmpdir/rows.ndjson"',
                'wait || true',
                'details_json="[]"',
                'if ls "$tmpdir"/detail-*.json >/dev/null 2>&1; then',
                '  details_json="$(jq -s "." "$tmpdir"/detail-*.json)"',
                'fi',
                "jq -nc --argjson rows \"$rows\" --argjson details \"$details_json\" '$rows | map(. as $row | (($details | map(select(.number == $row.number)) | first) // {checks:[],reviews:[],reviewRequests:[],checksError:\"\",reviewError:\"\"}) as $detail | $row + {checks:$detail.checks,reviews:$detail.reviews,reviewRequests:$detail.reviewRequests,checksError:$detail.checksError,reviewError:$detail.reviewError})'",
                'rm -rf "$tmpdir"'
            ].join("\n"),
            "pa-github-pulls",
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
