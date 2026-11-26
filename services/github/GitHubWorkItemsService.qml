import QtQuick
import Quickshell
import Quickshell.Io
import "GitHubToolboxBatch.js" as GitHubBatch

Scope {
    id: root

    property string repoSlug: ""

    property bool issuesBusy: false
    property bool pullsBusy: false

    property var issues: []
    property var pulls: []
    property string pullsRequestRepo: ""
    property int pullsRequestNumber: 0
    property string pullsPublishedRepo: ""
    property string pullsPendingRepo: ""
    property int pullsPendingNumber: 0
    property int pullsRepoEpoch: 0
    property int pullsRequestEpoch: 0
    property int pullsPageCount: 0
    property int pullsStreamOffset: 0
    property string pullsStreamError: ""
    property bool pullsTimedOut: false
    property double pullsListCompletedAtMs: 0
    property double pullsStartedAtMs: 0
    property int pullsFirstPageMs: -1
    property int pullsFullLoadMs: -1
    readonly property int pullsCacheMaxAgeMs: 30000

    onRepoSlugChanged: {
        pullsRepoEpoch += 1;
        pullsListCompletedAtMs = 0;
        pullsFirstPageMs = -1;
        pullsFullLoadMs = -1;
        pulls = [];
        pullsPublishedRepo = "";
        pullsPendingRepo = "";
        pullsPendingNumber = 0;
        pullsError = "";
        pullsStateText = "PULLS // READY";
    }

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
        const source = row || {};
        const counts = pullCheckCounts(source);

        if (counts.total > 0) {
            if (counts.failed > 0 || counts.cancelled > 0)
                return "FAIL";

            if (counts.pending > 0)
                return "PENDING";

            return "PASS";
        }

        const state = pullCheckRollupState(source);

        if (state === "SUCCESS")
            return "PASS";

        if (state === "FAILURE" || state === "ERROR")
            return "FAIL";

        if (state === "PENDING" || state === "EXPECTED")
            return "PENDING";

        const suiteCounts = pullCheckSuiteCounts(source);

        if (suiteCounts.total > 0) {
            if (suiteCounts.failed > 0
                    || suiteCounts.startupFailed > 0
                    || suiteCounts.cancelled > 0)
                return "FAIL";

            if (suiteCounts.pending > 0)
                return "PENDING";

            return "PASS";
        }

        if (String(source.checkEvidenceError || "").trim()
                || String(source.suiteError || "").trim())
            return "ERROR";

        return source.checkDetailsDeferred ? "UNKNOWN" : "NONE";
    }

    function pullCheckSummary(row) {
        const source = row || {};
        const counts = pullCheckCounts(source);
        const rollupState = pullCheckRollupState(source);

        if (counts.total > 0) {
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
                counts.failed > 0 || counts.cancelled > 0
                ? "FAILURE"
                : counts.pending > 0
                ? "PENDING"
                : "SUCCESS";

            return (
                stateText
                + " // "
                + parts.join(" · ")
            );
        }

        if (rollupState)
            return rollupState;

        const suiteCounts = pullCheckSuiteCounts(source);

        if (suiteCounts.total === 0) {
            if (String(source.checkEvidenceError || "").trim()
                    || String(source.suiteError || "").trim())
                return "ERROR";

            return source.checkDetailsDeferred ? "DETAILS NOT LOADED" : "NONE";
        }

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

        return source.reviewDetailsDeferred ? "UNKNOWN" : "NONE";
    }

    function pullReviewSummary(row) {
        const state = pullReviewState(row);
        if ((row || {}).reviewDetailsDeferred)
            return state === "UNKNOWN" ? "DETAILS NOT LOADED" : state + " // DETAILS ON OPEN";
        const approvals = pullApprovalCount(row);
        const countText =
            String(approvals)
            + " APPROVAL"
            + (approvals === 1 ? "" : "S");

        if (state === "REVIEW_REQUIRED")
            return "REQUIRED // " + countText;

        if (state === "ERROR")
            return "ERROR // REVIEW EVIDENCE";
        if (state === "UNKNOWN")
            return "DETAILS NOT LOADED";

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

    // Only automatic opening uses the freshness window. Explicit refresh
    // and mutation-driven reads continue through refreshPulls.
    function ensurePulls(repo) {
        const clean = String(repo || "").trim();
        if (!clean || clean.toLowerCase() !== repoSlug.toLowerCase())
            return false;
        if (pullsBusy && pullsRequestNumber === 0
                && pullsRequestEpoch === pullsRepoEpoch
                && pullsRequestRepo.toLowerCase() === clean.toLowerCase())
            return true;
        const age = Date.now() - pullsListCompletedAtMs;
        if (!pullsError && pullsPublishedRepo.toLowerCase() === clean.toLowerCase()
                && pullsListCompletedAtMs > 0 && age >= 0 && age < pullsCacheMaxAgeMs)
            return true;
        return refreshPulls(clean, 0);
    }

    function refreshPulls(repo, number) {
        const cleanRepo = String(repo || repoSlug || "").trim();
        const target = Number(number || 0);
        if (!Number.isSafeInteger(target) || target < 0 || target > 2147483647)
            return false;
        if (cleanRepo.toLowerCase() !== repoSlug.toLowerCase())
            return false;
        if (pullsBusy || pullsProcess.running) {
            // Last requested target wins; never publish another repository.
            pullsPendingRepo = cleanRepo;
            pullsPendingNumber = target;
            return false;
        }

        if (!cleanRepo) {
            pullsError = "PULLS UNAVAILABLE // ACTIVE REPOSITORY MISSING";
            pullsStateText = pullsError;
            pulls = [];
            return false;
        }

        if (target === 0) {
            pullsListCompletedAtMs = 0;
            pullsStartedAtMs = Date.now();
            pullsFirstPageMs = -1;
            pullsFullLoadMs = -1;
        }
        pullsRequestRepo = cleanRepo;
        pullsRequestNumber = target;
        pullsRequestEpoch = pullsRepoEpoch;
        pullsPageCount = 0;
        pullsStreamOffset = 0;
        pullsStreamError = "";
        pullsTimedOut = false;
        pullsPendingRepo = "";
        pullsPendingNumber = 0;
        pullsBusy = true;
        pullsError = "";
        pullsStateText = target > 0 ? "READING PR #" + target : "READING PULL REQUESTS";
        pullsStdoutSeen = false;
        pullsStderrSeen = false;
        pullsExitSeen = false;
        pullsExitCode = -1;
        pullsStdout = "";
        pullsStderr = "";

        pullsProcess.exec(GitHubBatch.wrap(
            [
                'set -eo pipefail',
                'repo="$1"',
                'owner="${repo%%/*}"',
                'name="${repo#*/}"',
                "[[ \"$repo\" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || { echo \"PULLS REQUEST // INVALID REPOSITORY\" >&2; exit 1; }",
                "query='query($owner:String!,$name:String!,$cursor:String,$size:Int!){repository(owner:$owner,name:$name){pullRequests(first:$size,after:$cursor,orderBy:{field:UPDATED_AT,direction:DESC}){pageInfo{hasNextPage endCursor} nodes{number title state url isDraft updatedAt author{login} headRefName baseRefName headRefOid reviewDecision mergeStateStatus mergeable reviewRequests(first:1){totalCount} commits(last:1){nodes{commit{statusCheckRollup{state}}}}}}}}'",
                "target=\"${2:-0}\"",
                "detail_query='query($owner:String!,$name:String!,$number:Int!){ repository(owner:$owner,name:$name){ pullRequest(number:$number){ number title state url isDraft updatedAt author{login} headRefName baseRefName headRefOid reviewDecision mergeStateStatus mergeable reviewRequests(first:20){totalCount} reviews(first:100){nodes{state author{login}}} commits(last:1){ nodes{ commit{ statusCheckRollup{ state contexts(first:100){ nodes{ __typename ... on CheckRun{name status conclusion} ... on StatusContext{context state} } } } } } } } } }'",
                "tmpdir=\"$(mktemp -d)\"",
                "trap 'rm -rf \"$tmpdir\"' EXIT",
                "cursor=\"\"",
                "for page in 1 2; do",
                "  size=25; [ \"$page\" -eq 1 ] || size=75",
                "  args=(-F size=\"$size\"); active_query=\"$query\"; [ -z \"$cursor\" ] || args+=(-f cursor=\"$cursor\")",
                "  if [ \"$target\" -gt 0 ]; then active_query=\"$detail_query\"; args=(-F number=\"$target\"); fi",
                "  rc=0",
                "  gh api graphql --include -f owner=\"$owner\" -f name=\"$name\" -f query=\"$active_query\" \"${args[@]}\" > \"$tmpdir/response\" 2> \"$tmpdir/gh-error\" || rc=$?",
                "  status=\"\"; content_type=\"\"; header_end=0",
                "  {",
                "    IFS= read -r line || true",
                "    status=\"$(printf \"%s\\n\" \"$line\" | awk '{print $2}')\"",
                "    if [[ \"$line\" == HTTP/* && \"$status\" =~ ^[0-9]{3}$ ]]; then",
                "      while IFS= read -r line; do",
                "        line=\"${line%$'\\r'}\"",
                "        if [ -z \"$line\" ]; then header_end=1; break; fi",
                "        case \"${line,,}\" in",
                "          content-type:*) content_type=\"${line#*:}\";;",
                "        esac",
                "      done",
                "      cat > \"$tmpdir/body.json\"",
                "    fi",
                "  } < \"$tmpdir/response\"",
                "  if [ \"$header_end\" -ne 1 ]; then",
                "    echo \"PULLS TRANSPORT // PAGE $page // NO COMPLETE HTTP HEADERS // GH EXIT $rc\" >&2; exit 1",
                "  fi",
                "  if [ \"$status\" != 200 ]; then",
                "    case \"$status\" in 401) reason=\"AUTHENTICATION REQUIRED\";; 403|429) reason=\"ACCESS OR RATE LIMIT\";; 5??) reason=\"GITHUB OR UPSTREAM FAILURE\";; *) reason=\"REQUEST REJECTED\";; esac",
                "    echo \"PULLS HTTP $status // PAGE $page // $reason\" >&2; exit 1",
                "  fi",
                "  case \"${content_type,,}\" in *application/json*|*application/*+json*) ;; *) echo \"PULLS RESPONSE // PAGE $page // NON-JSON CONTENT TYPE\" >&2; exit 1;; esac",
                "  if ! jq -e -s 'length == 1 and (.[0] | type == \"object\")' \"$tmpdir/body.json\" >/dev/null 2>&1; then",
                "    echo \"PULLS RESPONSE // PAGE $page // EMPTY OR INVALID JSON\" >&2; exit 1",
                "  fi",
                "  if jq -e '(.errors // []) | length > 0' \"$tmpdir/body.json\" >/dev/null 2>&1; then",
                "    echo \"PULLS GRAPHQL // PAGE $page // PROVIDER REPORTED ERRORS\" >&2; exit 1",
                "  fi",
                "  if [ \"$rc\" -ne 0 ]; then echo \"PULLS TRANSPORT // PAGE $page // GH EXIT $rc\" >&2; exit 1; fi",
                "  if [ \"$target\" -gt 0 ]; then",
                "    if ! jq -e --argjson target \"$target\" '.data.repository.pullRequest | (type == \"object\") and (.number == $target) and (.headRefOid | type == \"string\" and test(\"^[0-9a-fA-F]{40}$\"))' \"$tmpdir/body.json\" >/dev/null 2>&1; then",
                "      echo \"PULLS RESPONSE // INVALID TARGET RESULT\" >&2; exit 1",
                "    fi",
                "    jq -c \"[.data.repository.pullRequest]\" \"$tmpdir/body.json\" > \"$tmpdir/page-$page.json\"",
                "    break",
                "  fi",
                "  if ! jq -e --argjson size \"$size\" '.data.repository.pullRequests | (type == \"object\") and (.nodes | type == \"array\" and length <= $size) and (.pageInfo.hasNextPage | type == \"boolean\") and (if .pageInfo.hasNextPage then (.pageInfo.endCursor | type == \"string\" and length > 0) else true end) and all(.nodes[]; (.number | type == \"number\" and . > 0 and floor == .) and (.headRefOid | type == \"string\" and test(\"^[0-9a-fA-F]{40}$\")))' \"$tmpdir/body.json\" >/dev/null 2>&1; then",
                "    echo \"PULLS RESPONSE // PAGE $page // INVALID RESULT SHAPE\" >&2; exit 1",
                "  fi",
                "  jq -c \".data.repository.pullRequests.nodes\" \"$tmpdir/body.json\" > \"$tmpdir/page-$page.json\"",
                "  jq -c 'map(. + {checkState:(.commits.nodes[0].commit.statusCheckRollup.state // \"\"),checkContexts:(.commits.nodes[0].commit.statusCheckRollup.contexts.nodes // []),checkDetailsDeferred:true,reviewDetailsDeferred:true}) | {page: ., kind:\"page\"}' \"$tmpdir/page-$page.json\"",
                "  [ \"$(jq -r \".data.repository.pullRequests.pageInfo.hasNextPage\" \"$tmpdir/body.json\")\" = true ] || break",
                "  next=\"$(jq -r \".data.repository.pullRequests.pageInfo.endCursor\" \"$tmpdir/body.json\")\"",
                "  [ \"$next\" != \"$cursor\" ] || { echo \"PULLS PAGINATION // REPEATED CURSOR\" >&2; exit 1; }",
                "  cursor=\"$next\"",
                "done",
                "jq -c -s 'add | if (map(.number) | unique | length) != length then error(\"duplicate pull request across pages\") else . end' \"$tmpdir\"/page-*.json > \"$tmpdir/rows.json\"",
                "jq -c '[.[] | . + {checkState:(.commits.nodes[0].commit.statusCheckRollup.state // \"\"),checkContexts:(.commits.nodes[0].commit.statusCheckRollup.contexts.nodes // [])}]' \"$tmpdir/rows.json\" > \"$tmpdir/normalized.json\"",
                "if [ \"$target\" -eq 0 ]; then",
                "  jq -c 'map(. + {checkDetailsDeferred:true,reviewDetailsDeferred:true})' \"$tmpdir/normalized.json\"",
                "  exit 0",
                "fi",
                "jq -c '.[] | select((((.checkContexts // []) | length) == 0) or ((.state == \"OPEN\") and ((.reviewDecision // \"\") == \"\") and (((.reviews.nodes // []) | length) == 0)))' \"$tmpdir/normalized.json\" > \"$tmpdir/fallback.ndjson\"",
                'while IFS= read -r row; do',
                '  number="$(printf "%s" "$row" | jq -r ".number")"',
                '  sha="$(printf "%s" "$row" | jq -r ".headRefOid")"',
                '  need_checks="$(printf "%s" "$row" | jq -r "(((.checkContexts // []) | length) == 0)")"',
                "  need_reviews=\"$(printf \"%s\" \"$row\" | jq -r '((.state == \"OPEN\") and ((.reviewDecision // \"\") == \"\") and (((.reviews.nodes // []) | length) == 0))')\"",
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
                "      runs=\"$(gh api -H 'Accept: application/vnd.github+json' \"repos/$repo/commits/$sha/check-runs?per_page=100\" --jq '[.check_runs[]? | {__typename:\"CheckRun\",name:(.name // \"\"),status:(.status // \"\"),conclusion:(.conclusion // \"\")}]' 2>/dev/null)\" || { runs=\"[]\"; runs_ok=0; }",
                "      statuses=\"$(gh api -H 'Accept: application/vnd.github+json' \"repos/$repo/commits/$sha/status\" --jq '[.statuses[]? | {__typename:\"StatusContext\",context:(.context // \"\"),state:(.state // \"\")}]' 2>/dev/null)\" || { statuses=\"[]\"; statuses_ok=0; }",
                '      check_evidence="$(jq -nc --argjson runs "$runs" --argjson statuses "$statuses" \'$runs + $statuses\')"',
                '      if [ "$(printf "%s" "$check_evidence" | jq "length")" -eq 0 ]; then',
                "        suites=\"$(gh api -H 'Accept: application/vnd.github+json' \"repos/$repo/commits/$sha/check-suites?per_page=100\" --jq '[.check_suites[]? | {status:(.status // \"\"),conclusion:(.conclusion // \"\")}]' 2>/dev/null)\" || { suites=\"[]\"; suites_ok=0; }",
                '      fi',
                '      [ "$runs_ok" -eq 1 ] || [ "$statuses_ok" -eq 1 ] || check_error="DIRECT CHECK EVIDENCE LOOKUP FAILED"',
                '      [ "$suites_ok" -eq 1 ] || suite_error="CHECK SUITE LOOKUP FAILED"',
                '    fi',
                '    if [ "$need_reviews" = "true" ]; then',
                '      reviews_ok=1',
                '      requests_ok=1',
                "      review_evidence=\"$(gh api -H 'Accept: application/vnd.github+json' \"repos/$repo/pulls/$number/reviews?per_page=100\" --jq '[.[]? | {state:(.state // \"\"),author:{login:(.user.login // \"\")}}]' 2>/dev/null)\" || { review_evidence=\"[]\"; reviews_ok=0; }",
                '      review_request_count="$(gh api -H "Accept: application/vnd.github+json" "repos/$repo/pulls/$number/requested_reviewers" --jq "((.users // []) | length) + ((.teams // []) | length)" 2>/dev/null)" || { review_request_count=0; requests_ok=0; }',
                '      [ "$reviews_ok" -eq 1 ] || review_error="REVIEW LOOKUP FAILED"',
                '      [ "$requests_ok" -eq 1 ] || review_request_error="REVIEW REQUEST LOOKUP FAILED"',
                '    fi',
                "    jq -nc --argjson number \"$number\" --argjson checkEvidence \"$check_evidence\" --argjson checkEvidenceLoaded \"$need_checks\" --arg checkEvidenceError \"$check_error\" --argjson checkSuites \"$suites\" --arg suiteError \"$suite_error\" --argjson reviewEvidence \"$review_evidence\" --argjson reviewEvidenceLoaded \"$need_reviews\" --arg reviewEvidenceError \"$review_error\" --argjson reviewRequestCount \"$review_request_count\" --argjson reviewRequestEvidenceLoaded \"$need_reviews\" --arg reviewRequestError \"$review_request_error\" '{number:$number,checkEvidence:$checkEvidence,checkEvidenceLoaded:$checkEvidenceLoaded,checkEvidenceError:$checkEvidenceError,checkSuites:$checkSuites,suiteError:$suiteError,reviewEvidence:$reviewEvidence,reviewEvidenceLoaded:$reviewEvidenceLoaded,reviewEvidenceError:$reviewEvidenceError,reviewRequestCount:$reviewRequestCount,reviewRequestEvidenceLoaded:$reviewRequestEvidenceLoaded,reviewRequestError:$reviewRequestError}' > \"$tmpdir/detail-$number.json\"",
                '  ) &',
                '  while [ "$(jobs -rp | wc -l)" -ge 2 ]; do',
                '    wait -n || true',
                '  done',
                'done < "$tmpdir/fallback.ndjson"',
                'wait || true',
                'printf "[]" > "$tmpdir/details.json"',
                'if ls "$tmpdir"/detail-*.json >/dev/null 2>&1; then',
                '  jq -s "." "$tmpdir"/detail-*.json > "$tmpdir/details.json"',
                'fi',
                "jq -c --slurpfile details \"$tmpdir/details.json\" 'map(. as $row | (($details[0] | map(select(.number == $row.number)) | first) // {checkEvidence:[],checkEvidenceLoaded:false,checkEvidenceError:\"\",checkSuites:[],suiteError:\"\",reviewEvidence:[],reviewEvidenceLoaded:false,reviewEvidenceError:\"\",reviewRequestCount:0,reviewRequestEvidenceLoaded:false,reviewRequestError:\"\"}) as $detail | $row + $detail)' \"$tmpdir/normalized.json\"",
                '# cleanup handled by EXIT trap',
            ].join("\n"),
            "pa-github-pulls-graphql",
            [cleanRepo, String(target)]
        ));
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

    // The collector exposes its buffer before EOF. Only complete lines
    // may be decoded, and only for the current repository generation.
    function consumePullsOutput(value) {
        const buffer = String(value || "");
        if (buffer.length < pullsStreamOffset) {
            pullsStreamError = "RESPONSE BUFFER RESET";
            return;
        }
        while (true) {
            const end = buffer.indexOf("\n", pullsStreamOffset);
            if (end < 0)
                break;
            const line = buffer.slice(pullsStreamOffset, end).trim();
            pullsStreamOffset = end + 1;
            if (!line)
                continue;
            if (pullsRequestEpoch !== pullsRepoEpoch
                    || pullsRequestRepo.toLowerCase() !== repoSlug.toLowerCase()
                    || pullsTimedOut || pullsStreamError)
                continue;
            try {
                const frame = JSON.parse(line);
                if (Array.isArray(frame)) {
                    if (pullsStdout)
                        throw new Error("DUPLICATE FINAL RESPONSE");
                    pullsStdout = line;
                    continue;
                }
                if (pullsStdout || pullsRequestNumber !== 0 || !frame || frame.kind !== "page"
                        || !Array.isArray(frame.page) || frame.page.length > (pullsPageCount === 0 ? 25 : 75)
                        || pullsPageCount >= 2)
                    throw new Error("INVALID PAGE FRAME");
                const next = pullsPageCount ? pulls.slice() : [];
                const seen = new Set(next.map(function(row) { return root.rowNumber(row); }));
                for (const row of frame.page) {
                    const number = rowNumber(row);
                    if (!Number.isSafeInteger(number) || number <= 0 || seen.has(number)
                            || !/^[0-9a-fA-F]{40}$/.test(String(row.headRefOid || "")))
                        throw new Error("INVALID OR DUPLICATE PR");
                    seen.add(number);
                    next.push(row);
                }
                if (pullsPageCount === 0)
                    pullsFirstPageMs = Math.max(0, Date.now() - pullsStartedAtMs);
                pullsPageCount += 1;
                pullsPublishedRepo = pullsRequestRepo;
                pulls = next;
                pullsStateText = "PULLS // " + next.length + " LOADED // FIRST " + pullsFirstPageMs + " ms";
                pullsRefreshed();
            } catch (e) {
                pullsStreamError = "PULL RESPONSE FRAME // " + String(e);
            }
        }
    }

    function resumePendingPulls() {
        const repo = pullsPendingRepo;
        const target = pullsPendingNumber;
        pullsPendingRepo = "";
        pullsPendingNumber = 0;
        if (repo && repo.toLowerCase() === repoSlug.toLowerCase())
            Qt.callLater(function() { root.refreshPulls(repo, target); });
    }

    function maybeFinishPulls() {
        if (!pullsBusy
                || !pullsStdoutSeen
                || !pullsStderrSeen
                || !pullsExitSeen)
            return;

        pullsBusy = false;
        pullsWatchdog.stop();
        const requestRepo = pullsRequestRepo;
        const target = pullsRequestNumber;
        if (pullsRequestEpoch !== pullsRepoEpoch || requestRepo.toLowerCase() !== repoSlug.toLowerCase()) {
            resumePendingPulls();
            return;
        }

        const output = String(pullsStdout || "").trim();
        const error = String(pullsStderr || "").trim();

        if (pullsExitCode !== 0 || pullsStreamError || pullsTimedOut) {
            pullsError = pullsTimedOut ? "PULL REQUEST LIST TIMEOUT" : (pullsStreamError || error || "PULL REQUEST LIST FAILED");
            pullsStateText = "ERROR // " + pullsError;
            // Preserve same-repository last-known rows, never another repo.
            pullsRefreshed();
            resumePendingPulls();
            return;
        }

        try {
            if (!output)
                throw new Error("EMPTY RESPONSE");
            const parsed = JSON.parse(output);
            if (!Array.isArray(parsed))
                throw new Error("EXPECTED PR ARRAY");
            if (target > 0) {
                if (parsed.length !== 1 || rowNumber(parsed[0]) !== target)
                    throw new Error("WRONG PR TARGET");
                if (pullsPublishedRepo.toLowerCase() !== requestRepo.toLowerCase())
                    throw new Error("PR LIST NOT LOADED");
                const next = pulls.slice();
                const index = next.findIndex(function(row) { return root.rowNumber(row) === target; });
                if (index < 0)
                    throw new Error("PR NO LONGER IN LIST");
                next[index] = parsed[0];
                pulls = next;
            } else {
                if (pullsPageCount === 0 || JSON.stringify(parsed) !== JSON.stringify(pulls))
                    throw new Error("FINAL RESPONSE DOES NOT MATCH VALIDATED PAGES");
                pullsPublishedRepo = requestRepo;
                pulls = parsed;
                pullsListCompletedAtMs = Date.now();
                pullsFullLoadMs = Math.max(0, pullsListCompletedAtMs - pullsStartedAtMs);
            }
            pullsStateText = "PULLS READY // " + String(pulls.length)
                + (pulls.length >= 100 ? " // LATEST 100" : "")
                + (pullsFirstPageMs >= 0 && pullsFullLoadMs >= 0
                   ? " // FIRST " + pullsFirstPageMs + " ms / ALL " + pullsFullLoadMs + " ms" : "");
            pullsError = "";
        } catch (parseError) {
            pullsError = "PULL RESPONSE PARSE // " + String(parseError);
            pullsStateText = "ERROR // " + pullsError;
        }

        pullsRefreshed();
        resumePendingPulls();
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
            waitForEnd: false
            onTextChanged: {
                if (root.pullsBusy)
                    root.consumePullsOutput(this.text);
            }
            onStreamFinished: {
                root.consumePullsOutput(this.text);
                if (this.text.length !== root.pullsStreamOffset)
                    root.pullsStreamError = "INCOMPLETE RESPONSE FRAME";
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
            // Drain the old process/collectors before starting any queued request.
            root.pullsTimedOut = true;
            if (pullsProcess.running)
                pullsProcess.running = false;
        }
    }
}
