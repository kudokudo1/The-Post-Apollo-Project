import QtQuick
import Quickshell
import Quickshell.Io

// Guarded line-level commit Split.
//
// A selected set of atomic text edits from one modified historical path
// becomes replacement commit part 1. Every unselected edit from that path,
// plus every other path changed by the original commit, becomes part 2.
// The complete rewrite is rehearsed in a detached worktree before the live
// branch may move through an expected-old update-ref.
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
    property var lines: []
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

    signal previewReady(var lines)
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
        lines = [];
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
            state = "LINE SPLIT // " + String(reason);
    }

    function setMessages(first, second) {
        firstMessage = String(first || "");
        secondMessage = String(second || "");
        disarm("PLAN CHANGED");
    }

    function setFirstLine(index, selected) {
        const rowIndex = Number(index);

        if (executionBusy
                || rowIndex < 0
                || rowIndex >= lines.length)
            return false;

        const next = cloneValue(lines);
        const row = next[rowIndex] || {};
        row.first = Boolean(selected);
        next[rowIndex] = row;
        lines = next;
        disarm("PLAN CHANGED");
        return true;
    }

    function selectedLineIndexes() {
        const out = [];

        for (let i = 0; i < lines.length; ++i) {
            if (Boolean((lines[i] || {}).first))
                out.push(Number((lines[i] || {}).index));
        }

        return out;
    }

    function hasRemainder() {
        const selected = selectedLineIndexes().length;

        return selected > 0
            && (
                selected < lines.length
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
            state = "LINE SPLIT // REFUSED";
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
        state = "LINE SPLIT // READING PATCH";
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
            'import difflib, json, subprocess, sys',
            'repo, target_input, path = sys.argv[1:4]',
            'def run(*args): return subprocess.run(["git", "-C", repo] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE)',
            'def text(proc): return proc.stdout.decode("utf-8", "surrogateescape").strip()',
            'def refuse(msg): print("REFUSED\\t" + msg); sys.exit(1)',
            'def blob_lines(spec):',
            '    proc = run("show", spec)',
            '    if proc.returncode: refuse("TARGET FILE CONTENT CANNOT BE READ")',
            '    return proc.stdout.decode("utf-8", "surrogateescape").splitlines(True)',
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
            'if len(parents) != 2: refuse("LINE SPLIT TARGET MUST HAVE EXACTLY ONE PARENT")',
            'base = parents[1]',
            'if run("rev-list", "--merges", base + ".." + head).stdout.strip(): refuse("REWRITE RANGE CONTAINS MERGE COMMITS")',
            'changed = [p for p in text(run("diff", "--name-only", base, target)).splitlines() if p]',
            'if path not in changed: refuse("TARGET PATH WAS NOT CHANGED BY COMMIT")',
            'status_lines = text(run("diff", "--name-status", "-M", base, target, "--", path)).splitlines()',
            'if len(status_lines) != 1: refuse("TARGET PATH STATUS IS AMBIGUOUS")',
            'fields = status_lines[0].split("\\t")',
            'status = fields[0] if fields else ""',
            'if status != "M": refuse("LINE SPLIT REQUIRES AN EXISTING MODIFIED PATH")',
            'numstat = text(run("diff", "--numstat", base, target, "--", path)).split("\\t")',
            'if len(numstat) >= 2 and (numstat[0] == "-" or numstat[1] == "-"): refuse("LINE SPLIT DOES NOT SUPPORT BINARY PATHS")',
            'base_tree = text(run("ls-tree", base, "--", path)).split()',
            'target_tree = text(run("ls-tree", target, "--", path)).split()',
            'if len(base_tree) < 3 or len(target_tree) < 3: refuse("LINE SPLIT PATH TREE IDENTITY IS INCOMPLETE")',
            'if base_tree[0] != target_tree[0] or base_tree[1] != "blob" or target_tree[1] != "blob": refuse("LINE SPLIT DOES NOT SUPPORT MODE OR TYPE CHANGES")',
            'base_lines = blob_lines(base + ":" + path)',
            'target_lines = blob_lines(target + ":" + path)',
            'matcher = difflib.SequenceMatcher(a=base_lines, b=target_lines, autojunk=False)',
            'rows = []; unit = 0',
            'def clean(value): return value.rstrip("\\r\\n")',
            'for tag, i1, i2, j1, j2 in matcher.get_opcodes():',
            '    if tag == "equal": continue',
            '    if tag == "replace":',
            '        common = min(i2 - i1, j2 - j1)',
            '        for k in range(common):',
            '            rows.append({"index": unit, "kind": "replace", "oldLine": i1 + k + 1, "newLine": j1 + k + 1, "oldText": clean(base_lines[i1 + k]), "newText": clean(target_lines[j1 + k]), "first": False}); unit += 1',
            '        for k in range(common, i2 - i1):',
            '            rows.append({"index": unit, "kind": "delete", "oldLine": i1 + k + 1, "newLine": j2 + 1, "oldText": clean(base_lines[i1 + k]), "newText": "", "first": False}); unit += 1',
            '        for k in range(common, j2 - j1):',
            '            rows.append({"index": unit, "kind": "insert", "oldLine": i2 + 1, "newLine": j1 + k + 1, "oldText": "", "newText": clean(target_lines[j1 + k]), "first": False}); unit += 1',
            '    elif tag == "delete":',
            '        for k in range(i1, i2):',
            '            rows.append({"index": unit, "kind": "delete", "oldLine": k + 1, "newLine": j1 + 1, "oldText": clean(base_lines[k]), "newText": "", "first": False}); unit += 1',
            '    elif tag == "insert":',
            '        for k in range(j1, j2):',
            '            rows.append({"index": unit, "kind": "insert", "oldLine": i1 + 1, "newLine": k + 1, "oldText": "", "newText": clean(target_lines[k]), "first": False}); unit += 1',
            'if not rows: refuse("TARGET PATH HAS NO SELECTABLE TEXT LINE EDITS")',
            'subject = text(run("show", "-s", "--format=%s", target))',
            'payload = {"base": base, "branch": branch, "head": head, "target": target, "subject": subject, "path": path, "changedFileCount": len(changed), "lines": rows}',
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
        const outputLines = out.split("\n");
        let payload = null;
        let refused = "";

        for (let i = 0; i < outputLines.length; ++i) {
            const line = String(outputLines[i] || "");

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
            state = "LINE SPLIT // REFUSED";
            lastError =
                refused
                || err
                || out
                || ("LINE SPLIT PREVIEW EXIT " + previewExitCode);
            lines = [];
            return;
        }

        baseSha = String(payload.base || "");
        branchName = String(payload.branch || "");
        headSha = String(payload.head || "");
        targetSha = String(payload.target || "");
        targetSubject = String(payload.subject || "");
        path = String(payload.path || "");
        changedFileCount = Number(payload.changedFileCount || 0);
        lines = cloneValue(payload.lines || []);

        if (lines.length > 0) {
            const next = cloneValue(lines);
            next[0].first = true;
            lines = next;
        }

        firstMessage = targetSubject + " // part 1";
        secondMessage = targetSubject + " // part 2";
        state =
            "LINE SPLIT // PLAN READY // "
            + String(lines.length)
            + " EDIT"
            + (lines.length === 1 ? "" : "S");
        lastError = "";
        previewReady(cloneValue(lines));
    }

    function planObject() {
        return {
            scope: "line",
            branch: branchName,
            head: headSha,
            base: baseSha,
            target: targetSha,
            subject: targetSubject,
            path: path,
            changedFileCount: changedFileCount,
            lines: cloneValue(lines),
            selectedLines: selectedLineIndexes(),
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
                || plan.lines.length <= 0
                || plan.selectedLines.length <= 0
                || !hasRemainder()
                || !plan.firstMessage
                || !plan.secondMessage) {
            state = "LINE SPLIT // REFUSED";
            lastError =
                !hasRemainder()
                ? "SELECTED LINES WOULD LEAVE EMPTY PART 2"
                : "LINE SPLIT PLAN IS INCOMPLETE";
            return false;
        }

        armedPlanJson = JSON.stringify(plan);
        armed = true;
        state = "LINE SPLIT // ARMED";
        lastError = "";
        return true;
    }

    function planStillArmed() {
        return armed
            && armedPlanJson === JSON.stringify(planObject());
    }

    function journalContext() {
        return {
            source: "GitHistorySplitLineService",
            operation: "SPLIT_COMMIT_LINE",
            scope: "line",
            branch: branchName,
            head: headSha,
            base: baseSha,
            target: targetSha,
            path: path,
            selectedLines: selectedLineIndexes(),
            firstMessage: String(firstMessage || "").trim(),
            secondMessage: String(secondMessage || "").trim()
        };
    }

    function executeArmed() {
        if (previewBusy
                || executionBusy
                || !planStillArmed())
            return false;

        if (!operationJournal || !snapshotService) {
            state = "LINE SPLIT // REFUSED";
            lastError =
                "LINE SPLIT REQUIRES JOURNAL + SNAPSHOT SERVICES";
            return false;
        }

        executionBusy = true;
        pendingExecutionSuccess = false;
        pendingExecutionDetail = "";
        pendingNewHead = "";
        state = "LINE SPLIT // SNAPSHOT BEFORE";
        lastError = "";

        executeExitSeen = false;
        executeStdoutSeen = false;
        executeStderrSeen = false;
        executeExitCode = -1;
        executeStdout = "";
        executeStderr = "";

        snapshotPhase = "BEFORE";
        pendingSnapshotRequest = snapshotService.capture(
            "HISTORY BEFORE // SPLIT COMMIT LINES",
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
        armed = false;
        armedPlanJson = "";
        state = "LINE SPLIT // REFUSED";
        lastError =
            "LINE SPLIT BEFORE SNAPSHOT FAILED // "
            + String(detail || "UNKNOWN ERROR");
        executionFinished(false, lastError, "");
    }

    function executionScript() {
        return [
            'import difflib, json, os, shutil, stat, subprocess, sys, tempfile',
            'repo, plan_json = sys.argv[1:3]',
            'def run(repo_path, *args, env=None): return subprocess.run(["git", "-C", repo_path] + list(args), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)',
            'def text(proc): return proc.stdout.decode("utf-8", "surrogateescape").strip()',
            'def refuse(msg, code=1): print("REFUSED\\t" + msg); sys.exit(code)',
            'try: plan = json.loads(plan_json)',
            'except Exception: refuse("LINE SPLIT PLAN JSON INVALID")',
            'branch = str(plan.get("branch", "")); expected_head = str(plan.get("head", "")); base = str(plan.get("base", "")); target = str(plan.get("target", "")); path = str(plan.get("path", ""))',
            'selected = sorted(set(int(value) for value in plan.get("selectedLines", [])))',
            'first_message = str(plan.get("firstMessage", "")).strip(); second_message = str(plan.get("secondMessage", "")).strip()',
            'if not branch or not expected_head or not base or not target or not path or not selected or not first_message or not second_message: refuse("LINE SPLIT PLAN IS INCOMPLETE")',
            'if text(run(repo, "branch", "--show-current")) != branch: refuse("CURRENT BRANCH CHANGED SINCE ARM")',
            'if text(run(repo, "rev-parse", "HEAD")) != expected_head: refuse("HEAD CHANGED SINCE ARM")',
            'if run(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout.strip(): refuse("WORKTREE DIRTY SINCE ARM")',
            'if run(repo, "rev-list", "--merges", base + ".." + expected_head).stdout.strip(): refuse("REWRITE RANGE NOW CONTAINS MERGE COMMITS")',
            'parents = text(run(repo, "rev-list", "--parents", "-n", "1", target)).split()',
            'if len(parents) != 2 or parents[1] != base: refuse("TARGET PARENT CHANGED SINCE PREVIEW")',
            'status = text(run(repo, "diff", "--name-status", "-M", base, target, "--", path)).splitlines()',
            'if len(status) != 1 or status[0].split("\\t")[0] != "M": refuse("LINE SPLIT PATH IS NO LONGER A SIMPLE MODIFICATION")',
            'base_proc = run(repo, "show", base + ":" + path); target_proc = run(repo, "show", target + ":" + path)',
            'if base_proc.returncode or target_proc.returncode: refuse("LINE SPLIT FILE CONTENT CAN NO LONGER BE READ")',
            'base_lines = base_proc.stdout.decode("utf-8", "surrogateescape").splitlines(True); target_lines = target_proc.stdout.decode("utf-8", "surrogateescape").splitlines(True)',
            'matcher = difflib.SequenceMatcher(a=base_lines, b=target_lines, autojunk=False)',
            'out = []; unit = 0; total = 0',
            'selected_set = set(selected)',
            'for tag, i1, i2, j1, j2 in matcher.get_opcodes():',
            '    if tag == "equal": out.extend(base_lines[i1:i2]); continue',
            '    if tag == "replace":',
            '        common = min(i2 - i1, j2 - j1)',
            '        for k in range(common):',
            '            out.append(target_lines[j1 + k] if unit in selected_set else base_lines[i1 + k]); unit += 1',
            '        for k in range(common, i2 - i1):',
            '            if unit not in selected_set: out.append(base_lines[i1 + k])',
            '            unit += 1',
            '        for k in range(common, j2 - j1):',
            '            if unit in selected_set: out.append(target_lines[j1 + k])',
            '            unit += 1',
            '    elif tag == "delete":',
            '        for k in range(i1, i2):',
            '            if unit not in selected_set: out.append(base_lines[k])',
            '            unit += 1',
            '    elif tag == "insert":',
            '        for k in range(j1, j2):',
            '            if unit in selected_set: out.append(target_lines[k])',
            '            unit += 1',
            'total = unit',
            'if any(value < 0 or value >= total for value in selected): refuse("SELECTED LINE SET NO LONGER MATCHES TARGET")',
            'changed_count = len([p for p in text(run(repo, "diff", "--name-only", base, target)).splitlines() if p])',
            'if len(selected) >= total and changed_count <= 1: refuse("SELECTED LINES WOULD LEAVE EMPTY PART 2")',
            'part1_bytes = "".join(out).encode("utf-8", "surrogateescape")',
            'ordered = text(run(repo, "rev-list", "--first-parent", "--reverse", base + ".." + expected_head)).splitlines()',
            'if target not in ordered: refuse("TARGET COMMIT LEFT CURRENT REWRITE RANGE")',
            'subjects = {sha: text(run(repo, "show", "-s", "--format=%s", sha)) for sha in ordered}',
            'tmp = tempfile.mkdtemp(prefix="pa-line-split-"); wt = os.path.join(tmp, "worktree"); todo = os.path.join(tmp, "todo"); editor = os.path.join(tmp, "sequence-editor"); first_msg = os.path.join(tmp, "first-message"); second_msg = os.path.join(tmp, "second-message")',
            'try:',
            '    add = run(repo, "worktree", "add", "--detach", wt, expected_head)',
            '    if add.returncode: refuse("LINE SPLIT REHEARSAL WORKTREE CREATE FAILED // " + add.stderr.decode("utf-8", "replace").strip())',
            '    with open(todo, "w", encoding="utf-8") as handle: handle.write("\\n".join(("edit" if sha == target else "pick") + " " + sha + " " + subjects[sha].replace("\\n", " ") for sha in ordered) + "\\n")',
            '    with open(editor, "w", encoding="utf-8") as handle: handle.write("#!/bin/sh\\ncp \\"$PA_LINE_SPLIT_TODO\\" \\"$1\\"\\n")',
            '    os.chmod(editor, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)',
            '    with open(first_msg, "w", encoding="utf-8") as handle: handle.write(first_message + "\\n")',
            '    with open(second_msg, "w", encoding="utf-8") as handle: handle.write(second_message + "\\n")',
            '    env = dict(os.environ); env["GIT_SEQUENCE_EDITOR"] = editor; env["GIT_EDITOR"] = ":"; env["PA_LINE_SPLIT_TODO"] = todo',
            '    paused = run(wt, "-c", "commit.gpgSign=false", "rebase", "-i", "--empty=keep", "--reapply-cherry-picks", base, env=env)',
            '    if paused.returncode or not os.path.isdir(os.path.join(text(run(wt, "rev-parse", "--git-dir")) if os.path.isabs(text(run(wt, "rev-parse", "--git-dir"))) else os.path.join(wt, text(run(wt, "rev-parse", "--git-dir"))), "rebase-merge")): refuse("LINE SPLIT REHEARSAL DID NOT PAUSE AT TARGET")',
            '    reset = run(wt, "reset", "--mixed", "HEAD^")',
            '    if reset.returncode: refuse("LINE SPLIT COULD NOT UNCOMMIT TARGET")',
            '    target_path = os.path.join(wt, path)',
            '    os.makedirs(os.path.dirname(target_path) or wt, exist_ok=True)',
            '    with open(target_path, "wb") as handle: handle.write(part1_bytes)',
            '    staged = run(wt, "add", "--", path)',
            '    if staged.returncode: refuse("LINE SPLIT PART 1 COULD NOT STAGE SELECTED LINES")',
            '    if run(wt, "diff", "--cached", "--quiet").returncode == 0: refuse("LINE SPLIT PART 1 IS EMPTY")',
            '    first_commit = run(wt, "-c", "commit.gpgSign=false", "commit", "--no-verify", "-F", first_msg)',
            '    if first_commit.returncode: refuse("LINE SPLIT PART 1 COMMIT FAILED // " + first_commit.stderr.decode("utf-8", "replace").strip())',
            '    with open(target_path, "wb") as handle: handle.write(target_proc.stdout)',
            '    add_rest = run(wt, "add", "-A")',
            '    if add_rest.returncode: refuse("LINE SPLIT PART 2 COULD NOT STAGE REMAINDER")',
            '    if run(wt, "diff", "--cached", "--quiet").returncode == 0: refuse("LINE SPLIT PART 2 IS EMPTY")',
            '    second_commit = run(wt, "-c", "commit.gpgSign=false", "commit", "--no-verify", "-F", second_msg)',
            '    if second_commit.returncode: refuse("LINE SPLIT PART 2 COMMIT FAILED // " + second_commit.stderr.decode("utf-8", "replace").strip())',
            '    continued = run(wt, "-c", "commit.gpgSign=false", "rebase", "--continue", env=env)',
            '    if continued.returncode:',
            '        run(wt, "rebase", "--abort")',
            '        detail = continued.stderr.decode("utf-8", "replace").strip() or continued.stdout.decode("utf-8", "replace").strip()',
            '        refuse("LINE SPLIT REHEARSAL CONFLICT OR FAILURE // " + detail)',
            '    new_head = text(run(wt, "rev-parse", "HEAD"))',
            '    if not new_head: refuse("LINE SPLIT REHEARSAL PRODUCED NO HEAD")',
            'finally:',
            '    run(repo, "worktree", "remove", "--force", wt)',
            '    shutil.rmtree(tmp, ignore_errors=True)',
            'if text(run(repo, "branch", "--show-current")) != branch: refuse("CURRENT BRANCH CHANGED AFTER REHEARSAL")',
            'if text(run(repo, "rev-parse", "HEAD")) != expected_head: refuse("HEAD CHANGED AFTER REHEARSAL")',
            'if run(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout.strip(): refuse("WORKTREE CHANGED AFTER REHEARSAL")',
            'ref = "refs/heads/" + branch',
            'run(repo, "update-ref", "ORIG_HEAD", expected_head)',
            'move = run(repo, "update-ref", ref, new_head, expected_head)',
            'if move.returncode: refuse("GUARDED LINE SPLIT BRANCH UPDATE FAILED")',
            'align = run(repo, "reset", "--hard", new_head)',
            'if align.returncode:',
            '    rollback = run(repo, "update-ref", ref, expected_head, new_head)',
            '    run(repo, "reset", "--hard", expected_head)',
            '    if rollback.returncode: refuse("LINE SPLIT REALIGN FAILED // REF ROLLBACK FAILED", 91)',
            '    refuse("LINE SPLIT REALIGN FAILED // REF ROLLED BACK", 90)',
            'print("OK\\t{}\\t{}\\t{}".format(expected_head, new_head, len(selected)))'
        ].join("\n");
    }

    function startExecutionProcess() {
        state = "LINE SPLIT // REHEARSING";
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
        const outputLines = out.split("\n");
        let control = "";

        for (let i = outputLines.length - 1; i >= 0; --i) {
            const line = String(outputLines[i] || "");

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
                + " LINE EDIT"
                + (String(fields[3] || "") === "1" ? "" : "S")
              )
            : (
                fields[0] === "REFUSED"
                ? fields.slice(1).join("\t")
                : String(
                    err
                    || out
                    || ("LINE SPLIT EXIT " + executeExitCode)
                  ).trim()
              );
        pendingNewHead =
            pendingExecutionSuccess
            ? String(fields[2] || "")
            : "";

        state = "LINE SPLIT // SNAPSHOT AFTER";
        snapshotPhase = "AFTER";
        pendingSnapshotRequest = snapshotService.capture(
            "HISTORY AFTER // SPLIT COMMIT LINES",
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
                    warning || "LINE SPLIT AFTER SNAPSHOT UNAVAILABLE"
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
                ? "LINE SPLIT // COMPLETE // SNAPSHOT WARNING"
                : "LINE SPLIT // COMPLETE";
            lastError = warning;
            headSha = newHead;
        } else {
            state = "LINE SPLIT // REFUSED";
            lastError = detail || "LINE SPLIT FAILED";
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
                        "LINE SPLIT REQUIRES CLEAN REF-RECOVERABLE STATE"
                    );
                    return;
                }

                root.pendingJournalId =
                    root.operationJournal.beginOperation(
                        "HISTORY/SPLIT_COMMIT_LINE",
                        snapshot,
                        root.journalContext()
                    );

                if (!root.pendingJournalId) {
                    root.failBeforeSnapshot(
                        "LINE SPLIT JOURNAL RECORD COULD NOT START"
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
