import QtQuick
import Quickshell
import Quickshell.Io

// Guarded contiguous-commit fold engine.
// Rehearses the exact rewrite in a temporary detached worktree before moving
// the live branch with an expected-old update-ref.
Scope {
    id: root

    property string repositoryPath: ""
    property var operationJournal: null
    property var snapshotService: null

    property bool previewBusy: false
    property bool executionBusy: false
    property string state: "READY"
    property string lastError: ""

    property string branchName: ""
    property string headSha: ""
    property string baseSha: ""
    property string startSha: ""
    property string endSha: ""
    property var commits: []
    property string foldMessage: ""

    property bool armed: false
    property string armedPlanJson: ""

    property string pendingJournalId: ""
    property string pendingSnapshotRequest: ""
    property string snapshotPhase: ""
    property bool pendingExecutionSuccess: false
    property string pendingExecutionDetail: ""
    property string pendingNewHead: ""

    property bool previewExitSeen: false
    property bool previewStdoutSeen: false
    property bool previewStderrSeen: false
    property int previewExitCode: -1
    property string previewStdout: ""
    property string previewStderr: ""

    property bool executeExitSeen: false
    property bool executeStdoutSeen: false
    property bool executeStderrSeen: false
    property int executeExitCode: -1
    property string executeStdout: ""
    property string executeStderr: ""

    signal previewReady(var commits)
    signal executionFinished(bool success, string detail, string newHead)

    function cloneValue(value) {
        try {
            return JSON.parse(JSON.stringify(value || []));
        } catch (error) {
            return [];
        }
    }

    function clear() {
        if (previewBusy || executionBusy)
            return false;

        branchName = "";
        headSha = "";
        baseSha = "";
        startSha = "";
        endSha = "";
        commits = [];
        foldMessage = "";
        armed = false;
        armedPlanJson = "";
        state = "READY";
        lastError = "";
        return true;
    }

    function disarm(reason) {
        armed = false;
        armedPlanJson = "";
        if (reason)
            state = "FOLD // " + String(reason);
    }

    function setMessage(message) {
        foldMessage = String(message || "");
        disarm("PLAN CHANGED");
    }

    function preview(oldest, newest) {
        if (previewBusy || executionBusy)
            return false;

        const repo = String(repositoryPath || "").trim();
        const start = String(oldest || "").trim();
        const end = String(newest || "").trim();

        if (!repo || !start || !end) {
            state = "FOLD // REFUSED";
            lastError =
                !repo
                ? "NO REPOSITORY"
                : "OLDEST + NEWEST COMMITS REQUIRED";
            return false;
        }

        previewBusy = true;
        armed = false;
        armedPlanJson = "";
        state = "FOLD // READING RANGE";
        lastError = "";

        previewExitSeen = false;
        previewStdoutSeen = false;
        previewStderrSeen = false;
        previewExitCode = -1;
        previewStdout = "";
        previewStderr = "";

        previewProcess.exec([
            "python3",
            "-c",
            previewScript(),
            repo,
            start,
            end
        ]);
        return true;
    }

    function previewScript() {
        return [
            'import json, subprocess, sys',
            'repo, start_input, end_input = sys.argv[1:4]',
            'def run(*args): return subprocess.run(["git", "-C", repo] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE)',
            'def text(proc): return proc.stdout.decode("utf-8", "surrogateescape").strip()',
            'def refuse(msg): print("REFUSED\\t" + msg); sys.exit(1)',
            'if run("rev-parse", "--is-inside-work-tree").returncode: refuse("NOT A GIT WORKTREE")',
            'if run("status", "--porcelain=v1", "--untracked-files=all").stdout.strip(): refuse("WORKTREE DIRTY // COMMIT OR STASH FIRST")',
            'branch = text(run("branch", "--show-current"))',
            'if not branch: refuse("DETACHED HEAD")',
            'head = text(run("rev-parse", "HEAD"))',
            'start = text(run("rev-parse", start_input + "^{commit}"))',
            'end = text(run("rev-parse", end_input + "^{commit}"))',
            'if not head or not start or not end: refuse("FOLD COMMITS CANNOT BE RESOLVED")',
            'if start == end: refuse("FOLD REQUIRES AT LEAST TWO COMMITS")',
            'if run("merge-base", "--is-ancestor", start, end).returncode: refuse("OLDEST COMMIT IS NOT AN ANCESTOR OF NEWEST")',
            'if run("merge-base", "--is-ancestor", end, head).returncode: refuse("NEWEST COMMIT IS NOT ON CURRENT HEAD HISTORY")',
            'parents = text(run("rev-list", "--parents", "-n", "1", start)).split()',
            'if len(parents) != 2: refuse("FOLD OLDEST COMMIT MUST HAVE EXACTLY ONE PARENT")',
            'base = parents[1]',
            'if run("rev-list", "--merges", base + ".." + head).stdout.strip(): refuse("REWRITE RANGE CONTAINS MERGE COMMITS")',
            'selected = text(run("rev-list", "--first-parent", "--reverse", base + ".." + end)).splitlines()',
            'if len(selected) < 2 or selected[0] != start or selected[-1] != end: refuse("FOLD RANGE IS NOT CONTIGUOUS ON CURRENT FIRST-PARENT CHAIN")',
            'rows = [{"sha": sha, "subject": text(run("show", "-s", "--format=%s", sha))} for sha in selected]',
            'print("JSON\\t" + json.dumps({"base": base, "branch": branch, "head": head, "start": start, "end": end, "commits": rows}, separators=(",", ":")))'
        ].join("\n");
    }

    function maybeFinishPreview() {
        if (!previewBusy
                || !previewExitSeen
                || !previewStdoutSeen
                || !previewStderrSeen)
            return;

        previewBusy = false;
        const out = String(previewStdout || "").trim();
        const err = String(previewStderr || "").trim();
        const lines = out.split("\n");
        let payload = null;
        let refused = "";

        for (let i = 0; i < lines.length; ++i) {
            const line = String(lines[i] || "");
            if (line.indexOf("JSON\t") === 0) {
                try {
                    payload = JSON.parse(line.slice(5));
                } catch (error) {
                    payload = null;
                }
            } else if (line.indexOf("REFUSED\t") === 0) {
                refused = line.slice(8);
            }
        }

        if (previewExitCode !== 0 || !payload) {
            state = "FOLD // REFUSED";
            lastError =
                refused
                || err
                || out
                || ("FOLD PREVIEW EXIT " + previewExitCode);
            commits = [];
            return;
        }

        baseSha = String(payload.base || "");
        branchName = String(payload.branch || "");
        headSha = String(payload.head || "");
        startSha = String(payload.start || "");
        endSha = String(payload.end || "");
        commits = cloneValue(payload.commits || []);
        foldMessage =
            commits.length > 0
            ? String((commits[0] || {}).subject || "")
            : "";
        state =
            "FOLD // PLAN READY // "
            + String(commits.length)
            + " COMMITS";
        lastError = "";
        previewReady(cloneValue(commits));
    }

    function planObject() {
        return {
            branch: branchName,
            head: headSha,
            base: baseSha,
            start: startSha,
            end: endSha,
            message: String(foldMessage || "").trim(),
            commits: cloneValue(commits)
        };
    }

    function arm() {
        if (previewBusy || executionBusy)
            return false;

        const plan = planObject();

        if (!plan.branch
                || !plan.head
                || !plan.base
                || !plan.start
                || !plan.end
                || plan.commits.length < 2
                || !plan.message) {
            state = "FOLD // REFUSED";
            lastError = "FOLD PLAN IS INCOMPLETE";
            return false;
        }

        armedPlanJson = JSON.stringify(plan);
        armed = true;
        state = "FOLD // ARMED";
        lastError = "";
        return true;
    }

    function planStillArmed() {
        return armed
            && armedPlanJson === JSON.stringify(planObject());
    }

    function journalContext() {
        const plan = planObject();
        return {
            source: "GitHistoryFoldService",
            operation: "FOLD_COMMITS",
            branch: plan.branch,
            head: plan.head,
            baseSha: plan.base,
            startSha: plan.start,
            endSha: plan.end,
            commitCount: plan.commits.length,
            message: plan.message,
            commits: cloneValue(plan.commits)
        };
    }

    function executeArmed() {
        if (previewBusy || executionBusy || !planStillArmed())
            return false;

        if (!operationJournal || !snapshotService) {
            state = "FOLD // REFUSED";
            lastError = "FOLD REQUIRES JOURNAL + SNAPSHOT SERVICES";
            return false;
        }

        executionBusy = true;
        state = "FOLD // SNAPSHOT BEFORE";
        lastError = "";
        pendingExecutionSuccess = false;
        pendingExecutionDetail = "";
        pendingNewHead = "";

        executeExitSeen = false;
        executeStdoutSeen = false;
        executeStderrSeen = false;
        executeExitCode = -1;
        executeStdout = "";
        executeStderr = "";

        snapshotPhase = "BEFORE";
        pendingSnapshotRequest = snapshotService.capture(
            "HISTORY BEFORE // FOLD COMMITS",
            journalContext()
        );

        if (!pendingSnapshotRequest) {
            failBeforeSnapshot("SNAPSHOT SERVICE BUSY OR UNAVAILABLE");
            return false;
        }
        return true;
    }

    function failBeforeSnapshot(detail) {
        executionBusy = false;
        pendingSnapshotRequest = "";
        snapshotPhase = "";
        state = "FOLD // REFUSED";
        lastError =
            "FOLD BEFORE SNAPSHOT FAILED // "
            + String(detail || "UNKNOWN ERROR");
        executionFinished(false, lastError, "");
    }

    function executionScript() {
        return [
            'import base64, json, os, shutil, stat, subprocess, sys, tempfile',
            'repo = sys.argv[1]',
            'plan = json.loads(sys.argv[2])',
            'branch, expected_head, base = plan["branch"], plan["head"], plan["base"]',
            'start_sha, end_sha, message = plan["start"], plan["end"], plan["message"]',
            'def run(repo_path, *args, env=None): return subprocess.run(["git", "-C", repo_path] + list(args), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)',
            'def text(proc): return proc.stdout.decode("utf-8", "surrogateescape").strip()',
            'def refuse(msg, code=1): print("REFUSED\\t" + msg); sys.exit(code)',
            'if run(repo, "rev-parse", "--is-inside-work-tree").returncode: refuse("NOT A GIT WORKTREE")',
            'if text(run(repo, "branch", "--show-current")) != branch: refuse("CURRENT BRANCH CHANGED SINCE ARM")',
            'if text(run(repo, "rev-parse", "HEAD")) != expected_head: refuse("HEAD CHANGED SINCE ARM")',
            'if run(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout.strip(): refuse("WORKTREE DIRTY SINCE ARM")',
            'if run(repo, "rev-list", "--merges", base + ".." + expected_head).stdout.strip(): refuse("REWRITE RANGE NOW CONTAINS MERGE COMMITS")',
            'ordered = text(run(repo, "rev-list", "--first-parent", "--reverse", base + ".." + expected_head)).splitlines()',
            'if start_sha not in ordered or end_sha not in ordered: refuse("FOLD COMMITS LEFT CURRENT FIRST-PARENT CHAIN")',
            'start_index, end_index = ordered.index(start_sha), ordered.index(end_sha)',
            'if start_index >= end_index: refuse("FOLD RANGE ORDER IS INVALID")',
            'selected = ordered[start_index:end_index + 1]',
            'subjects = {sha: text(run(repo, "show", "-s", "--format=%s", sha)).replace("\\n", " ").replace("\\r", " ") for sha in ordered}',
            'payload = base64.b64encode(message.encode("utf-8")).decode("ascii")',
            'todo = []',
            'for index, sha in enumerate(ordered):',
            '    action = "fixup" if start_index < index <= end_index else "pick"',
            '    todo.append("{} {} {}".format(action, sha, subjects[sha]))',
            '    if index == end_index: todo.append("exec sh -c \'printf %s {} | base64 -d | git commit --amend --no-verify -F -\'".format(payload))',
            'tmp = tempfile.mkdtemp(prefix="pa-fold-")',
            'wt, todo_path, editor = os.path.join(tmp, "worktree"), os.path.join(tmp, "todo"), os.path.join(tmp, "sequence-editor")',
            'try:',
            '    add = run(repo, "worktree", "add", "--detach", wt, expected_head)',
            '    if add.returncode: refuse("FOLD REHEARSAL WORKTREE CREATE FAILED // " + add.stderr.decode("utf-8", "replace").strip())',
            '    open(todo_path, "w", encoding="utf-8").write("\\n".join(todo) + "\\n")',
            '    open(editor, "w", encoding="utf-8").write("#!/bin/sh\\ncp \\"$PA_FOLD_TODO\\" \\"$1\\"\\n")',
            '    os.chmod(editor, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)',
            '    env = dict(os.environ); env["GIT_SEQUENCE_EDITOR"] = editor; env["GIT_EDITOR"] = ":"; env["PA_FOLD_TODO"] = todo_path',
            '    result = run(wt, "-c", "commit.gpgSign=false", "rebase", "-i", "--empty=keep", "--reapply-cherry-picks", base, env=env)',
            '    if result.returncode:',
            '        run(wt, "rebase", "--abort")',
            '        detail = result.stderr.decode("utf-8", "replace").strip() or result.stdout.decode("utf-8", "replace").strip()',
            '        refuse("FOLD REHEARSAL CONFLICT OR FAILURE // " + detail)',
            '    new_head = text(run(wt, "rev-parse", "HEAD"))',
            '    if not new_head: refuse("FOLD REHEARSAL PRODUCED NO HEAD")',
            'finally:',
            '    run(repo, "worktree", "remove", "--force", wt)',
            '    shutil.rmtree(tmp, ignore_errors=True)',
            'if text(run(repo, "branch", "--show-current")) != branch: refuse("CURRENT BRANCH CHANGED AFTER REHEARSAL")',
            'if text(run(repo, "rev-parse", "HEAD")) != expected_head: refuse("HEAD CHANGED AFTER REHEARSAL")',
            'if run(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout.strip(): refuse("WORKTREE CHANGED AFTER REHEARSAL")',
            'ref = "refs/heads/" + branch',
            'run(repo, "update-ref", "ORIG_HEAD", expected_head)',
            'move = run(repo, "update-ref", ref, new_head, expected_head)',
            'if move.returncode: refuse("GUARDED FOLD BRANCH UPDATE FAILED")',
            'align = run(repo, "reset", "--hard", new_head)',
            'if align.returncode:',
            '    rollback = run(repo, "update-ref", ref, expected_head, new_head)',
            '    run(repo, "reset", "--hard", expected_head)',
            '    if rollback.returncode: refuse("FOLD WORKTREE REALIGN FAILED // REF ROLLBACK FAILED", 91)',
            '    refuse("FOLD WORKTREE REALIGN FAILED // REF ROLLED BACK", 90)',
            'print("OK\\t{}\\t{}\\t{}".format(expected_head, new_head, len(selected)))'
        ].join("\n");
    }

    function startExecutionProcess() {
        state = "FOLD // REHEARSING";
        executeProcess.exec([
            "python3",
            "-c",
            executionScript(),
            String(repositoryPath || ""),
            armedPlanJson
        ]);
    }

    function maybeFinishExecution() {
        if (!executionBusy
                || !executeExitSeen
                || !executeStdoutSeen
                || !executeStderrSeen)
            return;

        const out = String(executeStdout || "").trim();
        const err = String(executeStderr || "").trim();
        const lines = out.split("\n");
        let control = "";

        for (let i = lines.length - 1; i >= 0; --i) {
            const line = String(lines[i] || "");
            if (line.indexOf("OK\t") === 0
                    || line.indexOf("REFUSED\t") === 0) {
                control = line;
                break;
            }
        }

        const fields = control.split("\t");
        pendingExecutionSuccess =
            executeExitCode === 0
            && fields.length >= 4
            && fields[0] === "OK";
        pendingExecutionDetail =
            fields.length > 1
            ? fields.slice(1).join("\t")
            : String(err || out || ("FOLD EXIT " + executeExitCode)).trim();
        pendingNewHead =
            pendingExecutionSuccess
            ? String(fields[2] || "")
            : "";

        state = "FOLD // SNAPSHOT AFTER";
        snapshotPhase = "AFTER";
        pendingSnapshotRequest = snapshotService.capture(
            "HISTORY AFTER // FOLD COMMITS",
            journalContext()
        );

        if (!pendingSnapshotRequest)
            finalizeExecution(null, "AFTER SNAPSHOT COULD NOT START");
    }

    function finalizeExecution(afterSnapshot, warningText) {
        const warning = String(warningText || "");
        const success = pendingExecutionSuccess;
        const detail =
            String(pendingExecutionDetail || "")
            + (warning ? " // " + warning : "");
        const snapshot =
            afterSnapshot
            || {
                snapshotVersion: 1,
                repository: String(repositoryPath || ""),
                capturedAt: new Date().toISOString(),
                captureFailed: true,
                recoveryClass: "EVIDENCE_ONLY",
                recoveryReason: warning || "FOLD AFTER SNAPSHOT UNAVAILABLE"
            };

        if (pendingJournalId && operationJournal) {
            if (success)
                operationJournal.completeOperation(
                    pendingJournalId,
                    snapshot,
                    detail
                );
            else
                operationJournal.failOperation(
                    pendingJournalId,
                    snapshot,
                    detail
                );
        }

        executionBusy = false;
        pendingJournalId = "";
        pendingSnapshotRequest = "";
        snapshotPhase = "";

        if (success) {
            state = warning
                ? "FOLD // COMPLETE // SNAPSHOT WARNING"
                : "FOLD // COMPLETE";
            lastError = warning;
            headSha = pendingNewHead;
        } else {
            state = "FOLD // REFUSED";
            lastError = detail || "FOLD FAILED";
        }

        armed = false;
        armedPlanJson = "";
        const newHead = pendingNewHead;
        pendingNewHead = "";
        executionFinished(success, detail, newHead);
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

                if (String((snapshot || {}).recoveryClass || "")
                        !== "REF_RECOVERABLE") {
                    root.failBeforeSnapshot(
                        "FOLD REQUIRES CLEAN REF-RECOVERABLE STATE"
                    );
                    return;
                }

                root.pendingJournalId =
                    root.operationJournal.beginOperation(
                        "HISTORY/FOLD_COMMITS",
                        snapshot,
                        root.journalContext()
                    );

                if (!root.pendingJournalId) {
                    root.failBeforeSnapshot(
                        "FOLD JOURNAL RECORD COULD NOT START"
                    );
                    return;
                }

                root.startExecutionProcess();
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
        id: executeProcess
        stdout: StdioCollector {
            onStreamFinished: {
                root.executeStdout = this.text;
                root.executeStdoutSeen = true;
                root.maybeFinishExecution();
            }
        }
        stderr: StdioCollector {
            onStreamFinished: {
                root.executeStderr = this.text;
                root.executeStderrSeen = true;
                root.maybeFinishExecution();
            }
        }
        onExited: function(code, exitStatus) {
            root.executeExitCode = Number(code);
            root.executeExitSeen = true;
            root.maybeFinishExecution();
        }
    }
}
