import QtQuick
import Quickshell
import Quickshell.Io

// Transactional executor for a previously inspected GitStackPlanner plan.
//
// Safety model:
//   PREVIEW -> ARM -> EXECUTE
// Rewrites are computed in temporary detached worktrees first. Branch refs are
// updated together only after every rebase succeeds.
Scope {
    id: root

    required property var stackPlanner
    required property var branchWorkspaceService

    property string repositoryPath: ""
    property var operationJournal: null
    property var snapshotService: null

    property bool armed: false
    property string armedFingerprint: ""
    property string armedStartBranch: ""
    property var armedPlan: []
    property string armStatus: "RESTACK // NOT ARMED"

    property bool running: false
    property string stateText: "RESTACK // READY"
    property string lastError: ""
    property var lastResult: []

    property bool stdoutSeen: false
    property bool stderrSeen: false
    property bool exitSeen: false
    property int exitCode: -1
    property string stdoutText: ""
    property string stderrText: ""

    property string pendingJournalId: ""
    property string pendingSnapshotRequest: ""
    property string snapshotPhase: ""
    property var pendingExecutorArgs: []
    property bool pendingExecutionSuccess: false
    property string pendingExecutionDetail: ""

    signal executionFinished(bool success, var result)

    function fingerprintFor(repo, start, plan) {
        const rows = Array.isArray(plan) ? plan : [];

        return JSON.stringify({
            repository: String(repo || ""),
            startBranch: String(start || ""),
            steps: rows.map(function(step) {
                const row = step || {};
                return {
                    branch: String(row.branch || ""),
                    parent: String(row.parent || ""),
                    head: String(row.head || ""),
                    parentHead: String(row.parentHead || ""),
                    mergeBase: String(row.mergeBase || ""),
                    uniqueCommits: Number(row.uniqueCommits || 0),
                    mergeCommits: Number(row.mergeCommits || 0),
                    status: String(row.status || "")
                };
            })
        });
    }

    function currentPlannerFingerprint() {
        if (!stackPlanner)
            return "";

        return fingerprintFor(
            repositoryPath,
            stackPlanner.startBranch,
            stackPlanner.plan
        );
    }

    function requiredSteps(plan) {
        const rows = Array.isArray(plan) ? plan : [];

        return rows.filter(function(step) {
            return String((step || {}).status || "")
                === "RESTACK_REQUIRED";
        });
    }

    function occupiedRequiredBranch(plan) {
        if (!branchWorkspaceService)
            return "";

        const rows = requiredSteps(plan);

        for (let i = 0; i < rows.length; ++i) {
            const branch = String((rows[i] || {}).branch || "");

            if (branch
                    && branchWorkspaceService.branchIsOccupied(branch))
                return branch;
        }

        return "";
    }

    function disarm(reason) {
        armed = false;
        armedFingerprint = "";
        armedStartBranch = "";
        armedPlan = [];
        armTimer.stop();

        armStatus = reason
            ? "RESTACK // DISARMED // " + String(reason)
            : "RESTACK // NOT ARMED";
    }

    function armFromPlanner() {
        if (running || !stackPlanner) {
            lastError = running
                ? "RESTACK ARM REFUSED // EXECUTION RUNNING"
                : "RESTACK ARM REFUSED // NO PLANNER";
            return false;
        }

        if (stackPlanner.busy
                || !stackPlanner.executable
                || stackPlanner.requiredCount <= 0) {
            lastError =
                "RESTACK ARM REFUSED // VALID PREVIEW REQUIRED";
            return false;
        }

        const repo = String(repositoryPath || "").trim();
        const start = String(stackPlanner.startBranch || "").trim();
        const plan = Array.isArray(stackPlanner.plan)
            ? stackPlanner.plan.slice()
            : [];

        if (!repo || !start || plan.length === 0) {
            lastError =
                "RESTACK ARM REFUSED // PREVIEW CONTEXT INCOMPLETE";
            return false;
        }

        const occupied = occupiedRequiredBranch(plan);

        if (occupied) {
            lastError =
                "RESTACK ARM REFUSED // "
                + occupied
                + " IS CHECKED OUT IN A WORKTREE";
            return false;
        }

        armedFingerprint = fingerprintFor(repo, start, plan);
        armedStartBranch = start;
        armedPlan = plan;
        armed = true;
        lastError = "";
        armStatus =
            "RESTACK // ARMED // "
            + String(stackPlanner.requiredCount)
            + " MOVE"
            + (stackPlanner.requiredCount === 1 ? "" : "S");
        armTimer.restart();
        return true;
    }

    function clearPendingExecution() {
        pendingJournalId = "";
        pendingSnapshotRequest = "";
        snapshotPhase = "";
        pendingExecutorArgs = [];
        pendingExecutionSuccess = false;
        pendingExecutionDetail = "";
    }

    function journalContext() {
        const rows = requiredSteps(armedPlan);

        return {
            source: "GitStackExecutor",
            startBranch: String(armedStartBranch || ""),
            fingerprint: String(armedFingerprint || ""),
            steps: rows.map(function(step) {
                const row = step || {};

                return {
                    branch: String(row.branch || ""),
                    parent: String(row.parent || ""),
                    head: String(row.head || ""),
                    parentHead: String(row.parentHead || ""),
                    mergeBase: String(row.mergeBase || ""),
                    status: String(row.status || "")
                };
            })
        };
    }

    function failBeforeSnapshot(detail) {
        const message =
            "RESTACK BEFORE SNAPSHOT FAILED // "
            + String(detail || "SNAPSHOT UNAVAILABLE");

        running = false;
        lastError = message;
        stateText = "RESTACK // REFUSED";
        disarm("SNAPSHOT FAILED");
        clearPendingExecution();
        executionFinished(false, lastResult);
    }

    function startPendingExecution() {
        if (!running || !Array.isArray(pendingExecutorArgs)
                || pendingExecutorArgs.length === 0)
            return false;

        stateText = "RESTACK // EXECUTING";
        executorWatchdog.restart();
        executorProcess.exec(pendingExecutorArgs);
        return true;
    }

    function finalizeExecution(afterSnapshot, snapshotWarning) {
        const warning = String(snapshotWarning || "");
        const detail = String(pendingExecutionDetail || "");
        const success = pendingExecutionSuccess;
        const snapshot =
            afterSnapshot
            || {
                snapshotVersion: 1,
                repository: String(repositoryPath || ""),
                capturedAt: new Date().toISOString(),
                captureFailed: true,
                recoveryClass: "EVIDENCE_ONLY",
                recoveryReason:
                    warning
                    || "RESTACK AFTER SNAPSHOT UNAVAILABLE"
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

        running = false;
        executorWatchdog.stop();

        if (!success) {
            lastError =
                detail
                || "RESTACK FAILED";
            if (warning)
                lastError += " // " + warning;
            stateText = "RESTACK // REFUSED";
            disarm("EXECUTION FAILED");
        } else {
            stateText =
                warning
                ? "RESTACK // COMPLETE // SNAPSHOT WARNING"
                : "RESTACK // COMPLETE";
            lastError = warning;
            disarm("COMPLETE");

            if (branchWorkspaceService)
                branchWorkspaceService.refresh();

            if (stackPlanner)
                stackPlanner.clear();
        }

        clearPendingExecution();
        executionFinished(success, lastResult);
    }

    function executeArmed() {
        if (running)
            return false;

        if (!armed) {
            lastError = "RESTACK REFUSED // NOT ARMED";
            return false;
        }

        const repo = String(repositoryPath || "").trim();

        if (!repo) {
            disarm("NO REPOSITORY");
            lastError = "RESTACK REFUSED // NO REPOSITORY";
            return false;
        }

        const liveFingerprint = currentPlannerFingerprint();

        if (!liveFingerprint
                || liveFingerprint !== armedFingerprint) {
            disarm("PREVIEW CHANGED");
            lastError =
                "RESTACK REFUSED // PREVIEW IS STALE";
            return false;
        }

        const occupied = occupiedRequiredBranch(armedPlan);

        if (occupied) {
            disarm("WORKTREE OCCUPANCY CHANGED");
            lastError =
                "RESTACK REFUSED // "
                + occupied
                + " IS CHECKED OUT IN A WORKTREE";
            return false;
        }

        const steps = requiredSteps(armedPlan);

        if (steps.length === 0) {
            disarm("NOTHING TO RESTACK");
            lastError =
                "RESTACK REFUSED // NOTHING TO RESTACK";
            return false;
        }

        const args = [
            "bash",
            "-lc",
            [
                'repo="$1"',
                'shift',
                'if ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then',
                '  printf "ERROR\\tNOT A GIT WORKTREE\\n"',
                '  exit 21',
                'fi',
                'declare -A rewritten',
                'declare -a update_branch',
                'declare -a update_old',
                'declare -a update_new',
                'tmp_base=""',
                'cleanup_tmp() {',
                '  if [ -n "$tmp_base" ]; then',
                '    tmp="$tmp_base/worktree"',
                '    git -C "$repo" worktree remove --force "$tmp" >/dev/null 2>&1 || true',
                '    rm -rf "$tmp_base" >/dev/null 2>&1 || true',
                '    tmp_base=""',
                '  fi',
                '}',
                'trap cleanup_tmp EXIT INT TERM',
                'while [ "$#" -ge 7 ]; do',
                '  child="$1"',
                '  parent="$2"',
                '  expected_child="$3"',
                '  expected_parent="$4"',
                '  base="$5"',
                '  unique_count="$6"',
                '  status="$7"',
                '  shift 7',
                '  [ "$status" = "RESTACK_REQUIRED" ] || continue',
                '  current_child="$(git -C "$repo" rev-parse "refs/heads/$child" 2>/dev/null || true)"',
                '  current_parent="$(git -C "$repo" rev-parse "refs/heads/$parent" 2>/dev/null || true)"',
                '  if [ -z "$current_child" ] || [ "$current_child" != "$expected_child" ]; then',
                '    printf "ERROR\\tSTALE CHILD // %s\\n" "$child"',
                '    exit 31',
                '  fi',
                '  if [ -z "$current_parent" ] || [ "$current_parent" != "$expected_parent" ]; then',
                '    printf "ERROR\\tSTALE PARENT // %s\\n" "$parent"',
                '    exit 32',
                '  fi',
                '  if git -C "$repo" worktree list --porcelain 2>/dev/null | grep -Fqx "branch refs/heads/$child"; then',
                '    printf "ERROR\\tBRANCH CHECKED OUT // %s\\n" "$child"',
                '    exit 33',
                '  fi',
                '  target_parent="$current_parent"',
                '  if [ -n "${rewritten[$parent]:-}" ]; then',
                '    target_parent="${rewritten[$parent]}"',
                '  fi',
                '  if [ -z "$base" ]; then',
                '    printf "ERROR\\tNO MERGE BASE // %s\\n" "$child"',
                '    exit 34',
                '  fi',
                '  if [ "$unique_count" -eq 0 ]; then',
                '    new_head="$target_parent"',
                '  else',
                '    tmp_base="$(mktemp -d "${TMPDIR:-/tmp}/pa-restack.XXXXXX")" || exit 35',
                '    tmp="$tmp_base/worktree"',
                '    if ! git -C "$repo" worktree add --detach "$tmp" "$expected_child" >/dev/null 2>&1; then',
                '      printf "ERROR\\tTEMP WORKTREE FAILED // %s\\n" "$child"',
                '      cleanup_tmp',
                '      exit 36',
                '    fi',
                '    if ! GIT_EDITOR=: GIT_SEQUENCE_EDITOR=: git -C "$tmp" rebase --onto "$target_parent" "$base" >/dev/null 2>&1; then',
                '      git -C "$tmp" rebase --abort >/dev/null 2>&1 || true',
                '      printf "ERROR\\tRESTACK CONFLICT // %s -> %s\\n" "$child" "$parent"',
                '      cleanup_tmp',
                '      exit 37',
                '    fi',
                '    new_head="$(git -C "$tmp" rev-parse HEAD 2>/dev/null || true)"',
                '    cleanup_tmp',
                '    if [ -z "$new_head" ]; then',
                '      printf "ERROR\\tNO REWRITTEN HEAD // %s\\n" "$child"',
                '      exit 38',
                '    fi',
                '  fi',
                '  rewritten["$child"]="$new_head"',
                '  update_branch+=("$child")',
                '  update_old+=("$expected_child")',
                '  update_new+=("$new_head")',
                '  printf "PREPARED\\t%s\\t%s\\t%s\\t%s\\n" "$child" "$expected_child" "$new_head" "$target_parent"',
                'done',
                'if [ "${#update_branch[@]}" -eq 0 ]; then',
                '  printf "ERROR\\tNO REF UPDATES PREPARED\\n"',
                '  exit 39',
                'fi',
                '{',
                '  printf "start\\n"',
                '  for ((i=0; i<${#update_branch[@]}; ++i)); do',
                '    printf "update refs/heads/%s %s %s\\n" "${update_branch[$i]}" "${update_new[$i]}" "${update_old[$i]}"',
                '  done',
                '  printf "prepare\\n"',
                '  printf "commit\\n"',
                '} | git -C "$repo" update-ref --stdin >/dev/null 2>&1 || {',
                '  printf "ERROR\\tATOMIC REF TRANSACTION FAILED\\n"',
                '  exit 40',
                '}',
                'for ((i=0; i<${#update_branch[@]}; ++i)); do',
                '  printf "UPDATED\\t%s\\t%s\\t%s\\n" "${update_branch[$i]}" "${update_old[$i]}" "${update_new[$i]}"',
                'done',
                'printf "OK\\t%s BRANCHES RESTACKED\\n" "${#update_branch[@]}"'
            ].join("\n"),
            "git-stack-restack",
            repo
        ];

        for (let i = 0; i < steps.length; ++i) {
            const step = steps[i] || {};

            args.push(String(step.branch || ""));
            args.push(String(step.parent || ""));
            args.push(String(step.head || ""));
            args.push(String(step.parentHead || ""));
            args.push(String(step.mergeBase || ""));
            args.push(String(Number(step.uniqueCommits || 0)));
            args.push(String(step.status || ""));
        }

        if ((operationJournal && !snapshotService)
                || (snapshotService && !operationJournal)) {
            lastError =
                "RESTACK REFUSED // JOURNAL + SNAPSHOT SERVICES MUST BE PAIRED";
            return false;
        }

        clearPendingExecution();
        pendingExecutorArgs = args;

        running = true;
        stateText =
            operationJournal && snapshotService
            ? "RESTACK // SNAPSHOT BEFORE"
            : "RESTACK // EXECUTING";
        lastError = "";
        lastResult = [];

        stdoutSeen = false;
        stderrSeen = false;
        exitSeen = false;
        exitCode = -1;
        stdoutText = "";
        stderrText = "";

        armTimer.stop();

        if (!operationJournal && !snapshotService)
            return startPendingExecution();

        snapshotPhase = "BEFORE";
        pendingSnapshotRequest = snapshotService.capture(
            "STACK BEFORE // RESTACK",
            journalContext()
        );

        if (!pendingSnapshotRequest) {
            failBeforeSnapshot("SNAPSHOT SERVICE BUSY OR UNAVAILABLE");
            return false;
        }

        return true;
    }

    function parseResult(text) {
        const rows = [];
        const lines = String(text || "").split("\n");

        for (let i = 0; i < lines.length; ++i) {
            const raw = String(lines[i] || "");

            if (!raw)
                continue;

            const parts = raw.split("\t");
            const kind = parts.length > 0 ? parts[0] : "";

            if (kind === "ERROR") {
                lastError = parts.length > 1
                    ? parts.slice(1).join("\t")
                    : "RESTACK FAILED";
                continue;
            }

            if (kind === "PREPARED") {
                rows.push({
                    phase: "PREPARED",
                    branch: parts.length > 1 ? parts[1] : "",
                    oldHead: parts.length > 2 ? parts[2] : "",
                    newHead: parts.length > 3 ? parts[3] : "",
                    parentHead: parts.length > 4 ? parts[4] : ""
                });
                continue;
            }

            if (kind === "UPDATED") {
                rows.push({
                    phase: "UPDATED",
                    branch: parts.length > 1 ? parts[1] : "",
                    oldHead: parts.length > 2 ? parts[2] : "",
                    newHead: parts.length > 3 ? parts[3] : ""
                });
            }
        }

        lastResult = rows;
    }

    function maybeFinish() {
        if (!running || !stdoutSeen || !stderrSeen || !exitSeen)
            return;

        executorWatchdog.stop();
        parseResult(stdoutText);

        pendingExecutionSuccess =
            exitCode === 0
            && !lastError;
        pendingExecutionDetail =
            pendingExecutionSuccess
            ? (
                lastResult.length > 0
                ? String(lastResult.length) + " RESTACK RESULT ROWS"
                : "RESTACK COMPLETE"
              )
            : String(
                lastError
                || stderrText
                || stdoutText
                || ("RESTACK EXIT " + exitCode)
              ).trim();

        if (!operationJournal || !snapshotService) {
            finalizeExecution(null, "");
            return;
        }

        stateText = "RESTACK // SNAPSHOT AFTER";
        snapshotPhase = "AFTER";
        pendingSnapshotRequest = snapshotService.capture(
            "STACK AFTER // RESTACK",
            journalContext()
        );

        if (!pendingSnapshotRequest) {
            finalizeExecution(
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

                root.pendingJournalId =
                    root.operationJournal
                    ? root.operationJournal.beginOperation(
                        "STACK/RESTACK",
                        snapshot,
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

                root.startPendingExecution();
                return;
            }

            if (root.snapshotPhase === "AFTER") {
                root.snapshotPhase = "";
                root.finalizeExecution(snapshot, "");
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
                root.finalizeExecution(
                    null,
                    "AFTER SNAPSHOT FAILED // "
                        + String(detail || "UNKNOWN ERROR")
                );
            }
        }
    }

    Process {
        id: executorProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.stdoutText = this.text;
                root.stdoutSeen = true;
                root.maybeFinish();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.stderrText = this.text;
                root.stderrSeen = true;
                root.maybeFinish();
            }
        }

        onExited: function(code, exitStatus) {
            root.exitCode = Number(code);
            root.exitSeen = true;
            root.maybeFinish();
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
        id: executorWatchdog
        interval: 120000
        repeat: false

        onTriggered: {
            if (!root.running)
                return;

            const detail =
                "RESTACK EXECUTION TIMEOUT // VERIFY REPOSITORY STATE";

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
                            "RESTACK TIMEOUT // REPOSITORY STATE UNCERTAIN"
                    },
                    detail
                );
            }

            root.running = false;
            root.lastError = detail;
            root.stateText = "RESTACK // UNCERTAIN";
            root.disarm("TIMEOUT");
            root.clearPendingExecution();
            root.executionFinished(false, root.lastResult);
        }
    }
}
