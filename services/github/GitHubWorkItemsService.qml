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
        const source = row || {};
        const evidence = source.checkEvidence || [];

        if (source.checkEvidenceLoaded
                && evidence
                && evidence.length !== undefined
                && evidence.length > 0)
            return evidence;

        const direct = source.checkContexts || [];

        if (direct
                && direct.length !== undefined
                && direct.length > 0)
            return direct;

        const rollup = pullStatusCheckRollup(source);

        if (!rollup)
            return [];

        return (rollup.contexts || {}).nodes || [];
    }

    function pullCheckRollupState(row) {
        const source = row || {};
        const direct = String(
            source.checkState || ""
        ).toUpperCase();

        if (direct)
            return direct;

        const rollup = pullStatusCheckRollup(source);
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

    function pullCheckSuites(row) {
        const suites = (row || {}).checkSuites || [];

        if (suites && suites.length !== undefined)
            return suites;

        return [];
    }

    function pullCheckSuiteCounts(row) {
        const suites = pullCheckSuites(row);
        let passed = 0;
        let failed = 0;
        let startupFailed = 0;
        let cancelled = 0;
        let pending = 0;

        for (let i = 0; i < suites.length; ++i) {
            const suite = suites[i] || {};
            const status = String(suite.status || "").toUpperCase();
            const conclusion = String(
                suite.conclusion || ""
            ).toUpperCase();

            if (conclusion === "STARTUP_FAILURE") {
                startupFailed += 1;
            } else if (conclusion === "CANCELLED") {
                cancelled += 1;
            } else if ([
                           "FAILURE",
                           "ERROR",
                           "TIMED_OUT",
                           "ACTION_REQUIRED",
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
                       ].indexOf(status) >= 0
                       || !conclusion) {
                pending += 1;
            } else {
                pending += 1;
            }
        }

        return {
            total: suites.length,
            passed: passed,
            failed: failed,
            startupFailed: startupFailed,
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

        if (counts.total > 0) {
            if (counts.failed > 0 || counts.cancelled > 0)
                return "FAIL";

            if (counts.pending > 0)
                return "PENDING";

            return "PASS";
        }

        if (String((row || {}).suiteError || "").trim())
            return "ERROR";

        const suiteCounts = pullCheckSuiteCounts(row);

        if (suiteCounts.total === 0)
            return "NONE";

        if (suiteCounts.failed > 0
                || suiteCounts.startupFailed > 0
                || suiteCounts.cancelled > 0)
            return "FAIL";

        if (suiteCounts.pending > 0)
            return "PENDING";

        return "PASS";
    }

    function pullCheckSummary(row) {
        const rollupState = pullCheckRollupState(row);
        const counts = pullCheckCounts(row);

        if (rollupState || counts.total > 0) {
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

        if (String((row || {}).suiteError || "").trim())
            return "ERROR";

        const suiteCounts = pullCheckSuiteCounts(row);

        if (suiteCounts.total === 0)
            return "NONE";

        if (suiteCounts.startupFailed > 0
                && suiteCounts.startupFailed === suiteCounts.total) {
            return (
                "STARTUP FAILURE // "
                + String(suiteCounts.total)
                + " SUITE"
                + (suiteCounts.total === 1 ? "" : "S")
            );
        }

        const suiteParts = [];

        if (suiteCounts.passed > 0)
            suiteParts.push(String(suiteCounts.passed) + " PASS");

        if (suiteCounts.failed > 0)
            suiteParts.push(String(suiteCounts.failed) + " FAIL");

        if (suiteCounts.startupFailed > 0)
            suiteParts.push(
                String(suiteCounts.startupFailed) + " STARTUP FAILURE"
            );

        if (suiteCounts.cancelled > 0)
            suiteParts.push(String(suiteCounts.cancelled) + " CANCELLED");

        if (suiteCounts.pending > 0)
            suiteParts.push(String(suiteCounts.pending) + " PENDING");

        const suiteState =
            suiteCounts.failed > 0
            || suiteCounts.startupFailed > 0
            || suiteCounts.cancelled > 0
            ? "FAILURE"
            : suiteCounts.pending > 0
            ? "PENDING"
            : "SUCCESS";

        return (
            suiteState
            + (
                suiteParts.length > 0
                ? " // " + suiteParts.join(" · ")
                : ""
              )
        );
    }

    function pullReviewNodes(row) {
        const source = row || {};
        const evidence = source.reviewEvidence || [];

        if (source.reviewEvidenceLoaded
                && Array.isArray(evidence))
            return evidence;

        const nodes = ((source.reviews || {}).nodes || []);
        return Array.isArray(nodes) ? nodes : [];
    }

    function pullReviewRequestCount(row) {
        const source = row || {};

        if (source.reviewRequestEvidenceLoaded)
            return Number(source.reviewRequestCount || 0);

        return Number(
            ((source.reviewRequests || {}).totalCount) || 0
        );
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

        const requestCount =
            pullReviewRequestCount(source);

        if (requestCount > 0)
            return "REVIEW_REQUIRED";

        if (String(source.reviewEvidenceError || "").trim()
                || String(source.reviewRequestError || "").trim())
            return "ERROR";

        return "NONE";
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

        if (state === "ERROR")
            return "ERROR // REVIEW EVIDENCE";

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
                "query='query($owner:String!,$name:String!){ repository(owner:$owner,name:$name){ pullRequests(first:100,orderBy:{field:UPDATED_AT,direction:DESC}){ nodes{ number title state url isDraft updatedAt author{login} headRefName baseRefName headRefOid reviewDecision mergeStateStatus mergeable reviewRequests(first:20){totalCount} reviews(first:100){nodes{state author{login}}} commits(last:1){ nodes{ commit{ statusCheckRollup{ state contexts(first:100){ nodes{ __typename ... on CheckRun{name status conclusion} ... on StatusContext{context state} } } } } } } } } } }'",
                'rows="$(gh api graphql -F owner="$owner" -F name="$name" -f query="$query" --jq ".data.repository.pullRequests.nodes")" || exit $?',
                "rows=\"$(printf \"%s\" \"$rows\" | jq -c '[.[] | . + {checkState:(.commits.nodes[0].commit.statusCheckRollup.state // \"\"),checkContexts:(.commits.nodes[0].commit.statusCheckRollup.contexts.nodes // [])}]')\"",
                'tmpdir="$(mktemp -d)"',
                'printf "%s" "$rows" | jq -c ".[] | select((((.checkContexts // []) | length) == 0) or ((.state == \"OPEN\") and ((.reviewDecision // \"\") == \"\") and (((.reviews.nodes // []) | length) == 0)))" > "$tmpdir/fallback.ndjson"',
                'while IFS= read -r row; do',
                '  number="$(printf "%s" "$row" | jq -r ".number")"',
                '  sha="$(printf "%s" "$row" | jq -r ".headRefOid")"',
                '  need_checks="$(printf "%s" "$row" | jq -r "(((.checkContexts // []) | length) == 0)")"',
                '  need_reviews="$(printf "%s" "$row" | jq -r "((.state == \"OPEN\") and ((.reviewDecision // \"\") == \"\") and (((.reviews.nodes // []) | length) == 0))")"',
                '  (',
                '    check_evidence="[]"',
                '    check_error=""',
                '    suites="[]"',
                '    suite_error=""',
                '    review_evidence="[]"',
                '    review_error=""',
                '    review_request_count=0',
                '    review_request_error=""',
                '    if [ "$need_checks" = "true" ]; then',
                '      runs_ok=1',
                '      statuses_ok=1',
                '      suites_ok=1',
                '      runs="$(gh api -H "Accept: application/vnd.github+json" "repos/$repo/commits/$sha/check-runs?per_page=100" --jq "[.check_runs[]? | {__typename:\"CheckRun\",name:(.name // \"\"),status:(.status // \"\"),conclusion:(.conclusion // \"\")}]" 2>/dev/null)" || { runs="[]"; runs_ok=0; }',
                '      statuses="$(gh api -H "Accept: application/vnd.github+json" "repos/$repo/commits/$sha/status" --jq "[.statuses[]? | {__typename:\"StatusContext\",context:(.context // \"\"),state:(.state // \"\")}]" 2>/dev/null)" || { statuses="[]"; statuses_ok=0; }',
                '      suites="$(gh api -H "Accept: application/vnd.github+json" "repos/$repo/commits/$sha/check-suites?per_page=100" --jq "[.check_suites[]? | {status:(.status // \"\"),conclusion:(.conclusion // \"\")}]" 2>/dev/null)" || { suites="[]"; suites_ok=0; }',
                '      check_evidence="$(jq -nc --argjson runs "$runs" --argjson statuses "$statuses" "$runs + $statuses")"',
                '      [ "$runs_ok" -eq 1 ] || [ "$statuses_ok" -eq 1 ] || check_error="DIRECT CHECK EVIDENCE LOOKUP FAILED"',
                '      [ "$suites_ok" -eq 1 ] || suite_error="CHECK SUITE LOOKUP FAILED"',
                '    fi',
                '    if [ "$need_reviews" = "true" ]; then',
                '      reviews_ok=1',
                '      requests_ok=1',
                '      review_evidence="$(gh api -H "Accept: application/vnd.github+json" "repos/$repo/pulls/$number/reviews?per_page=100" --jq "[.[]? | {state:(.state // \"\"),author:{login:(.user.login // \"\")}}]" 2>/dev/null)" || { review_evidence="[]"; reviews_ok=0; }',
                '      review_request_count="$(gh api -H "Accept: application/vnd.github+json" "repos/$repo/pulls/$number/requested_reviewers" --jq "((.users // []) | length) + ((.teams // []) | length)" 2>/dev/null)" || { review_request_count=0; requests_ok=0; }',
                '      [ "$reviews_ok" -eq 1 ] || review_error="REVIEW LOOKUP FAILED"',
                '      [ "$requests_ok" -eq 1 ] || review_request_error="REVIEW REQUEST LOOKUP FAILED"',
                '    fi',
                '    jq -nc --argjson number "$number" --argjson checkEvidence "$check_evidence" --argjson checkEvidenceLoaded "$need_checks" --arg checkEvidenceError "$check_error" --argjson checkSuites "$suites" --arg suiteError "$suite_error" --argjson reviewEvidence "$review_evidence" --argjson reviewEvidenceLoaded "$need_reviews" --arg reviewEvidenceError "$review_error" --argjson reviewRequestCount "$review_request_count" --argjson reviewRequestEvidenceLoaded "$need_reviews" --arg reviewRequestError "$review_request_error" "{number:\$number,checkEvidence:\$checkEvidence,checkEvidenceLoaded:\$checkEvidenceLoaded,checkEvidenceError:\$checkEvidenceError,checkSuites:\$checkSuites,suiteError:\$suiteError,reviewEvidence:\$reviewEvidence,reviewEvidenceLoaded:\$reviewEvidenceLoaded,reviewEvidenceError:\$reviewEvidenceError,reviewRequestCount:\$reviewRequestCount,reviewRequestEvidenceLoaded:\$reviewRequestEvidenceLoaded,reviewRequestError:\$reviewRequestError}" > "$tmpdir/detail-$number.json"',
                '  ) &',
                '  while [ "$(jobs -rp | wc -l)" -ge 8 ]; do',
                '    wait -n || true',
                '  done',
                'done < "$tmpdir/fallback.ndjson"',
                'wait || true',
                'details_json="[]"',
                'if ls "$tmpdir"/detail-*.json >/dev/null 2>&1; then',
                '  details_json="$(jq -s "." "$tmpdir"/detail-*.json)"',
                'fi',
                "jq -nc --argjson rows "$rows" --argjson details "$details_json" '$rows | map(. as $row | (($details | map(select(.number == $row.number)) | first) // {checkEvidence:[],checkEvidenceLoaded:false,checkEvidenceError:"",checkSuites:[],suiteError:"",reviewEvidence:[],reviewEvidenceLoaded:false,reviewEvidenceError:"",reviewRequestCount:0,reviewRequestEvidenceLoaded:false,reviewRequestError:""}) as $detail | $row + $detail)'",
                'rm -rf "$tmpdir"'
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
