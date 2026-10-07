import QtQuick
import Quickshell
import Quickshell.Io

// Guarded single-commit split engine.
// First slice splits one non-merge commit into two commits by file groups.
// The exact rewrite is rehearsed in a temporary detached worktree before the
// live branch is moved with expected-old update-ref protection.
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
    property string targetSha: ""
    property string targetSubject: ""
    property var files: []
    property string firstMessage: ""
    property string secondMessage: ""

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

    signal previewReady(var files)
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
        targetSha = "";
        targetSubject = "";
        files = [];
        firstMessage = "";
        secondMessage = "";
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
            state = "SPLIT // " + String(reason);
    }

    function setMessages(first, second) {
        firstMessage = String(first || "");
        secondMessage = String(second || "");
        disarm("PLAN CHANGED");
    }

    function setFirstFile(index, selected) {
        const rowIndex = Number(index);

        if (executionBusy
                || rowIndex < 0
                || rowIndex >= files.length)
            return false;

        const next = cloneValue(files);
        const row = next[rowIndex] || {};
        row.first = Boolean(selected);
        next[rowIndex] = row;
        files = next;
        disarm("PLAN CHANGED");
        return true;
    }

    function selectedFirstPaths() {
        const out = [];

        for (let i = 0; i < files.length; ++i) {
            const row = files[i] || {};
            if (Boolean(row.first))
                out.push(String(row.path || ""));
        }

        return out.filter(function(path) {
            return path.length > 0;
        });
    }

    function preview(target) {
        if (previewBusy || executionBusy)
            return false;

        const repo = String(repositoryPath || "").trim();
        const commit = String(target || "").trim();

        if (!repo || !commit) {
            state = "SPLIT // REFUSED";
            lastError =
                !repo
                ? "NO REPOSITORY"
                : "TARGET COMMIT REQUIRED";
            return false;
        }

        previewBusy = true;
        armed = false;
        armedPlanJson = "";
        state = "SPLIT // READING COMMIT";
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
            commit
        ]);
        return true;
    }

    function previewScript() {
        return [
            'import json, subprocess, sys',
            'repo, target_input = sys.argv[1:3]',
            'def run(*args): return subprocess.run(["git", "-C", repo] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE)',
            'def text(proc): return proc.stdout.decode("utf-8", "surrogateescape").strip()',
            'def refuse(msg): print("REFUSED\\t" + msg); sys.exit(1)',
            'if run("rev-parse", "--is-inside-work-tree").returncode: refuse("NOT A GIT WORKTREE")',
            'if run("status", "--porcelain=v1", "--untracked-files=all").stdout.strip(): refuse("WORKTREE DIRTY // COMMIT OR STASH FIRST")',
            'branch = text(run("branch", "--show-current"))',
            'if not branch: refuse("DETACHED HEAD")',
            'head = text(run("rev-parse", "HEAD"))',
            'target = text(run("rev-parse", target_input + "^{commit}"))',
            'if not target: refuse("TARGET COMMIT CANNOT BE RESOLVED")',
            'chain = text(run("rev-list", "--first-parent", "HEAD")).splitlines()',
            'if target not in chain: refuse("TARGET COMMIT IS NOT ON CURRENT FIRST-PARENT CHAIN")',
            'parents = text(run("rev-list", "--parents", "-n", "1", target)).split()',
            'if len(parents) != 2: refuse("SPLIT TARGET MUST HAVE EXACTLY ONE PARENT")',
            'base = parents[1]',
            'if run("rev-list", "--merges", base + ".." + head).stdout.strip(): refuse("REWRITE RANGE CONTAINS MERGE COMMITS")',
            'diff = text(run("diff-tree", "--no-commit-id", "--name-status", "-r", "-M", target)).splitlines()',
            'rows = []',
            'for raw in diff:',
            '    if not raw: continue',
            '    fields = raw.split("\\t")',
            '    status = fields[0]',
            '    if status.startswith("R") or status.startswith("C"): refuse("SPLIT FIRST SLICE DOES NOT SUPPORT RENAMES OR COPIES")',
            '    if len(fields) != 2: refuse("UNSUPPORTED SPLIT PATH RECORD")',
            '    rows.append({"status": status, "path": fields[1], "first": False})',
            'if len(rows) < 2: refuse("FILE SPLIT REQUIRES AT LEAST TWO CHANGED FILES")',
            'subject = text(run("show", "-s", "--format=%s", target))',
            'print("JSON\\t" + json.dumps({"base": base, "branch": branch, "head": head, "target": target, "subject": subject, "files": rows}, separators=(",", ":")))'
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
            state = "SPLIT // REFUSED";
            lastError =
                refused
                || err
                || out
                || ("SPLIT PREVIEW EXIT " + previewExitCode);
            files = [];
            return;
        }

        baseSha = String(payload.base || "");
        branchName = String(payload.branch || "");
        headSha = String(payload.head || "");
        targetSha = String(payload.target || "");
        targetSubject = String(payload.subject || "");
        files = cloneValue(payload.files || []);

        // Deterministic initial partition: first changed file -> part 1.
        if (files.length > 0) {
            const next = cloneValue(files);
            next[0].first = true;
            files = next;
        }

        firstMessage = targetSubject + " // part 1";
        secondMessage = targetSubject + " // part 2";
        state =
            "SPLIT // PLAN READY // "
            + String(files.length)
            + " FILES";
        lastError = "";
        previewReady(cloneValue(files));
    }

    function planObject() {
        return {
            branch: branchName,
            head: headSha,
            base: baseSha,
            target: targetSha,
            subject: targetSubject,
            files: cloneValue(files),
            firstPaths: selectedFirstPaths(),
            firstMessage: String(firstMessage || "").trim(),
            secondMessage: String(secondMessage || "").trim()
        };
    }

    function arm() {
        if (previewBusy || executionBusy)
            return false;

        const plan = planObject();

        if (!plan.branch
                || !plan.head
                || !plan.base
                || !plan.target
                || plan.files.length < 2
                || plan.firstPaths.length <= 0
                || plan.firstPaths.length >= plan.files.length
                || !plan.firstMessage
                || !plan.secondMessage) {
            state = "SPLIT // REFUSED";
            lastError =
                "SPLIT REQUIRES NON-EMPTY FILE GROUPS + TWO MESSAGES";
            return false;
        }

        armedPlanJson = JSON.stringify(plan);
        armed = true;
        state = "SPLIT // ARMED";
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
            source: "GitHistorySplitService",
            operation: "SPLIT_COMMIT_FILES",
            scope: "files",
            branch: plan.branch,
            head: plan.head,
            baseSha: plan.base,
            targetSha: plan.target,
            firstPaths: cloneValue(plan.firstPaths),
            firstMessage: plan.firstMessage,
            secondMessage: plan.secondMessage
        };
    }

    function executeArmed() {
        if (previewBusy || executionBusy || !planStillArmed())
            return false;

        if (!operationJournal || !snapshotService) {
            state = "SPLIT // REFUSED";
            lastError = "SPLIT REQUIRES JOURNAL + SNAPSHOT SERVICES";
            return false;
        }

        executionBusy = true;
        state = "SPLIT // SNAPSHOT BEFORE";
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
            "HISTORY BEFORE // SPLIT COMMIT",
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
        state = "SPLIT // REFUSED";
        lastError =
            "SPLIT BEFORE SNAPSHOT FAILED // "
            + String(detail || "UNKNOWN ERROR");
        executionFinished(false, lastError, "");
    }

    function executionScript() {
        return [
            'import json, os, shutil, stat, subprocess, sys, tempfile',
            'repo = sys.argv[1]',
            'plan = json.loads(sys.argv[2])',
            'branch, expected_head, base, target = plan["branch"], plan["head"], plan["base"], plan["target"]',
            'first_paths = [str(x) for x in plan["firstPaths"]]',
            'first_message, second_message = plan["firstMessage"], plan["secondMessage"]',
            'def run(repo_path, *args, env=None): return subprocess.run(["git", "-C", repo_path] + list(args), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)',
            'def text(proc): return proc.stdout.decode("utf-8", "surrogateescape").strip()',
            'def refuse(msg, code=1): print("REFUSED\\t" + msg); sys.exit(code)',
            'if run(repo, "rev-parse", "--is-inside-work-tree").returncode: refuse("NOT A GIT WORKTREE")',
            'if text(run(repo, "branch", "--show-current")) != branch: refuse("CURRENT BRANCH CHANGED SINCE ARM")',
            'if text(run(repo, "rev-parse", "HEAD")) != expected_head: refuse("HEAD CHANGED SINCE ARM")',
            'if run(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout.strip(): refuse("WORKTREE DIRTY SINCE ARM")',
            'if run(repo, "rev-list", "--merges", base + ".." + expected_head).stdout.strip(): refuse("REWRITE RANGE NOW CONTAINS MERGE COMMITS")',
            'ordered = text(run(repo, "rev-list", "--first-parent", "--reverse", base + ".." + expected_head)).splitlines()',
            'if target not in ordered: refuse("SPLIT TARGET LEFT CURRENT FIRST-PARENT CHAIN")',
            'live_rows = []',
            'for raw in text(run(repo, "diff-tree", "--no-commit-id", "--name-status", "-r", "-M", target)).splitlines():',
            '    if not raw: continue',
            '    fields = raw.split("\\t"); status = fields[0]',
            '    if status.startswith("R") or status.startswith("C") or len(fields) != 2: refuse("SPLIT TARGET PATH SET CHANGED OR BECAME UNSUPPORTED")',
            '    live_rows.append(fields[1])',
            'planned_rows = [str(row.get("path", "")) for row in plan["files"]]',
            'if live_rows != planned_rows: refuse("SPLIT TARGET FILE SET CHANGED SINCE ARM")',
            'if not first_paths or len(first_paths) >= len(live_rows): refuse("SPLIT FILE GROUPS ARE NO LONGER VALID")',
            'subjects = {sha: text(run(repo, "show", "-s", "--format=%s", sha)).replace("\\n", " ").replace("\\r", " ") for sha in ordered}',
            'todo = [("{} {} {}".format("edit" if sha == target else "pick", sha, subjects[sha])) for sha in ordered]',
            'tmp = tempfile.mkdtemp(prefix="pa-split-")',
            'wt = os.path.join(tmp, "worktree"); todo_path = os.path.join(tmp, "todo"); editor = os.path.join(tmp, "sequence-editor")',
            'first_msg = os.path.join(tmp, "first-message"); second_msg = os.path.join(tmp, "second-message")',
            'try:',
            '    add = run(repo, "worktree", "add", "--detach", wt, expected_head)',
            '    if add.returncode: refuse("SPLIT REHEARSAL WORKTREE CREATE FAILED // " + add.stderr.decode("utf-8", "replace").strip())',
            '    open(todo_path, "w", encoding="utf-8").write("\\n".join(todo) + "\\n")',
            '    open(editor, "w", encoding="utf-8").write("#!/bin/sh\\ncp \\"$PA_SPLIT_TODO\\" \\"$1\\"\\n")',
            '    open(first_msg, "w", encoding="utf-8").write(first_message + "\\n")',
            '    open(second_msg, "w", encoding="utf-8").write(second_message + "\\n")',
            '    os.chmod(editor, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)',
            '    env = dict(os.environ); env["GIT_SEQUENCE_EDITOR"] = editor; env["GIT_EDITOR"] = ":"; env["PA_SPLIT_TODO"] = todo_path',
            '    paused = run(wt, "-c", "commit.gpgSign=false", "rebase", "-i", "--empty=keep", "--reapply-cherry-picks", base, env=env)',
            '    gd = text(run(wt, "rev-parse", "--git-dir")); gd = gd if os.path.isabs(gd) else os.path.join(wt, gd)',
            '    if not os.path.isdir(os.path.join(gd, "rebase-merge")) and not os.path.isdir(os.path.join(gd, "rebase-apply")): refuse("SPLIT REHEARSAL DID NOT PAUSE AT TARGET")',
            '    if text(run(wt, "rev-parse", "HEAD")) == base: refuse("SPLIT TARGET WAS NOT APPLIED BEFORE EDIT STOP")',
            '    reset = run(wt, "reset", "--mixed", "HEAD^")',
            '    if reset.returncode: refuse("SPLIT REHEARSAL COULD NOT UNCOMMIT TARGET")',
            '    staged = run(wt, "add", "-A", "--", *first_paths)',
            '    if staged.returncode: refuse("SPLIT FIRST FILE GROUP COULD NOT BE STAGED")',
            '    if run(wt, "diff", "--cached", "--quiet").returncode == 0: refuse("SPLIT FIRST FILE GROUP IS EMPTY")',
            '    first_commit = run(wt, "-c", "commit.gpgSign=false", "commit", "--no-verify", "-F", first_msg)',
            '    if first_commit.returncode: refuse("SPLIT FIRST COMMIT FAILED // " + first_commit.stderr.decode("utf-8", "replace").strip())',
            '    if run(wt, "add", "-A").returncode: refuse("SPLIT SECOND FILE GROUP COULD NOT BE STAGED")',
            '    if run(wt, "diff", "--cached", "--quiet").returncode == 0: refuse("SPLIT SECOND FILE GROUP IS EMPTY")',
            '    second_commit = run(wt, "-c", "commit.gpgSign=false", "commit", "--no-verify", "-F", second_msg)',
            '    if second_commit.returncode: refuse("SPLIT SECOND COMMIT FAILED // " + second_commit.stderr.decode("utf-8", "replace").strip())',
            '    continued = run(wt, "-c", "commit.gpgSign=false", "rebase", "--continue", env=env)',
            '    if continued.returncode:',
            '        run(wt, "rebase", "--abort")',
            '        detail = continued.stderr.decode("utf-8", "replace").strip() or continued.stdout.decode("utf-8", "replace").strip()',
            '        refuse("SPLIT REHEARSAL CONFLICT OR FAILURE // " + detail)',
            '    new_head = text(run(wt, "rev-parse", "HEAD"))',
            '    if not new_head: refuse("SPLIT REHEARSAL PRODUCED NO HEAD")',
            'finally:',
            '    run(repo, "worktree", "remove", "--force", wt)',
            '    shutil.rmtree(tmp, ignore_errors=True)',
            'if text(run(repo, "branch", "--show-current")) != branch: refuse("CURRENT BRANCH CHANGED AFTER REHEARSAL")',
            'if text(run(repo, "rev-parse", "HEAD")) != expected_head: refuse("HEAD CHANGED AFTER REHEARSAL")',
            'if run(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout.strip(): refuse("WORKTREE CHANGED AFTER REHEARSAL")',
            'ref = "refs/heads/" + branch',
            'run(repo, "update-ref", "ORIG_HEAD", expected_head)',
            'move = run(repo, "update-ref", ref, new_head, expected_head)',
            'if move.returncode: refuse("GUARDED SPLIT BRANCH UPDATE FAILED")',
            'align = run(repo, "reset", "--hard", new_head)',
            'if align.returncode:',
            '    rollback = run(repo, "update-ref", ref, expected_head, new_head)',
            '    run(repo, "reset", "--hard", expected_head)',
            '    if rollback.returncode: refuse("SPLIT WORKTREE REALIGN FAILED // REF ROLLBACK FAILED", 91)',
            '    refuse("SPLIT WORKTREE REALIGN FAILED // REF ROLLED BACK", 90)',
            'print("OK\\t{}\\t{}\\t{}".format(expected_head, new_head, len(live_rows)))'
        ].join("\n");
    }

    function startExecutionProcess() {
        state = "SPLIT // REHEARSING";
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
            pendingExecutionSuccess
            ? (
                "SPLIT "
                + String(targetSha || "").slice(0, 12)
                + " INTO TWO COMMITS"
              )
            : (
                fields[0] === "REFUSED"
                ? fields.slice(1).join("\t")
                : String(
                    err
                    || out
                    || ("SPLIT EXIT " + executeExitCode)
                  ).trim()
              );
        pendingNewHead =
            pendingExecutionSuccess
            ? String(fields[2] || "")
            : "";

        state = "SPLIT // SNAPSHOT AFTER";
        snapshotPhase = "AFTER";
        pendingSnapshotRequest = snapshotService.capture(
            "HISTORY AFTER // SPLIT COMMIT",
            journalContext()
        );

        if (!pendingSnapshotRequest)
            finalizeExecution(null, "AFTER SNAPSHOT COULD NOT START");
    }

    function finalizeExecution(afterSnapshot, warningText) {
        const warning = String(warningText || "");
        const snapshot =
            afterSnapshot
            || {
                snapshotVersion: 1,
                repository: String(repositoryPath || ""),
                capturedAt: new Date().toISOString(),
                captureFailed: true,
                recoveryClass: "EVIDENCE_ONLY",
                recoveryReason:
                    warning || "SPLIT AFTER SNAPSHOT UNAVAILABLE"
            };
        const detail =
            String(pendingExecutionDetail || "")
            + (warning ? " // " + warning : "");

        if (pendingJournalId && operationJournal) {
            if (pendingExecutionSuccess)
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

        const success = pendingExecutionSuccess;
        const newHead = pendingNewHead;

        executionBusy = false;
        pendingJournalId = "";
        pendingSnapshotRequest = "";
        snapshotPhase = "";
        armed = false;
        armedPlanJson = "";
        pendingNewHead = "";

        if (success) {
            state = warning
                ? "SPLIT // COMPLETE // SNAPSHOT WARNING"
                : "SPLIT // COMPLETE";
            lastError = warning;
            headSha = newHead;
        } else {
            state = "SPLIT // REFUSED";
            lastError = detail || "SPLIT FAILED";
        }

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
                        "SPLIT REQUIRES CLEAN REF-RECOVERABLE STATE"
                    );
                    return;
                }

                root.pendingJournalId =
                    root.operationJournal.beginOperation(
                        "HISTORY/SPLIT_COMMIT",
                        snapshot,
                        root.journalContext()
                    );

                if (!root.pendingJournalId) {
                    root.failBeforeSnapshot(
                        "SPLIT JOURNAL RECORD COULD NOT START"
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
