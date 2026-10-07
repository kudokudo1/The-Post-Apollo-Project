import QtQuick
import Quickshell
import Quickshell.Io

// Safe stacked-branch submission to GitHub.
//
// Workflow:
//   PREVIEW -> ARM -> SUBMIT
//
// PREVIEW is read-only. SUBMIT verifies the previewed local + remote heads,
// atomically pushes every branch with exact force-with-lease guards, then
// creates/reuses/retargets/reopens pull requests in stack order.
Scope {
    id: root

    required property var branchStackStore
    required property var branchWorkspaceService

    property string repositoryPath: ""
    property var operationJournal: null
    property var snapshotService: null
    property string repoSlug: ""
    property string remoteName: "origin"

    property bool previewBusy: false
    property string startBranch: ""
    property var plan: []
    property string previewState: "STACK SUBMIT // READY"
    property string lastError: ""

    property bool armed: false
    property string armedFingerprint: ""
    property var armedPlan: []
    property string armStatus: "STACK SUBMIT // NOT ARMED"

    property bool submitBusy: false
    property string submitState: "STACK SUBMIT // READY"
    property var lastResult: []

    property bool previewStdoutSeen: false
    property bool previewStderrSeen: false
    property bool previewExitSeen: false
    property int previewExitCode: -1
    property string previewStdout: ""
    property string previewStderr: ""

    property bool submitStdoutSeen: false
    property bool submitStderrSeen: false
    property bool submitExitSeen: false
    property int submitExitCode: -1
    property string submitStdout: ""
    property string submitStderr: ""

    property string pendingJournalId: ""
    property string pendingSnapshotRequest: ""
    property string snapshotPhase: ""
    property var pendingSubmitArgs: []
    property bool pendingSubmissionSuccess: false
    property string pendingSubmissionDetail: ""

    signal previewReady(var plan)
    signal submissionFinished(bool success, var result)

    readonly property int invalidCount:
        plan.filter(function(row) {
            const status = String((row || {}).status || "");
            return status === "MISSING_BRANCH"
                || status === "MISSING_PARENT"
                || status === "MERGED_PR"
                || status === "ERROR";
        }).length

    readonly property int createCount:
        plan.filter(function(row) {
            return String((row || {}).status || "") === "CREATE_PR";
        }).length

    readonly property int reuseCount:
        plan.filter(function(row) {
            return [
                "READY_EXISTING",
                "UPDATE_BASE",
                "REOPEN_EXISTING",
                "REOPEN_UPDATE_BASE"
            ].indexOf(String((row || {}).status || "")) >= 0;
        }).length

    readonly property bool executable:
        plan.length > 0 && invalidCount === 0

    function clear() {
        if (submitBusy)
            return false;

        previewBusy = false;
        startBranch = "";
        plan = [];
        previewState = "STACK SUBMIT // READY";
        lastError = "";
        previewWatchdog.stop();
        disarm("");
        return true;
    }

    function structuralSteps(branch) {
        const selected = String(branch || "").trim();
        const rows = [];
        const seen = {};

        if (!selected || !branchStackStore)
            return rows;

        function appendRelation(name) {
            const child = String(name || "");
            const parent = branchStackStore.parentOf(child);

            if (!child || !parent || seen[child])
                return;

            seen[child] = true;
            rows.push({
                branch: child,
                parent: parent
            });
        }

        // Include the ancestor chain so a selected middle branch never tries
        // to target a base branch that this submission forgot to push.
        const ancestors =
            branchStackStore.ancestorsOf(selected).slice().reverse();

        for (let i = 0; i < ancestors.length; ++i)
            appendRelation(ancestors[i]);

        appendRelation(selected);

        function appendDescendants(parent) {
            const children = branchStackStore.childrenOf(parent);

            for (let i = 0; i < children.length; ++i) {
                const child = String(children[i] || "");
                appendRelation(child);
                appendDescendants(child);
            }
        }

        appendDescendants(selected);
        return rows;
    }

    function fingerprintFor(rows) {
        const source = Array.isArray(rows) ? rows : [];

        return JSON.stringify({
            repository: String(repositoryPath || ""),
            slug: String(repoSlug || ""),
            remote: String(remoteName || "origin"),
            startBranch: String(startBranch || ""),
            rows: source.map(function(row) {
                const item = row || {};
                return {
                    branch: String(item.branch || ""),
                    parent: String(item.parent || ""),
                    localHead: String(item.localHead || ""),
                    parentHead: String(item.parentHead || ""),
                    remoteHead: String(item.remoteHead || ""),
                    prNumber: String(item.prNumber || ""),
                    prState: String(item.prState || ""),
                    prBase: String(item.prBase || ""),
                    status: String(item.status || "")
                };
            })
        });
    }

    function preview(branch) {
        if (previewBusy || submitBusy)
            return false;

        const repo = String(repositoryPath || "").trim();
        const slug = String(repoSlug || "").trim();
        const selected = String(branch || "").trim();
        const remote = String(remoteName || "origin").trim() || "origin";

        if (!repo || !slug || !selected) {
            lastError =
                !repo
                ? "STACK SUBMIT PREVIEW // NO REPOSITORY"
                : !slug
                ? "STACK SUBMIT PREVIEW // NO GITHUB REPOSITORY"
                : "STACK SUBMIT PREVIEW // NO BRANCH";
            previewState = lastError;
            plan = [];
            return false;
        }

        const stackRoot =
            branchStackStore
            ? String(branchStackStore.stackRoot(selected) || "")
            : "";
        const trunk =
            branchStackStore
            ? String(branchStackStore.trunkBranch || "main")
            : "main";

        if (stackRoot && stackRoot !== trunk) {
            lastError =
                "STACK SUBMIT PREVIEW // STACK ROOT "
                + stackRoot
                + " DOES NOT REACH TRUNK "
                + trunk
                + " // SET A PARENT FIRST";
            previewState = lastError;
            plan = [];
            return false;
        }

        const steps = structuralSteps(selected);

        startBranch = selected;
        plan = [];
        lastError = "";
        disarm("NEW PREVIEW");

        if (steps.length === 0) {
            previewState = "STACK SUBMIT // NOTHING TO SUBMIT";
            previewReady(plan);
            return true;
        }

        const args = [
            "bash",
            "-lc",
            [
                'repo="$1"',
                'slug="$2"',
                'remote="$3"',
                'shift 3',
                'if ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then',
                '  printf "ERROR\\tNOT A GIT WORKTREE\\n"',
                '  exit 21',
                'fi',
                'if ! gh auth status >/dev/null 2>&1; then',
                '  printf "ERROR\\tGITHUB CLI NOT AUTHENTICATED\\n"',
                '  exit 22',
                'fi',
                'while [ "$#" -ge 2 ]; do',
                '  branch="$1"',
                '  parent="$2"',
                '  shift 2',
                '  local_head="$(git -C "$repo" rev-parse "refs/heads/$branch" 2>/dev/null || true)"',
                '  parent_head="$(git -C "$repo" rev-parse "refs/heads/$parent" 2>/dev/null || true)"',
                '  remote_head="$(git -C "$repo" ls-remote --heads "$remote" "refs/heads/$branch" 2>/dev/null | awk "NR==1{print \\$1}")"',
                '  if [ -z "$local_head" ]; then',
                '    printf "STEP\\t%s\\t%s\\t\\t%s\\t%s\\t\\t\\t\\t\\tfalse\\tMISSING_BRANCH\\n" "$branch" "$parent" "$parent_head" "$remote_head"',
                '    continue',
                '  fi',
                '  if [ -z "$parent_head" ]; then',
                '    printf "STEP\\t%s\\t%s\\t%s\\t\\t%s\\t\\t\\t\\t\\tfalse\\tMISSING_PARENT\\n" "$branch" "$parent" "$local_head" "$remote_head"',
                '    continue',
                '  fi',
                '  pr_json="$(gh pr list --repo "$slug" --head "$branch" --state all --limit 100 --json number,url,state,baseRefName,isDraft 2>/dev/null)" || {',
                '    printf "ERROR\\tPR LOOKUP FAILED // %s\\n" "$branch"',
                '    exit 23',
                '  }',
                '  pr="$(printf "%s" "$pr_json" | jq -c "sort_by(if .state == \\"OPEN\\" then 0 elif .state == \\"CLOSED\\" then 1 else 2 end) | .[0] // {}")"',
                '  number="$(printf "%s" "$pr" | jq -r ".number // empty")"',
                '  url="$(printf "%s" "$pr" | jq -r ".url // empty")"',
                '  state="$(printf "%s" "$pr" | jq -r ".state // empty")"',
                '  base="$(printf "%s" "$pr" | jq -r ".baseRefName // empty")"',
                '  draft="$(printf "%s" "$pr" | jq -r ".isDraft // false")"',
                '  status="CREATE_PR"',
                '  if [ -n "$number" ]; then',
                '    if [ "$state" = "MERGED" ]; then',
                '      status="MERGED_PR"',
                '    elif [ "$state" = "OPEN" ]; then',
                '      if [ "$base" = "$parent" ]; then status="READY_EXISTING"; else status="UPDATE_BASE"; fi',
                '    elif [ "$state" = "CLOSED" ]; then',
                '      if [ "$base" = "$parent" ]; then status="REOPEN_EXISTING"; else status="REOPEN_UPDATE_BASE"; fi',
                '    fi',
                '  fi',
                '  printf "STEP\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\n" "$branch" "$parent" "$local_head" "$parent_head" "$remote_head" "$number" "$url" "$state" "$base" "$draft" "$status"',
                'done'
            ].join("\n"),
            "git-stack-submit-preview",
            repo,
            slug,
            remote
        ];

        for (let i = 0; i < steps.length; ++i) {
            args.push(String(steps[i].branch || ""));
            args.push(String(steps[i].parent || ""));
        }

        previewBusy = true;
        previewState = "STACK SUBMIT // READING";
        previewStdoutSeen = false;
        previewStderrSeen = false;
        previewExitSeen = false;
        previewExitCode = -1;
        previewStdout = "";
        previewStderr = "";

        previewProcess.exec(args);
        previewWatchdog.restart();
        return true;
    }

    function parsePreview(text) {
        const rows = [];
        const lines = String(text || "").split("\n");

        for (let i = 0; i < lines.length; ++i) {
            const raw = String(lines[i] || "");

            if (!raw)
                continue;

            const parts = raw.split("\t");
            const kind = parts.length > 0 ? parts[0] : "";

            if (kind === "ERROR") {
                lastError =
                    parts.length > 1
                    ? parts.slice(1).join("\t")
                    : "STACK SUBMIT PREVIEW FAILED";
                continue;
            }

            if (kind !== "STEP")
                continue;

            rows.push({
                branch: parts.length > 1 ? parts[1] : "",
                parent: parts.length > 2 ? parts[2] : "",
                localHead: parts.length > 3 ? parts[3] : "",
                parentHead: parts.length > 4 ? parts[4] : "",
                remoteHead: parts.length > 5 ? parts[5] : "",
                prNumber: parts.length > 6 ? parts[6] : "",
                prUrl: parts.length > 7 ? parts[7] : "",
                prState: parts.length > 8 ? parts[8] : "",
                prBase: parts.length > 9 ? parts[9] : "",
                isDraft: parts.length > 10 ? parts[10] === "true" : false,
                status: parts.length > 11 ? parts[11] : "ERROR"
            });
        }

        plan = rows;
    }

    function maybeFinishPreview() {
        if (!previewBusy
                || !previewStdoutSeen
                || !previewStderrSeen
                || !previewExitSeen)
            return;

        previewBusy = false;
        previewWatchdog.stop();

        if (previewExitCode !== 0) {
            lastError = String(
                previewStderr
                || previewStdout
                || ("STACK SUBMIT PREVIEW EXIT " + previewExitCode)
            ).trim();
            previewState = "STACK SUBMIT // ERROR";
            plan = [];
            previewReady(plan);
            return;
        }

        parsePreview(previewStdout);

        if (lastError) {
            previewState = "STACK SUBMIT // ERROR";
        } else if (invalidCount > 0) {
            previewState =
                "STACK SUBMIT // "
                + String(invalidCount)
                + " BLOCKED";
        } else {
            previewState =
                "STACK SUBMIT // "
                + String(plan.length)
                + " PR"
                + (plan.length === 1 ? "" : "S")
                + " READY";
        }

        previewReady(plan);
    }

    function arm() {
        if (submitBusy || previewBusy) {
            lastError = "STACK SUBMIT ARM REFUSED // BUSY";
            return false;
        }

        if (!executable) {
            lastError =
                "STACK SUBMIT ARM REFUSED // VALID PREVIEW REQUIRED";
            return false;
        }

        armedPlan = plan.slice();
        armedFingerprint = fingerprintFor(armedPlan);
        armed = true;
        lastError = "";
        armStatus =
            "STACK SUBMIT // ARMED // "
            + String(armedPlan.length)
            + " PR"
            + (armedPlan.length === 1 ? "" : "S");
        armTimer.restart();
        return true;
    }

    function disarm(reason) {
        armed = false;
        armedFingerprint = "";
        armedPlan = [];
        armTimer.stop();

        armStatus = reason
            ? "STACK SUBMIT // DISARMED // " + String(reason)
            : "STACK SUBMIT // NOT ARMED";
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

        out.recoveryClass = "EVIDENCE_ONLY";
        out.recoveryReason =
            "STACK SUBMIT MUTATES REMOTE REFS + GITHUB PR STATE";

        return out;
    }

    function clearPendingSubmission() {
        pendingJournalId = "";
        pendingSnapshotRequest = "";
        snapshotPhase = "";
        pendingSubmitArgs = [];
        pendingSubmissionSuccess = false;
        pendingSubmissionDetail = "";
    }

    function journalContext() {
        const rows =
            Array.isArray(armedPlan)
            ? armedPlan
            : [];

        return {
            source: "GitStackSubmitService",
            repositorySlug: String(repoSlug || ""),
            remote: String(remoteName || "origin"),
            startBranch: String(startBranch || ""),
            fingerprint: String(armedFingerprint || ""),
            recoveryClass: "EVIDENCE_ONLY",
            steps: rows.map(function(row) {
                const item = row || {};

                return {
                    branch: String(item.branch || ""),
                    parent: String(item.parent || ""),
                    localHead: String(item.localHead || ""),
                    parentHead: String(item.parentHead || ""),
                    remoteHead: String(item.remoteHead || ""),
                    prNumber: String(item.prNumber || ""),
                    prUrl: String(item.prUrl || ""),
                    prState: String(item.prState || ""),
                    prBase: String(item.prBase || ""),
                    status: String(item.status || "")
                };
            })
        };
    }

    function failBeforeSnapshot(detail) {
        const message =
            "STACK SUBMIT BEFORE SNAPSHOT FAILED // "
            + String(detail || "SNAPSHOT UNAVAILABLE");

        submitBusy = false;
        lastError = message;
        submitState = "STACK SUBMIT // REFUSED";
        disarm("SNAPSHOT FAILED");
        clearPendingSubmission();
        submissionFinished(false, lastResult);
    }

    function startPendingSubmission() {
        if (!submitBusy
                || !Array.isArray(pendingSubmitArgs)
                || pendingSubmitArgs.length === 0)
            return false;

        submitState = "STACK SUBMIT // PUSHING + OPENING PRS";
        submitProcess.exec(pendingSubmitArgs);
        submitWatchdog.restart();
        return true;
    }

    function finalizeSubmission(afterSnapshot, snapshotWarning) {
        const warning = String(snapshotWarning || "");
        const detail = String(pendingSubmissionDetail || "");
        const success = pendingSubmissionSuccess;
        const snapshot =
            afterSnapshot
            ? journalSnapshot(afterSnapshot)
            : {
                snapshotVersion: 1,
                repository: String(repositoryPath || ""),
                capturedAt: new Date().toISOString(),
                captureFailed: true,
                recoveryClass: "EVIDENCE_ONLY",
                recoveryReason:
                    warning
                    || "STACK SUBMIT AFTER SNAPSHOT UNAVAILABLE"
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

        submitBusy = false;
        submitWatchdog.stop();

        if (!success) {
            lastError =
                detail
                || "STACK SUBMIT FAILED";
            if (warning)
                lastError += " // " + warning;
            submitState = "STACK SUBMIT // REFUSED";
            disarm("SUBMISSION FAILED");
        } else {
            submitState =
                warning
                ? "STACK SUBMIT // COMPLETE // SNAPSHOT WARNING"
                : "STACK SUBMIT // COMPLETE";
            lastError = warning;
            disarm("COMPLETE");
        }

        clearPendingSubmission();
        submissionFinished(success, lastResult);
    }

    function submitArmed() {
        if (submitBusy)
            return false;

        if (!armed) {
            lastError = "STACK SUBMIT REFUSED // NOT ARMED";
            return false;
        }

        if (fingerprintFor(plan) !== armedFingerprint) {
            disarm("PREVIEW CHANGED");
            lastError = "STACK SUBMIT REFUSED // PREVIEW IS STALE";
            return false;
        }

        const repo = String(repositoryPath || "").trim();
        const slug = String(repoSlug || "").trim();
        const remote = String(remoteName || "origin").trim() || "origin";

        if (!repo || !slug) {
            disarm("CONTEXT MISSING");
            lastError =
                "STACK SUBMIT REFUSED // REPOSITORY CONTEXT MISSING";
            return false;
        }

        const args = [
            "bash",
            "-lc",
            [
                'repo="$1"',
                'slug="$2"',
                'remote="$3"',
                'shift 3',
                'if ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then',
                '  printf "ERROR\\tNOT A GIT WORKTREE\\n"',
                '  exit 31',
                'fi',
                'if ! gh auth status >/dev/null 2>&1; then',
                '  printf "ERROR\\tGITHUB CLI NOT AUTHENTICATED\\n"',
                '  exit 32',
                'fi',
                'declare -a branches parents local_heads parent_heads remote_heads pr_numbers pr_urls pr_states pr_bases statuses',
                'while [ "$#" -ge 10 ]; do',
                '  branches+=("$1")',
                '  parents+=("$2")',
                '  local_heads+=("$3")',
                '  parent_heads+=("$4")',
                '  remote_heads+=("$5")',
                '  pr_numbers+=("$6")',
                '  pr_urls+=("$7")',
                '  pr_states+=("$8")',
                '  pr_bases+=("$9")',
                '  statuses+=("${10}")',
                '  shift 10',
                'done',
                'for ((i=0; i<${#branches[@]}; ++i)); do',
                '  branch="${branches[$i]}"',
                '  parent="${parents[$i]}"',
                '  expected_local="${local_heads[$i]}"',
                '  expected_parent="${parent_heads[$i]}"',
                '  expected_remote="${remote_heads[$i]}"',
                '  current_local="$(git -C "$repo" rev-parse "refs/heads/$branch" 2>/dev/null || true)"',
                '  current_parent="$(git -C "$repo" rev-parse "refs/heads/$parent" 2>/dev/null || true)"',
                '  current_remote="$(git -C "$repo" ls-remote --heads "$remote" "refs/heads/$branch" 2>/dev/null | awk "NR==1{print \\$1}")"',
                '  [ "$current_local" = "$expected_local" ] || { printf "ERROR\\tSTALE LOCAL HEAD // %s\\n" "$branch"; exit 33; }',
                '  [ "$current_parent" = "$expected_parent" ] || { printf "ERROR\\tSTALE PARENT HEAD // %s\\n" "$parent"; exit 34; }',
                '  [ "$current_remote" = "$expected_remote" ] || { printf "ERROR\\tREMOTE CHANGED // %s\\n" "$branch"; exit 35; }',
                'done',
                'declare -a leases specs',
                'for ((i=0; i<${#branches[@]}; ++i)); do',
                '  branch="${branches[$i]}"',
                '  expected_remote="${remote_heads[$i]}"',
                '  leases+=("--force-with-lease=refs/heads/$branch:$expected_remote")',
                '  specs+=("$branch:refs/heads/$branch")',
                'done',
                'git -C "$repo" push --atomic "${leases[@]}" "$remote" "${specs[@]}" >/dev/null 2>&1 || {',
                '  printf "ERROR\\tATOMIC PUSH REFUSED // REMOTE MAY HAVE CHANGED\\n"',
                '  exit 36',
                '}',
                'for ((i=0; i<${#branches[@]}; ++i)); do',
                '  branch="${branches[$i]}"',
                '  parent="${parents[$i]}"',
                '  number="${pr_numbers[$i]}"',
                '  url="${pr_urls[$i]}"',
                '  status="${statuses[$i]}"',
                '  if [ "$status" = "CREATE_PR" ]; then',
                '    title="$(git -C "$repo" log -1 --format=%s "$branch" 2>/dev/null)"',
                '    [ -n "$title" ] || title="$branch"',
                '    body="$(printf "Post-Apollo stacked pull request.\\n\\nStack base: %s\\nStack branch: %s" "$parent" "$branch")"',
                '    url="$(gh pr create --repo "$slug" --head "$branch" --base "$parent" --title "$title" --body "$body")" || { printf "ERROR\\tPR CREATE FAILED // %s\\n" "$branch"; exit 41; }',
                '    printf "PR\\t%s\\t%s\\t%s\\tCREATED\\n" "$branch" "$parent" "$url"',
                '  elif [ "$status" = "UPDATE_BASE" ]; then',
                '    gh pr edit "$number" --repo "$slug" --base "$parent" >/dev/null || { printf "ERROR\\tPR BASE UPDATE FAILED // %s\\n" "$branch"; exit 42; }',
                '    printf "PR\\t%s\\t%s\\t%s\\tBASE_UPDATED\\n" "$branch" "$parent" "$url"',
                '  elif [ "$status" = "REOPEN_EXISTING" ]; then',
                '    gh pr reopen "$number" --repo "$slug" >/dev/null || { printf "ERROR\\tPR REOPEN FAILED // %s\\n" "$branch"; exit 43; }',
                '    printf "PR\\t%s\\t%s\\t%s\\tREOPENED\\n" "$branch" "$parent" "$url"',
                '  elif [ "$status" = "REOPEN_UPDATE_BASE" ]; then',
                '    gh pr reopen "$number" --repo "$slug" >/dev/null || { printf "ERROR\\tPR REOPEN FAILED // %s\\n" "$branch"; exit 44; }',
                '    gh pr edit "$number" --repo "$slug" --base "$parent" >/dev/null || { printf "ERROR\\tPR BASE UPDATE FAILED // %s\\n" "$branch"; exit 45; }',
                '    printf "PR\\t%s\\t%s\\t%s\\tREOPENED_BASE_UPDATED\\n" "$branch" "$parent" "$url"',
                '  else',
                '    printf "PR\\t%s\\t%s\\t%s\\tREUSED\\n" "$branch" "$parent" "$url"',
                '  fi',
                'done',
                'printf "OK\\t%s PULL REQUESTS SUBMITTED\\n" "${#branches[@]}"'
            ].join("\n"),
            "git-stack-submit",
            repo,
            slug,
            remote
        ];

        for (let i = 0; i < armedPlan.length; ++i) {
            const row = armedPlan[i] || {};
            args.push(String(row.branch || ""));
            args.push(String(row.parent || ""));
            args.push(String(row.localHead || ""));
            args.push(String(row.parentHead || ""));
            args.push(String(row.remoteHead || ""));
            args.push(String(row.prNumber || ""));
            args.push(String(row.prUrl || ""));
            args.push(String(row.prState || ""));
            args.push(String(row.prBase || ""));
            args.push(String(row.status || ""));
        }

        if ((operationJournal && !snapshotService)
                || (snapshotService && !operationJournal)) {
            lastError =
                "STACK SUBMIT REFUSED // JOURNAL + SNAPSHOT SERVICES MUST BE PAIRED";
            return false;
        }

        clearPendingSubmission();
        pendingSubmitArgs = args;

        submitBusy = true;
        submitState =
            operationJournal && snapshotService
            ? "STACK SUBMIT // SNAPSHOT BEFORE"
            : "STACK SUBMIT // PUSHING + OPENING PRS";
        lastError = "";
        lastResult = [];

        submitStdoutSeen = false;
        submitStderrSeen = false;
        submitExitSeen = false;
        submitExitCode = -1;
        submitStdout = "";
        submitStderr = "";

        armTimer.stop();

        if (!operationJournal && !snapshotService)
            return startPendingSubmission();

        snapshotPhase = "BEFORE";
        pendingSnapshotRequest = snapshotService.capture(
            "STACK BEFORE // SUBMIT",
            journalContext()
        );

        if (!pendingSnapshotRequest) {
            failBeforeSnapshot("SNAPSHOT SERVICE BUSY OR UNAVAILABLE");
            return false;
        }

        return true;
    }

    function parseSubmit(text) {
        const rows = [];
        const lines = String(text || "").split("\n");

        for (let i = 0; i < lines.length; ++i) {
            const raw = String(lines[i] || "");

            if (!raw)
                continue;

            const parts = raw.split("\t");
            const kind = parts.length > 0 ? parts[0] : "";

            if (kind === "ERROR") {
                lastError =
                    parts.length > 1
                    ? parts.slice(1).join("\t")
                    : "STACK SUBMIT FAILED";
                continue;
            }

            if (kind === "PR") {
                rows.push({
                    branch: parts.length > 1 ? parts[1] : "",
                    parent: parts.length > 2 ? parts[2] : "",
                    url: parts.length > 3 ? parts[3] : "",
                    result: parts.length > 4 ? parts[4] : ""
                });
            }
        }

        lastResult = rows;
    }

    function maybeFinishSubmit() {
        if (!submitBusy
                || !submitStdoutSeen
                || !submitStderrSeen
                || !submitExitSeen)
            return;

        submitWatchdog.stop();
        parseSubmit(submitStdout);

        pendingSubmissionSuccess =
            submitExitCode === 0
            && !lastError;
        pendingSubmissionDetail =
            pendingSubmissionSuccess
            ? (
                lastResult.length > 0
                ? String(lastResult.length)
                    + " STACK PR RESULT ROWS"
                : "STACK SUBMIT COMPLETE"
              )
            : String(
                lastError
                || submitStderr
                || submitStdout
                || ("STACK SUBMIT EXIT " + submitExitCode)
              ).trim();

        if (!operationJournal || !snapshotService) {
            finalizeSubmission(null, "");
            return;
        }

        submitState = "STACK SUBMIT // SNAPSHOT AFTER";
        snapshotPhase = "AFTER";
        pendingSnapshotRequest = snapshotService.capture(
            "STACK AFTER // SUBMIT",
            journalContext()
        );

        if (!pendingSnapshotRequest) {
            finalizeSubmission(
                null,
                "AFTER SNAPSHOT COULD NOT START"
            );
        }
    }

    Connections {
        target: root.snapshotService
        enabled: root.snapshotService !== null
        ignoreUnknownSignals: true

        function onSnapshotReady(requestId, snapshot) {
            if (String(requestId || "")
                    !== String(root.pendingSnapshotRequest || ""))
                return;

            root.pendingSnapshotRequest = "";

            if (root.snapshotPhase === "BEFORE") {
                root.snapshotPhase = "";
                const beforeSnapshot = root.journalSnapshot(snapshot);

                root.pendingJournalId =
                    root.operationJournal
                    ? root.operationJournal.beginOperation(
                        "STACK/SUBMIT",
                        beforeSnapshot,
                        root.journalContext()
                    )
                    : "";

                if (root.operationJournal
                        && !root.pendingJournalId) {
                    root.failBeforeSnapshot(
                        "JOURNAL RECORD COULD NOT START"
                    );
                    return;
                }

                root.startPendingSubmission();
                return;
            }

            if (root.snapshotPhase === "AFTER") {
                root.snapshotPhase = "";
                root.finalizeSubmission(snapshot, "");
            }
        }

        function onSnapshotFailed(requestId, detail) {
            if (String(requestId || "")
                    !== String(root.pendingSnapshotRequest || ""))
                return;

            root.pendingSnapshotRequest = "";

            if (root.snapshotPhase === "BEFORE") {
                root.snapshotPhase = "";
                root.failBeforeSnapshot(detail);
                return;
            }

            if (root.snapshotPhase === "AFTER") {
                root.snapshotPhase = "";
                root.finalizeSubmission(
                    null,
                    "AFTER SNAPSHOT FAILED // "
                        + String(detail || "UNKNOWN ERROR")
                );
            }
        }
    }

    Process {
        id: previewProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.previewStdout = this.text;
                root.previewStdoutSeen = true;
                root.maybeFinishPreview();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.previewStderr = this.text;
                root.previewStderrSeen = true;
                root.maybeFinishPreview();
            }
        }

        onExited: function(code, exitStatus) {
            root.previewExitCode = Number(code);
            root.previewExitSeen = true;
            root.maybeFinishPreview();
        }
    }

    Process {
        id: submitProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.submitStdout = this.text;
                root.submitStdoutSeen = true;
                root.maybeFinishSubmit();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.submitStderr = this.text;
                root.submitStderrSeen = true;
                root.maybeFinishSubmit();
            }
        }

        onExited: function(code, exitStatus) {
            root.submitExitCode = Number(code);
            root.submitExitSeen = true;
            root.maybeFinishSubmit();
        }
    }

    Timer {
        id: armTimer
        interval: 15000
        repeat: false

        onTriggered: {
            if (root.armed)
                root.disarm("ARM EXPIRED");
        }
    }

    Timer {
        id: previewWatchdog
        interval: 30000
        repeat: false

        onTriggered: {
            if (!root.previewBusy)
                return;

            root.previewBusy = false;
            root.lastError = "STACK SUBMIT PREVIEW // TIMEOUT";
            root.previewState = root.lastError;
            root.plan = [];
            root.previewReady(root.plan);
        }
    }

    Timer {
        id: submitWatchdog
        interval: 120000
        repeat: false

        onTriggered: {
            if (!root.submitBusy)
                return;

            const detail =
                "STACK SUBMIT TIMEOUT // VERIFY REMOTE + PR STATE";

            if (root.pendingJournalId && root.operationJournal) {
                root.operationJournal.failOperation(
                    root.pendingJournalId,
                    {
                        snapshotVersion: 1,
                        repository: String(root.repositoryPath || ""),
                        capturedAt: new Date().toISOString(),
                        captureFailed: true,
                        recoveryClass: "EVIDENCE_ONLY",
                        recoveryReason:
                            "STACK SUBMIT TIMEOUT // REMOTE + PR STATE UNCERTAIN"
                    },
                    detail
                );
            }

            root.submitBusy = false;
            root.lastError = detail;
            root.submitState = "STACK SUBMIT // UNCERTAIN";
            root.disarm("TIMEOUT");
            root.clearPendingSubmission();
            root.submissionFinished(false, root.lastResult);
        }
    }
}
