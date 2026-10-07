import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property var repositories: []
    property int maxPullRequestsPerRepository: 50

    property bool busy: false
    property var items: []
    property var repositoryStates: []
    property string viewerLogin: ""
    property string status: "READY"
    property string lastError: ""

    property bool refreshExitSeen: false
    property bool refreshStdoutSeen: false
    property bool refreshStderrSeen: false
    property int refreshExitCode: -1
    property string refreshStdoutText: ""
    property string refreshStderrText: ""

    signal refreshed()

    readonly property int repositoryCount:
        normalizeRepositories(repositories).length
    readonly property int itemCount: items.length
    readonly property int needsReviewCount: countWhere("needsReview")
    readonly property int requestedFromMeCount: countWhere("requestedFromMe")
    readonly property int failedCount: countWhere("failedChecks")
    readonly property int pendingCount: countWhere("pendingChecks")
    readonly property int changesRequestedCount: countWhere("changesRequested")
    readonly property int waitingCount: countWhere("waitingOnReviewer")
    readonly property int blockedCount: countWhere("blocked")
    readonly property int readyCount: countWhere("ready")

    function repositorySlug(value) {
        if (typeof value === "string")
            return String(value || "").trim();

        const row = value || {};
        return String(
            row.remoteSlug
            || row.repository
            || row.repo
            || row.slug
            || row.fullName
            || ""
        ).trim();
    }

    function normalizeRepositories(values) {
        const source = Array.isArray(values) ? values : [];
        const out = [];
        const seen = {};

        for (let i = 0; i < source.length; ++i) {
            const slug = repositorySlug(source[i]);

            if (!/^[^/\\s]+\\/[^/\\s]+$/.test(slug))
                continue;

            const key = slug.toLowerCase();
            if (seen[key])
                continue;

            seen[key] = true;
            out.push(slug);
        }

        return out;
    }

    function setRepositories(values) {
        repositories = normalizeRepositories(values);
    }

    function countWhere(field) {
        let count = 0;

        for (let i = 0; i < items.length; ++i) {
            if (Boolean((items[i] || {})[field]))
                count += 1;
        }

        return count;
    }

    function itemAt(index) {
        if (index < 0 || index >= items.length)
            return null;
        return items[index];
    }

    function itemsForRepository(repository) {
        const needle = String(repository || "").toLowerCase();

        return items.filter(function(item) {
            return String((item || {}).repository || "")
                .toLowerCase() === needle;
        });
    }

    function itemsForState(stateName) {
        const state = String(stateName || "").trim().toUpperCase();

        if (!state)
            return items.slice();

        return items.filter(function(item) {
            const states = (item || {}).attentionStates || [];
            return states.indexOf(state) >= 0;
        });
    }

    function repositoryState(repository) {
        const needle = String(repository || "").toLowerCase();

        for (let i = 0; i < repositoryStates.length; ++i) {
            const row = repositoryStates[i] || {};

            if (String(row.repository || "").toLowerCase() === needle)
                return row;
        }

        return null;
    }

    function checkCounts(row) {
        const checks =
            Array.isArray((row || {}).checkEvidence)
            ? row.checkEvidence
            : [];
        const suites =
            Array.isArray((row || {}).checkSuites)
            ? row.checkSuites
            : [];

        let passed = 0;
        let failed = 0;
        let cancelled = 0;
        let pending = 0;

        function classify(statusValue, conclusionValue) {
            const status = String(statusValue || "").toUpperCase();
            const conclusion =
                String(conclusionValue || "").toUpperCase();

            if (conclusion === "CANCELLED") {
                cancelled += 1;
                return;
            }

            if ([
                    "FAILURE",
                    "ERROR",
                    "TIMED_OUT",
                    "ACTION_REQUIRED",
                    "STARTUP_FAILURE",
                    "STALE"
                ].indexOf(conclusion) >= 0) {
                failed += 1;
                return;
            }

            if ([
                    "SUCCESS",
                    "NEUTRAL",
                    "SKIPPED"
                ].indexOf(conclusion) >= 0) {
                passed += 1;
                return;
            }

            if ([
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
                       ].indexOf(conclusion) >= 0
                    || !conclusion) {
                pending += 1;
                return;
            }

            pending += 1;
        }

        for (let i = 0; i < checks.length; ++i) {
            const check = checks[i] || {};
            const type = String(check.__typename || "");
            classify(
                check.status,
                type === "StatusContext"
                ? check.state
                : check.conclusion
            );
        }

        if (checks.length === 0) {
            for (let i = 0; i < suites.length; ++i) {
                const suite = suites[i] || {};
                classify(suite.status, suite.conclusion);
            }
        }

        return {
            total: checks.length > 0 ? checks.length : suites.length,
            passed: passed,
            failed: failed,
            cancelled: cancelled,
            pending: pending
        };
    }

    function reviewRequestFacts(row) {
        const requests =
            Array.isArray((row || {}).reviewRequests)
            ? row.reviewRequests
            : [];
        const viewer = String(viewerLogin || "").toLowerCase();
        const users = [];
        const teams = [];
        let requestedFromMe = false;

        for (let i = 0; i < requests.length; ++i) {
            const request = requests[i] || {};
            const reviewer = request.requestedReviewer || {};
            const type = String(reviewer.__typename || "");

            if (type === "User") {
                const login = String(reviewer.login || "");

                if (login)
                    users.push(login);

                if (viewer && login.toLowerCase() === viewer)
                    requestedFromMe = true;
            } else if (type === "Team") {
                const team =
                    String(reviewer.slug || reviewer.name || "");

                if (team)
                    teams.push(team);
            }
        }

        const declaredCount =
            Number((row || {}).reviewRequestCount || 0);

        return {
            count: Math.max(declaredCount, requests.length),
            users: users,
            teams: teams,
            requestedFromMe: requestedFromMe
        };
    }

    function normalizePullRequest(row) {
        const source = row || {};
        const checks = checkCounts(source);
        const reviews = reviewRequestFacts(source);

        const state = String(source.state || "").toUpperCase();
        const reviewDecision =
            String(source.reviewDecision || "").toUpperCase();
        const mergeState =
            String(source.mergeStateStatus || "").toUpperCase();
        const mergeable =
            String(source.mergeable || "").toUpperCase();
        const draft = Boolean(source.isDraft);

        const failedChecks = checks.failed > 0;
        const pendingChecks = checks.pending > 0;
        const changesRequested =
            reviewDecision === "CHANGES_REQUESTED";
        const requestedFromMe = Boolean(reviews.requestedFromMe);
        const needsReview =
            requestedFromMe
            || reviewDecision === "REVIEW_REQUIRED"
            || reviews.count > 0;
        const waitingOnReviewer =
            reviews.count > 0
            && !requestedFromMe
            && !changesRequested;

        const mergeConflict =
            mergeable === "CONFLICTING"
            || mergeState === "DIRTY";
        const mergeBlocked =
            ["BLOCKED", "DIRTY"].indexOf(mergeState) >= 0;

        const blocked =
            failedChecks
            || changesRequested
            || mergeConflict
            || mergeBlocked;

        const waiting =
            draft
            || pendingChecks
            || waitingOnReviewer
            || ["BEHIND", "UNSTABLE", "UNKNOWN"]
                .indexOf(mergeState) >= 0;

        const reviewSatisfied =
            reviewDecision === "APPROVED"
            || (!reviewDecision && reviews.count === 0);

        const mergeSatisfied =
            mergeable === "MERGEABLE"
            && ["BLOCKED", "DIRTY", "BEHIND", "UNSTABLE", "UNKNOWN"]
                .indexOf(mergeState) < 0;

        const ready =
            state === "OPEN"
            && !draft
            && !blocked
            && !pendingChecks
            && reviewSatisfied
            && mergeSatisfied;

        const attentionStates = [];

        if (requestedFromMe)
            attentionStates.push("NEEDS_ME");
        if (failedChecks)
            attentionStates.push("FAILED");
        if (blocked)
            attentionStates.push("BLOCKED");
        if (waiting)
            attentionStates.push("WAITING");
        if (ready)
            attentionStates.push("READY");
        if (needsReview)
            attentionStates.push("NEEDS_REVIEW");
        if (changesRequested)
            attentionStates.push("CHANGES_REQUESTED");
        if (waitingOnReviewer)
            attentionStates.push("WAITING_ON_REVIEWER");
        if (pendingChecks)
            attentionStates.push("PENDING_CHECKS");

        let primaryState = "CLEAR";

        if (requestedFromMe)
            primaryState = "NEEDS_ME";
        else if (failedChecks)
            primaryState = "FAILED";
        else if (blocked)
            primaryState = "BLOCKED";
        else if (waiting)
            primaryState = "WAITING";
        else if (ready)
            primaryState = "READY";
        else if (needsReview)
            primaryState = "NEEDS_REVIEW";

        return {
            kind: "pull_request",
            repository: String(source.repository || ""),
            number: Number(source.number || 0),
            title: String(source.title || ""),
            url: String(source.url || ""),
            author: String(((source.author || {}).login) || ""),
            updatedAt: String(source.updatedAt || ""),
            headRefName: String(source.headRefName || ""),
            baseRefName: String(source.baseRefName || ""),
            headSha: String(source.headRefOid || ""),
            state: state,
            draft: draft,
            reviewDecision: reviewDecision,
            reviewRequestCount: reviews.count,
            reviewRequestUsers: reviews.users,
            reviewRequestTeams: reviews.teams,
            requestedFromMe: requestedFromMe,
            needsReview: needsReview,
            changesRequested: changesRequested,
            waitingOnReviewer: waitingOnReviewer,
            checkTotal: checks.total,
            checkPassed: checks.passed,
            checkFailed: checks.failed,
            checkCancelled: checks.cancelled,
            checkPending: checks.pending,
            failedChecks: failedChecks,
            pendingChecks: pendingChecks,
            checkEvidenceSource:
                String(source.checkEvidenceSource || ""),
            checkEvidenceError:
                String(source.checkEvidenceError || ""),
            mergeable: mergeable,
            mergeStateStatus: mergeState,
            blocked: blocked,
            waiting: waiting,
            ready: ready,
            primaryState: primaryState,
            attentionStates: attentionStates
        };
    }

    function parseResponse(text) {
        const parsed = JSON.parse(String(text || "{}"));
        const source =
            Array.isArray(parsed.pullRequests)
            ? parsed.pullRequests
            : [];
        const out = [];

        viewerLogin = String(parsed.viewerLogin || "");
        repositoryStates =
            Array.isArray(parsed.repositories)
            ? parsed.repositories
            : [];

        for (let i = 0; i < source.length; ++i)
            out.push(normalizePullRequest(source[i]));

        items = out;
    }

    function refresh(values) {
        const targets =
            normalizeRepositories(
                values === undefined || values === null
                ? repositories
                : values
            );

        if (busy)
            return false;

        if (targets.length === 0) {
            items = [];
            repositoryStates = [];
            viewerLogin = "";
            lastError =
                "ATTENTION UNAVAILABLE // NO GITHUB REPOSITORIES";
            status = lastError;
            refreshed();
            return false;
        }

        repositories = targets;
        busy = true;
        items = [];
        repositoryStates = [];
        lastError = "";
        status =
            "ATTENTION // READING "
            + String(targets.length)
            + " REPOSITORIES";

        refreshExitSeen = false;
        refreshStdoutSeen = false;
        refreshStderrSeen = false;
        refreshExitCode = -1;
        refreshStdoutText = "";
        refreshStderrText = "";

        const args = [
            "bash",
            "-lc",
            [
                'limit="$1"',
                'shift',
                'viewer="$(gh api user --jq ".login" 2>/dev/null)" || {',
                '  printf "VIEWER LOOKUP FAILED\\n" >&2',
                '  exit 20',
                '}',
                'tmpdir="$(mktemp -d)"',
                'trap \\'rm -rf "$tmpdir"\\' EXIT',
                'rows_file="$tmpdir/pulls.ndjson"',
                'states_file="$tmpdir/repos.ndjson"',
                ': > "$rows_file"',
                ': > "$states_file"',
                'for repo in "$@"; do',
                '  owner="$(printf "%s" "$repo" | cut -d/ -f1)"',
                '  name="$(printf "%s" "$repo" | cut -d/ -f2-)"',
                '  if [ -z "$owner" ] || [ -z "$name" ] || [ "$owner" = "$name" ]; then',
                '    jq -nc --arg repository "$repo" \\'{repository:$repository,state:"ERROR",error:"INVALID REPOSITORY SLUG",pullRequestCount:0}\\' >> "$states_file"',
                '    continue',
                '  fi',
                "  query='query($owner:String!,$name:String!,$limit:Int!){ repository(owner:$owner,name:$name){ pullRequests(first:$limit,states:OPEN,orderBy:{field:UPDATED_AT,direction:DESC}){ nodes{ number title state url isDraft updatedAt author{login} headRefName baseRefName headRefOid reviewDecision mergeStateStatus mergeable reviewRequests(first:50){totalCount nodes{requestedReviewer{__typename ... on User{login} ... on Team{slug name}}}} commits(last:1){nodes{commit{statusCheckRollup{state contexts(first:100){nodes{__typename ... on CheckRun{name status conclusion} ... on StatusContext{context state}}}}}}} } } } }'",
                '  payload="$(gh api graphql -F owner="$owner" -F name="$name" -F limit="$limit" -f query="$query" 2>"$tmpdir/error")" || {',
                '    detail="$(cat "$tmpdir/error" 2>/dev/null)"',
                '    if [ -z "$detail" ]; then detail="REPOSITORY READ FAILED"; fi',
                '    jq -nc --arg repository "$repo" --arg error "$detail" \\'{repository:$repository,state:"ERROR",error:$error,pullRequestCount:0}\\' >> "$states_file"',
                '    continue',
                '  }',
                '  rows="$(printf "%s" "$payload" | jq -c ".data.repository.pullRequests.nodes // []")"',
                '  count="$(printf "%s" "$rows" | jq "length")"',
                '  jq -nc --arg repository "$repo" --argjson count "$count" \\'{repository:$repository,state:"OK",error:"",pullRequestCount:$count}\\' >> "$states_file"',
                '  printf "%s" "$rows" | jq -c ".[]" | while IFS= read -r row; do',
                '    sha="$(printf "%s" "$row" | jq -r ".headRefOid // \\"\\"")"',
                '    checks="$(printf "%s" "$row" | jq -c ".commits.nodes[0].commit.statusCheckRollup.contexts.nodes // []")"',
                '    check_source="rollup"',
                '    check_error=""',
                '    suites="[]"',
                '    if [ "$(printf "%s" "$checks" | jq "length")" -eq 0 ] && [ -n "$sha" ]; then',
                '      check_source="direct"',
                '      runs_ok=1',
                '      statuses_ok=1',
                '      suites_ok=1',
                '      runs="$(gh api -H "Accept: application/vnd.github+json" "repos/$repo/commits/$sha/check-runs?per_page=100" --jq "[.check_runs[]? | {__typename:\\"CheckRun\\",name:(.name // \\"\\"),status:(.status // \\"\\"),conclusion:(.conclusion // \\"\\")}]" 2>/dev/null)" || { runs="[]"; runs_ok=0; }',
                '      statuses="$(gh api -H "Accept: application/vnd.github+json" "repos/$repo/commits/$sha/status" --jq "[.statuses[]? | {__typename:\\"StatusContext\\",context:(.context // \\"\\"),state:(.state // \\"\\")}]" 2>/dev/null)" || { statuses="[]"; statuses_ok=0; }',
                '      checks="$(jq -nc --argjson runs "$runs" --argjson statuses "$statuses" \\'$runs + $statuses\\')"',
                '      if [ "$(printf "%s" "$checks" | jq "length")" -eq 0 ]; then',
                '        suites="$(gh api -H "Accept: application/vnd.github+json" "repos/$repo/commits/$sha/check-suites?per_page=100" --jq "[.check_suites[]? | {status:(.status // \\"\\"),conclusion:(.conclusion // \\"\\")}]" 2>/dev/null)" || { suites="[]"; suites_ok=0; }',
                '      fi',
                '      if [ "$runs_ok" -ne 1 ] && [ "$statuses_ok" -ne 1 ]; then check_error="DIRECT CHECK EVIDENCE LOOKUP FAILED"; fi',
                '      if [ "$suites_ok" -ne 1 ]; then',
                '        if [ -n "$check_error" ]; then check_error="$check_error // CHECK SUITE LOOKUP FAILED"; else check_error="CHECK SUITE LOOKUP FAILED"; fi',
                '      fi',
                '    fi',
                '    requests="$(printf "%s" "$row" | jq -c ".reviewRequests.nodes // []")"',
                '    request_count="$(printf "%s" "$row" | jq -r ".reviewRequests.totalCount // 0")"',
                '    jq -nc --arg repository "$repo" --arg viewer "$viewer" --arg source "$check_source" --arg checkError "$check_error" --argjson row "$row" --argjson checks "$checks" --argjson suites "$suites" --argjson requests "$requests" --argjson requestCount "$request_count" \\'$row + {repository:$repository,viewerLogin:$viewer,checkEvidence:$checks,checkSuites:$suites,checkEvidenceSource:$source,checkEvidenceError:$checkError,reviewRequests:$requests,reviewRequestCount:$requestCount}\\' >> "$rows_file"',
                '  done',
                'done',
                'pulls="[]"',
                'repos="[]"',
                'if [ -s "$rows_file" ]; then pulls="$(jq -s "." "$rows_file")"; fi',
                'if [ -s "$states_file" ]; then repos="$(jq -s "." "$states_file")"; fi',
                'jq -nc --arg viewerLogin "$viewer" --argjson pullRequests "$pulls" --argjson repositories "$repos" \\'{viewerLogin:$viewerLogin,pullRequests:$pullRequests,repositories:$repositories}\\''
            ].join("\\n"),
            "pa-github-attention",
            String(
                Math.max(
                    1,
                    Math.min(
                        100,
                        Number(maxPullRequestsPerRepository || 50)
                    )
                )
            )
        ];

        for (let i = 0; i < targets.length; ++i)
            args.push(targets[i]);

        refreshProcess.exec(args);
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
            items = [];
            repositoryStates = [];
            viewerLogin = "";
            lastError =
                error
                || output
                || ("ATTENTION EXIT " + refreshExitCode);
            status = "ATTENTION // ERROR";
            refreshed();
            return;
        }

        try {
            parseResponse(output || "{}");

            let failedRepositories = 0;

            for (let i = 0; i < repositoryStates.length; ++i) {
                if (String(
                        (repositoryStates[i] || {}).state || ""
                    ).toUpperCase() !== "OK")
                    failedRepositories += 1;
            }

            lastError =
                failedRepositories > 0
                ? String(failedRepositories)
                  + " REPOSITORY"
                  + (failedRepositories === 1 ? "" : "IES")
                  + " FAILED"
                : "";

            status =
                "ATTENTION // "
                + String(items.length)
                + " OPEN PRS // "
                + String(readyCount)
                + " READY // "
                + String(blockedCount)
                + " BLOCKED // "
                + String(requestedFromMeCount)
                + " NEEDS ME";
        } catch (parseError) {
            items = [];
            repositoryStates = [];
            viewerLogin = "";
            lastError =
                "ATTENTION RESPONSE PARSE // "
                + String(parseError);
            status = "ATTENTION // ERROR";
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
            root.lastError = "ATTENTION REFRESH TIMEOUT";
            root.status = "ATTENTION // TIMEOUT";

            if (refreshProcess.running)
                refreshProcess.running = false;

            root.refreshed();
        }
    }
}
