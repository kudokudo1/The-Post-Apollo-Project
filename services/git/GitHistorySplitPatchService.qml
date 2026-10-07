import QtQuick
import Quickshell
import Quickshell.Io

// Guarded hunk-level commit Split.
// Selects one or more historical hunks for replacement commit part 1;
// all remaining target-commit content becomes part 2. The exact rewrite is
// rehearsed in a detached worktree before guarded live ref movement.
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
    property string path: ""
    property int changedFileCount: 0
    property var hunks: []
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

    signal previewReady(var hunks)
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
        path = "";
        changedFileCount = 0;
        hunks = [];
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
            state = "HUNK SPLIT // " + String(reason);
    }

    function setMessages(first, second) {
        firstMessage = String(first || "");
        secondMessage = String(second || "");
        disarm("PLAN CHANGED");
    }

    function setFirstHunk(index, selected) {
        const rowIndex = Number(index);

        if (executionBusy
                || rowIndex < 0
                || rowIndex >= hunks.length)
            return false;

        const next = cloneValue(hunks);
        const row = next[rowIndex] || {};
        row.first = Boolean(selected);
        next[rowIndex] = row;
        hunks = next;
        disarm("PLAN CHANGED");
        return true;
    }

    function selectedHunkIndexes() {
        const out = [];

        for (let i = 0; i < hunks.length; ++i) {
            if (Boolean((hunks[i] || {}).first))
                out.push(Number((hunks[i] || {}).index));
        }

        return out;
    }

    function hasRemainder() {
        const selected = selectedHunkIndexes().length;
        return selected > 0
            && (
                selected < hunks.length
                || changedFileCount > 1
            );
    }

    function preview(target, targetPath) {
        if (previewBusy || executionBusy)
            return false;

        const repo = String(repositoryPath || "").trim();
        const commit = String(target || "").trim();
        const filePath = String(targetPath || "").trim();

        if (!repo || !commit || !filePath) {
            state = "HUNK SPLIT // REFUSED";
            lastError =
                !repo
                ? "NO REPOSITORY"
                : !commit
                ? "TARGET COMMIT REQUIRED"
                : "TARGET PATH REQUIRED";
            return false;
        }

        previewBusy = true;
        armed = false;
        armedPlanJson = "";
        state = "HUNK SPLIT // READING PATCH";
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
            commit,
            filePath
        ]);
        return true;
    }

    function previewScript() {
        return [
            'import json, re, subprocess, sys',
            'repo, target_input, path = sys.argv[1:4]',
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
            'if len(parents) != 2: refuse("HUNK SPLIT TARGET MUST HAVE EXACTLY ONE PARENT")',
            'base = parents[1]',
            'if run("rev-list", "--merges", base + ".." + head).stdout.strip(): refuse("REWRITE RANGE CONTAINS MERGE COMMITS")',
            'changed = [p for p in text(run("diff", "--name-only", base, target)).splitlines() if p]',
            'if path not in changed: refuse("TARGET PATH WAS NOT CHANGED BY COMMIT")',
            'status_lines = text(run("diff", "--name-status", "-M", base, target, "--", path)).splitlines()',
            'if len(status_lines) != 1: refuse("TARGET PATH STATUS IS AMBIGUOUS")',
            'fields = status_lines[0].split("\\t")',
            'status = fields[0] if fields else ""',
            'if status.startswith("R") or status.startswith("C"): refuse("HUNK SPLIT DOES NOT SUPPORT RENAMES OR COPIES")',
            'numstat = text(run("diff", "--numstat", base, target, "--", path)).split("\\t")',
            'if len(numstat) >= 2 and (numstat[0] == "-" or numstat[1] == "-"): refuse("HUNK SPLIT DOES NOT SUPPORT BINARY PATHS")',
            'proc = run("diff", "--no-ext-diff", "--binary", base, target, "--", path)',
            'if proc.returncode: refuse("TARGET PATCH CANNOT BE READ")',
            'lines = proc.stdout.decode("utf-8", "surrogateescape").splitlines(True)',
            'header, groups, current = [], [], None',
            'for raw in lines:',
            '    if raw.startswith("@@"):',
            '        if current is not None: groups.append(current)',
            '        current = [raw]',
            '    elif current is None: header.append(raw)',
            '    else: current.append(raw)',
            'if current is not None: groups.append(current)',
            'if not groups: refuse("TARGET PATH HAS NO TEXT HUNKS")',
            'rows = []',
            'for index, group in enumerate(groups):',
            '    added = sum(1 for line in group[1:] if line.startswith("+") and not line.startswith("+++"))',
            '    removed = sum(1 for line in group[1:] if line.startswith("-") and not line.startswith("---"))',
            '    rows.append({"index": index, "header": group[0].rstrip("\\n"), "added": added, "removed": removed, "preview": "".join(group[:8]).rstrip("\\n"), "first": False})',
            'subject = text(run("show", "-s", "--format=%s", target))',
            'payload = {"base": base, "branch": branch, "head": head, "target": target, "subject": subject, "path": path, "changedFileCount": len(changed), "hunks": rows}',
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
            state = "HUNK SPLIT // REFUSED";
            lastError =
                refused
                || err
                || out
                || ("HUNK SPLIT PREVIEW EXIT " + previewExitCode);
            hunks = [];
            return;
        }

        baseSha = String(payload.base || "");
        branchName = String(payload.branch || "");
        headSha = String(payload.head || "");
        targetSha = String(payload.target || "");
        targetSubject = String(payload.subject || "");
        path = String(payload.path || "");
        changedFileCount = Number(payload.changedFileCount || 0);
        hunks = cloneValue(payload.hunks || []);

        if (hunks.length > 0) {
            const next = cloneValue(hunks);
            next[0].first = true;
            hunks = next;
        }

        firstMessage = targetSubject + " // part 1";
        secondMessage = targetSubject + " // part 2";
        state =
            "HUNK SPLIT // PLAN READY // "
            + String(hunks.length)
            + " HUNK"
            + (hunks.length === 1 ? "" : "S");
        lastError = "";
        previewReady(cloneValue(hunks));
    }

    function planObject() {
        return {
            scope: "hunk",
            branch: branchName,
            head: headSha,
            base: baseSha,
            target: targetSha,
            subject: targetSubject,
            path: path,
            changedFileCount: changedFileCount,
            hunks: cloneValue(hunks),
            selectedHunks: selectedHunkIndexes(),
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
                || !plan.path
                || plan.hunks.length <= 0
                || plan.selectedHunks.length <= 0
                || !hasRemainder()
                || !plan.firstMessage
                || !plan.secondMessage) {
            state = "HUNK SPLIT // REFUSED";
            lastError =
                "HUNK SPLIT REQUIRES SELECTED HUNKS + NON-EMPTY REMAINDER + TWO MESSAGES";
            return false;
        }

        armedPlanJson = JSON.stringify(plan);
        armed = true;
        state = "HUNK SPLIT // ARMED";
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
            source: "GitHistorySplitPatchService",
            operation: "SPLIT_COMMIT_HUNKS",
            scope: "hunk",
            branch: plan.branch,
            head: plan.head,
            baseSha: plan.base,
            targetSha: plan.target,
            path: plan.path,
            selectedHunks: cloneValue(plan.selectedHunks),
            firstMessage: plan.firstMessage,
            secondMessage: plan.secondMessage
        };
    }

    function executeArmed() {
        if (previewBusy || executionBusy || !planStillArmed())
            return false;

        if (!operationJournal || !snapshotService) {
            state = "HUNK SPLIT // REFUSED";
            lastError = "HUNK SPLIT REQUIRES JOURNAL + SNAPSHOT SERVICES";
            return false;
        }

        executionBusy = true;
        state = "HUNK SPLIT // SNAPSHOT BEFORE";
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
            "HISTORY BEFORE // SPLIT COMMIT HUNKS",
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
        state = "HUNK SPLIT // REFUSED";
        lastError =
            "HUNK SPLIT BEFORE SNAPSHOT FAILED // "
            + String(detail || "UNKNOWN ERROR");
        executionFinished(false, lastError, "");
    }

    function executionScript() {
        return [
            'import json, os, shutil, stat, subprocess, sys, tempfile',
            'repo = sys.argv[1]',
            'plan = json.loads(sys.argv[2])',
            'branch, expected_head, base, target, path = plan["branch"], plan["head"], plan["base"], plan["target"], plan["path"]',
            'selected = sorted(set(int(x) for x in plan["selectedHunks"]))',
            'first_message, second_message = plan["firstMessage"], plan["secondMessage"]',
            'def run(repo_path, *args, env=None, data=None): return subprocess.run(["git", "-C", repo_path] + list(args), env=env, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)',
            'def text(proc): return proc.stdout.decode("utf-8", "surrogateescape").strip()',
            'def refuse(msg, code=1): print("REFUSED\\t" + msg); sys.exit(code)',
            'def selected_patch(repo_path):',
            '    proc = run(repo_path, "diff", "--no-ext-diff", "--binary", base, target, "--", path)',
            '    if proc.returncode: refuse("HISTORICAL HUNK PATCH CANNOT BE READ")',
            '    lines = proc.stdout.decode("utf-8", "surrogateescape").splitlines(True)',
            '    header, groups, current = [], [], None',
            '    for raw in lines:',
            '        if raw.startswith("@@"):',
            '            if current is not None: groups.append(current)',
            '            current = [raw]',
            '        elif current is None: header.append(raw)',
            '        else: current.append(raw)',
            '    if current is not None: groups.append(current)',
            '    if not groups: refuse("HISTORICAL HUNK SET DISAPPEARED")',
            '    if not selected or any(index < 0 or index >= len(groups) for index in selected): refuse("SELECTED HUNK SET IS INVALID")',
            '    return "".join(header + [line for index in selected for line in groups[index]]).encode("utf-8", "surrogateescape"), len(groups)',
            'if run(repo, "rev-parse", "--is-inside-work-tree").returncode: refuse("NOT A GIT WORKTREE")',
            'if text(run(repo, "branch", "--show-current")) != branch: refuse("CURRENT BRANCH CHANGED SINCE ARM")',
            'if text(run(repo, "rev-parse", "HEAD")) != expected_head: refuse("HEAD CHANGED SINCE ARM")',
            'if run(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout.strip(): refuse("WORKTREE DIRTY SINCE ARM")',
            'if run(repo, "rev-list", "--merges", base + ".." + expected_head).stdout.strip(): refuse("REWRITE RANGE NOW CONTAINS MERGE COMMITS")',
            'ordered = text(run(repo, "rev-list", "--first-parent", "--reverse", base + ".." + expected_head)).splitlines()',
            'if target not in ordered: refuse("SPLIT TARGET LEFT CURRENT FIRST-PARENT CHAIN")',
            'patch, hunk_count = selected_patch(repo)',
            'changed_files = [p for p in text(run(repo, "diff", "--name-only", base, target)).splitlines() if p]',
            'if len(selected) >= hunk_count and len(changed_files) <= 1: refuse("SELECTED HUNKS WOULD LEAVE EMPTY PART 2")',
            'subjects = {sha: text(run(repo, "show", "-s", "--format=%s", sha)).replace("\\n", " ").replace("\\r", " ") for sha in ordered}',
            'todo = [("{} {} {}".format("edit" if sha == target else "pick", sha, subjects[sha])) for sha in ordered]',
            'tmp = tempfile.mkdtemp(prefix="pa-hunk-split-")',
            'wt = os.path.join(tmp, "worktree"); todo_path = os.path.join(tmp, "todo"); editor = os.path.join(tmp, "sequence-editor")',
            'first_msg = os.path.join(tmp, "first-message"); second_msg = os.path.join(tmp, "second-message")',
            'try:',
            '    add = run(repo, "worktree", "add", "--detach", wt, expected_head)',
            '    if add.returncode: refuse("HUNK SPLIT REHEARSAL WORKTREE CREATE FAILED // " + add.stderr.decode("utf-8", "replace").strip())',
            '    open(todo_path, "w", encoding="utf-8").write("\\n".join(todo) + "\\n")',
            '    open(editor, "w", encoding="utf-8").write("#!/bin/sh\\ncp \\"$PA_SPLIT_TODO\\" \\"$1\\"\\n")',
            '    open(first_msg, "w", encoding="utf-8").write(first_message + "\\n")',
            '    open(second_msg, "w", encoding="utf-8").write(second_message + "\\n")',
            '    os.chmod(editor, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)',
            '    env = dict(os.environ); env["GIT_SEQUENCE_EDITOR"] = editor; env["GIT_EDITOR"] = ":"; env["PA_SPLIT_TODO"] = todo_path',
            '    paused = run(wt, "-c", "commit.gpgSign=false", "rebase", "-i", "--empty=keep", "--reapply-cherry-picks", base, env=env)',
            '    gd = text(run(wt, "rev-parse", "--git-dir")); gd = gd if os.path.isabs(gd) else os.path.join(wt, gd)',
            '    if not os.path.isdir(os.path.join(gd, "rebase-merge")) and not os.path.isdir(os.path.join(gd, "rebase-apply")): refuse("HUNK SPLIT REHEARSAL DID NOT PAUSE AT TARGET")',
            '    if run(wt, "reset", "--mixed", "HEAD^").returncode: refuse("HUNK SPLIT COULD NOT UNCOMMIT TARGET")',
            '    check = run(wt, "apply", "--check", "--cached", "--binary", "--whitespace=nowarn", "-", data=patch)',
            '    if check.returncode: refuse("SELECTED HISTORICAL HUNKS DO NOT APPLY TO TARGET PARENT // " + check.stderr.decode("utf-8", "replace").strip())',
            '    applied = run(wt, "apply", "--cached", "--binary", "--whitespace=nowarn", "-", data=patch)',
            '    if applied.returncode: refuse("SELECTED HUNKS COULD NOT BE STAGED")',
            '    if run(wt, "diff", "--cached", "--quiet").returncode == 0: refuse("HUNK SPLIT PART 1 IS EMPTY")',
            '    first_commit = run(wt, "-c", "commit.gpgSign=false", "commit", "--no-verify", "-F", first_msg)',
            '    if first_commit.returncode: refuse("HUNK SPLIT PART 1 COMMIT FAILED // " + first_commit.stderr.decode("utf-8", "replace").strip())',
            '    if run(wt, "add", "-A").returncode: refuse("HUNK SPLIT REMAINDER COULD NOT BE STAGED")',
            '    if run(wt, "diff", "--cached", "--quiet").returncode == 0: refuse("HUNK SPLIT PART 2 IS EMPTY")',
            '    second_commit = run(wt, "-c", "commit.gpgSign=false", "commit", "--no-verify", "-F", second_msg)',
            '    if second_commit.returncode: refuse("HUNK SPLIT PART 2 COMMIT FAILED // " + second_commit.stderr.decode("utf-8", "replace").strip())',
            '    continued = run(wt, "-c", "commit.gpgSign=false", "rebase", "--continue", env=env)',
            '    if continued.returncode:',
            '        run(wt, "rebase", "--abort")',
            '        detail = continued.stderr.decode("utf-8", "replace").strip() or continued.stdout.decode("utf-8", "replace").strip()',
            '        refuse("HUNK SPLIT REHEARSAL CONFLICT OR FAILURE // " + detail)',
            '    new_head = text(run(wt, "rev-parse", "HEAD"))',
            '    if not new_head: refuse("HUNK SPLIT REHEARSAL PRODUCED NO HEAD")',
            'finally:',
            '    run(repo, "worktree", "remove", "--force", wt)',
            '    shutil.rmtree(tmp, ignore_errors=True)',
            'if text(run(repo, "branch", "--show-current")) != branch: refuse("CURRENT BRANCH CHANGED AFTER REHEARSAL")',
            'if text(run(repo, "rev-parse", "HEAD")) != expected_head: refuse("HEAD CHANGED AFTER REHEARSAL")',
            'if run(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout.strip(): refuse("WORKTREE CHANGED AFTER REHEARSAL")',
            'ref = "refs/heads/" + branch',
            'run(repo, "update-ref", "ORIG_HEAD", expected_head)',
            'move = run(repo, "update-ref", ref, new_head, expected_head)',
            'if move.returncode: refuse("GUARDED HUNK SPLIT BRANCH UPDATE FAILED")',
            'align = run(repo, "reset", "--hard", new_head)',
            'if align.returncode:',
            '    rollback = run(repo, "update-ref", ref, expected_head, new_head)',
            '    run(repo, "reset", "--hard", expected_head)',
            '    if rollback.returncode: refuse("HUNK SPLIT REALIGN FAILED // REF ROLLBACK FAILED", 91)',
            '    refuse("HUNK SPLIT REALIGN FAILED // REF ROLLED BACK", 90)',
            'print("OK\\t{}\\t{}\\t{}".format(expected_head, new_head, len(selected)))'
        ].join("\n");
    }

    function startExecutionProcess() {
        state = "HUNK SPLIT // REHEARSING";
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
                + " BY "
                + String(fields[3] || "0")
                + " HUNK"
                + (String(fields[3] || "") === "1" ? "" : "S")
              )
            : (
                fields[0] === "REFUSED"
                ? fields.slice(1).join("\t")
                : String(
                    err
                    || out
                    || ("HUNK SPLIT EXIT " + executeExitCode)
                  ).trim()
              );
        pendingNewHead =
            pendingExecutionSuccess
            ? String(fields[2] || "")
            : "";

        state = "HUNK SPLIT // SNAPSHOT AFTER";
        snapshotPhase = "AFTER";
        pendingSnapshotRequest = snapshotService.capture(
            "HISTORY AFTER // SPLIT COMMIT HUNKS",
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
                    warning || "HUNK SPLIT AFTER SNAPSHOT UNAVAILABLE"
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
                ? "HUNK SPLIT // COMPLETE // SNAPSHOT WARNING"
                : "HUNK SPLIT // COMPLETE";
            lastError = warning;
            headSha = newHead;
        } else {
            state = "HUNK SPLIT // REFUSED";
            lastError = detail || "HUNK SPLIT FAILED";
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
                        "HUNK SPLIT REQUIRES CLEAN REF-RECOVERABLE STATE"
                    );
                    return;
                }

                root.pendingJournalId =
                    root.operationJournal.beginOperation(
                        "HISTORY/SPLIT_COMMIT_HUNK",
                        snapshot,
                        root.journalContext()
                    );

                if (!root.pendingJournalId) {
                    root.failBeforeSnapshot(
                        "HUNK SPLIT JOURNAL RECORD COULD NOT START"
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
