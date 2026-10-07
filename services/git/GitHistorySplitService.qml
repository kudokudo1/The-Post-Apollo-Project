import QtQuick
import Quickshell
import Quickshell.Io

// Split one non-merge commit into two commits by file subset.
//
// First slice: file boundaries only. The target must be on the current linear
// first-parent history and change at least two A/M/D paths. The exact split is
// rehearsed in a temporary detached worktree, the combined replacement tree
// must equal the original target tree, and the final replayed tree must equal
// the original HEAD tree before the live branch may move.
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
    property string parentSha: ""
    property string targetSha: ""
    property string targetSubject: ""
    property string authorName: ""
    property string authorEmail: ""
    property string authorDate: ""
    property var files: []
    property var firstFiles: []
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

    signal previewReady()
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
        parentSha = "";
        targetSha = "";
        targetSubject = "";
        authorName = "";
        authorEmail = "";
        authorDate = "";
        files = [];
        firstFiles = [];
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

    function selectedForFirst(path) {
        return firstFiles.indexOf(String(path || "")) >= 0;
    }

    function toggleFirst(path) {
        const target = String(path || "");
        if (!target || executionBusy)
            return false;

        const next = firstFiles.slice();
        const index = next.indexOf(target);

        if (index >= 0)
            next.splice(index, 1);
        else
            next.push(target);

        firstFiles = next;
        disarm("PLAN CHANGED");
        return true;
    }

    function setFirstMessage(message) {
        firstMessage = String(message || "");
        disarm("PLAN CHANGED");
    }

    function setSecondMessage(message) {
        secondMessage = String(message || "");
        disarm("PLAN CHANGED");
    }

    function preview(target) {
        if (previewBusy || executionBusy)
            return false;

        const repo = String(repositoryPath || "").trim();
        const targetInput = String(target || "").trim();

        if (!repo || !targetInput) {
            state = "SPLIT // REFUSED";
            lastError = !repo ? "NO REPOSITORY" : "TARGET COMMIT REQUIRED";
            return false;
        }

        previewBusy = true;
        armed = false;
        armedPlanJson = "";
        state = "SPLIT // READING TARGET";
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
            targetInput
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
            'if run("merge-base", "--is-ancestor", target, head).returncode: refuse("TARGET IS NOT AN ANCESTOR OF HEAD")',
            'parents = text(run("rev-list", "--parents", "-n", "1", target)).split()',
            'if len(parents) != 2: refuse("SPLIT TARGET MUST HAVE EXACTLY ONE PARENT")',
            'parent = parents[1]',
            'if run("rev-list", "--merges", parent + ".." + head).stdout.strip(): refuse("REWRITE RANGE CONTAINS MERGE COMMITS")',
            'ordered = text(run("rev-list", "--first-parent", "--reverse", parent + ".." + head)).splitlines()',
            'if not ordered or ordered[0] != target: refuse("TARGET IS NOT ON CURRENT FIRST-PARENT CHAIN")',
            'raw = text(run("diff-tree", "--no-commit-id", "--name-status", "-r", target))',
            'rows = []',
            'for line in raw.splitlines():',
            '    if not line: continue',
            '    parts = line.split("\\t")',
            '    status = parts[0] if parts else ""',
            '    if status.startswith("R") or status.startswith("C"): refuse("RENAME/COPY TARGETS ARE NOT SUPPORTED IN FILE SPLIT YET")',
            '    if status not in ("A", "M", "D"): refuse("UNSUPPORTED TARGET FILE STATUS // " + status)',
            '    path = parts[1] if len(parts) > 1 else ""',
            '    if path: rows.append({"status": status, "path": path})',
            'if len(rows) < 2: refuse("FILE SPLIT REQUIRES AT LEAST TWO CHANGED PATHS")',
            'meta = text(run("show", "-s", "--format=%s%x09%an%x09%ae%x09%aI", target)).split("\\t")',
            'payload = {"branch": branch, "head": head, "target": target, "parent": parent, "subject": meta[0] if len(meta) > 0 else "", "authorName": meta[1] if len(meta) > 1 else "", "authorEmail": meta[2] if len(meta) > 2 else "", "authorDate": meta[3] if len(meta) > 3 else "", "files": rows}',
            'print("JSON\\t" + json.dumps(payload, separators=(",", ":")))'
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
            return;
        }

        branchName = String(payload.branch || "");
        headSha = String(payload.head || "");
        targetSha = String(payload.target || "");
        parentSha = String(payload.parent || "");
        targetSubject = String(payload.subject || "");
        authorName = String(payload.authorName || "");
        authorEmail = String(payload.authorEmail || "");
        authorDate = String(payload.authorDate || "");
        files = cloneValue(payload.files || []);
        firstFiles = files.length > 0
            ? [String((files[0] || {}).path || "")]
            : [];
        firstMessage = targetSubject + " // PART 1";
        secondMessage = targetSubject + " // PART 2";
        state =
            "SPLIT // PLAN READY // "
            + String(files.length)
            + " FILES";
        lastError = "";
        previewReady();
    }

    function secondFiles() {
        const out = [];
        for (let i = 0; i < files.length; ++i) {
            const path = String((files[i] || {}).path || "");
            if (path && firstFiles.indexOf(path) < 0)
                out.push(path);
        }
        return out;
    }

    function planObject() {
        return {
            branch: branchName,
            head: headSha,
            target: targetSha,
            parent: parentSha,
            subject: targetSubject,
            authorName: authorName,
            authorEmail: authorEmail,
            authorDate: authorDate,
            files: cloneValue(files),
            firstFiles: firstFiles.slice(),
            secondFiles: secondFiles(),
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
                || !plan.target
                || !plan.parent
                || plan.files.length < 2
                || plan.firstFiles.length < 1
                || plan.secondFiles.length < 1
                || !plan.firstMessage
                || !plan.secondMessage) {
            state = "SPLIT // REFUSED";
            lastError =
                "SPLIT REQUIRES A NON-EMPTY STRICT FILE SUBSET + TWO MESSAGES";
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
            operation: "SPLIT_COMMIT_BY_FILE",
            scope: "file",
            branch: plan.branch,
            head: plan.head,
            targetSha: plan.target,
            parentSha: plan.parent,
            firstFiles: plan.firstFiles.slice(),
            secondFiles: plan.secondFiles.slice(),
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
            "HISTORY BEFORE // SPLIT COMMIT BY FILE",
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
            'import base64, json, os, shutil, stat, subprocess, sys, tempfile',
            'repo = sys.argv[1]',
            'plan = json.loads(sys.argv[2])',
            'branch, expected_head, target, parent = plan["branch"], plan["head"], plan["target"], plan["parent"]',
            'first_files, second_files = plan["firstFiles"], plan["secondFiles"]',
            'first_message, second_message = plan["firstMessage"], plan["secondMessage"]',
            'author_name, author_email, author_date = plan["authorName"], plan["authorEmail"], plan["authorDate"]',
            'def run(repo_path, *args, env=None): return subprocess.run(["git", "-C", repo_path] + list(args), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)',
            'def text(proc): return proc.stdout.decode("utf-8", "surrogateescape").strip()',
            'def refuse(msg, code=1): print("REFUSED\\t" + msg); sys.exit(code)',
            'if text(run(repo, "branch", "--show-current")) != branch: refuse("CURRENT BRANCH CHANGED SINCE ARM")',
            'if text(run(repo, "rev-parse", "HEAD")) != expected_head: refuse("HEAD CHANGED SINCE ARM")',
            'if run(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout.strip(): refuse("WORKTREE DIRTY SINCE ARM")',
            'if run(repo, "rev-list", "--merges", parent + ".." + expected_head).stdout.strip(): refuse("REWRITE RANGE NOW CONTAINS MERGE COMMITS")',
            'ordered = text(run(repo, "rev-list", "--first-parent", "--reverse", parent + ".." + expected_head)).splitlines()',
            'if not ordered or ordered[0] != target: refuse("TARGET LEFT CURRENT FIRST-PARENT CHAIN")',
            'subjects = {sha: text(run(repo, "show", "-s", "--format=%s", sha)).replace("\\n", " ").replace("\\r", " ") for sha in ordered}',
            'todo = ["edit {} {}".format(target, subjects[target])] + ["pick {} {}".format(sha, subjects[sha]) for sha in ordered[1:]]',
            'tmp = tempfile.mkdtemp(prefix="pa-split-file-")',
            'wt, todo_path, editor = os.path.join(tmp, "worktree"), os.path.join(tmp, "todo"), os.path.join(tmp, "sequence-editor")',
            'try:',
            '    add = run(repo, "worktree", "add", "--detach", wt, expected_head)',
            '    if add.returncode: refuse("SPLIT REHEARSAL WORKTREE CREATE FAILED // " + add.stderr.decode("utf-8", "replace").strip())',
            '    open(todo_path, "w", encoding="utf-8").write("\\n".join(todo) + "\\n")',
            '    open(editor, "w", encoding="utf-8").write("#!/bin/sh\\ncp \\"$PA_SPLIT_TODO\\" \\"$1\\"\\n")',
            '    os.chmod(editor, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)',
            '    env = dict(os.environ); env["GIT_SEQUENCE_EDITOR"] = editor; env["GIT_EDITOR"] = ":"; env["PA_SPLIT_TODO"] = todo_path',
            '    stopped = run(wt, "-c", "commit.gpgSign=false", "rebase", "-i", "--empty=keep", "--reapply-cherry-picks", parent, env=env)',
            '    gd = text(run(wt, "rev-parse", "--git-dir"))',
            '    if not os.path.isabs(gd): gd = os.path.join(wt, gd)',
            '    if not os.path.isdir(os.path.join(gd, "rebase-merge")) and not os.path.isdir(os.path.join(gd, "rebase-apply")): refuse("SPLIT REHEARSAL DID NOT PAUSE AT TARGET")',
            '    reset = run(wt, "reset", "HEAD^")',
            '    if reset.returncode: refuse("SPLIT TARGET UNCOMMIT FAILED // " + reset.stderr.decode("utf-8", "replace").strip())',
            '    stage_first = run(wt, "add", "-A", "--", *first_files)',
            '    if stage_first.returncode: refuse("SPLIT FIRST FILE STAGE FAILED // " + stage_first.stderr.decode("utf-8", "replace").strip())',
            '    if run(wt, "diff", "--cached", "--quiet").returncode == 0: refuse("SPLIT FIRST COMMIT WOULD BE EMPTY")',
            '    author_env = dict(os.environ); author_env["GIT_AUTHOR_NAME"] = author_name; author_env["GIT_AUTHOR_EMAIL"] = author_email; author_env["GIT_AUTHOR_DATE"] = author_date',
            '    first_payload = base64.b64encode(first_message.encode("utf-8")).decode("ascii")',
            '    first = subprocess.run(["bash", "-lc", "printf %s \\"$1\\" | base64 -d | git -C \\"$2\\" -c commit.gpgSign=false commit --no-verify -F -", "split-first", first_payload, wt], env=author_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)',
            '    if first.returncode: refuse("SPLIT FIRST COMMIT FAILED // " + first.stderr.decode("utf-8", "replace").strip())',
            '    stage_second = run(wt, "add", "-A")',
            '    if stage_second.returncode: refuse("SPLIT SECOND FILE STAGE FAILED // " + stage_second.stderr.decode("utf-8", "replace").strip())',
            '    if run(wt, "diff", "--cached", "--quiet").returncode == 0: refuse("SPLIT SECOND COMMIT WOULD BE EMPTY")',
            '    second_payload = base64.b64encode(second_message.encode("utf-8")).decode("ascii")',
            '    second = subprocess.run(["bash", "-lc", "printf %s \\"$1\\" | base64 -d | git -C \\"$2\\" -c commit.gpgSign=false commit --no-verify -F -", "split-second", second_payload, wt], env=author_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)',
            '    if second.returncode: refuse("SPLIT SECOND COMMIT FAILED // " + second.stderr.decode("utf-8", "replace").strip())',
            '    if run(wt, "diff", "--quiet", target, "HEAD").returncode: refuse("SPLIT REPLACEMENT TREE DOES NOT MATCH ORIGINAL TARGET")',
            '    continued = run(wt, "rebase", "--continue", env=dict(os.environ, GIT_EDITOR=":"))',
            '    if continued.returncode:',
            '        run(wt, "rebase", "--abort")',
            '        detail = continued.stderr.decode("utf-8", "replace").strip() or continued.stdout.decode("utf-8", "replace").strip()',
            '        refuse("SPLIT LATER-COMMIT REPLAY FAILED // " + detail)',
            '    new_head = text(run(wt, "rev-parse", "HEAD"))',
            '    if not new_head: refuse("SPLIT REHEARSAL PRODUCED NO HEAD")',
            '    if run(wt, "diff", "--quiet", expected_head, new_head).returncode: refuse("SPLIT FINAL TREE DOES NOT MATCH ORIGINAL HEAD")',
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
            'print("OK\\t{}\\t{}\\t{}".format(expected_head, new_head, target))'
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
            fields.length > 1
            ? fields.slice(1).join("\t")
            : String(err || out || ("SPLIT EXIT " + executeExitCode)).trim();
        pendingNewHead =
            pendingExecutionSuccess
            ? String(fields[2] || "")
            : "";

        state = "SPLIT // SNAPSHOT AFTER";
        snapshotPhase = "AFTER";
        pendingSnapshotRequest = snapshotService.capture(
            "HISTORY AFTER // SPLIT COMMIT BY FILE",
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
                recoveryReason: warning || "SPLIT AFTER SNAPSHOT UNAVAILABLE"
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
        armed = false;
        armedPlanJson = "";

        if (success) {
            state = warning
                ? "SPLIT // COMPLETE // SNAPSHOT WARNING"
                : "SPLIT // COMPLETE";
            lastError = warning;
            headSha = pendingNewHead;
        } else {
            state = "SPLIT // REFUSED";
            lastError = detail || "SPLIT FAILED";
        }

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
