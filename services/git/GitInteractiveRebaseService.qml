import QtQuick
import Quickshell
import Quickshell.Io

// Deterministic interactive-rebase engine.
//
// This first slice supports reorder + pick/reword/squash/fixup/drop. The exact
// plan is rehearsed in a temporary detached worktree. Only a successful
// rehearsal may atomically move the live branch ref, and the clean live
// worktree is then realigned to the rehearsed result.
//
// "edit" and live conflict continuation are intentionally not approximated:
// they require a later persistent rewrite-session model.
Scope {
    id: root

    property string repositoryPath: ""
    property var operationJournal: null
    property var snapshotService: null

    property bool previewBusy: false
    property bool executionBusy: false
    property string state: "READY"
    property string lastError: ""

    property string baseRef: ""
    property string baseSha: ""
    property string branchName: ""
    property string headSha: ""
    property var originalShas: []
    property var plan: []
    property bool mergePreserving: false
    property int mergeCommitCount: 0

    property bool armed: false
    property string armedBaseSha: ""
    property string armedHeadSha: ""
    property string armedBranch: ""
    property string armedPlanJson: ""
    property bool armedMergePreserving: false

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

    signal previewReady(var plan)
    signal executionFinished(bool success, string detail, string newHead)

    readonly property bool available:
        String(repositoryPath || "").trim().length > 0

    function allowedAction(value) {
        return [
            "pick",
            "reword",
            "squash",
            "fixup",
            "drop",
            "edit"
        ].indexOf(String(value || "").toLowerCase()) >= 0;
    }

    function clonePlan(value) {
        try {
            return JSON.parse(JSON.stringify(value || []));
        } catch (error) {
            return [];
        }
    }

    function disarm(reason) {
        armed = false;
        armedBaseSha = "";
        armedHeadSha = "";
        armedBranch = "";
        armedPlanJson = "";
        armedMergePreserving = false;

        if (reason)
            state = "REBASE // " + String(reason);
    }

    function clearPlan() {
        if (previewBusy || executionBusy)
            return false;

        baseRef = "";
        baseSha = "";
        branchName = "";
        headSha = "";
        originalShas = [];
        plan = [];
        mergePreserving = false;
        mergeCommitCount = 0;
        lastError = "";
        disarm("");
        state = "READY";
        return true;
    }

    function setAction(index, action) {
        const rowIndex = Number(index);
        const token = String(action || "").toLowerCase();

        if (executionBusy
                || rowIndex < 0
                || rowIndex >= plan.length
                || !allowedAction(token))
            return false;

        const next = clonePlan(plan);
        const row = next[rowIndex] || {};
        row.action = token;
        next[rowIndex] = row;
        plan = next;
        disarm("PLAN CHANGED");
        return true;
    }

    function setMessage(index, message) {
        const rowIndex = Number(index);

        if (executionBusy
                || rowIndex < 0
                || rowIndex >= plan.length)
            return false;

        const next = clonePlan(plan);
        const row = next[rowIndex] || {};
        row.message = String(message || "");
        next[rowIndex] = row;
        plan = next;
        disarm("PLAN CHANGED");
        return true;
    }

    function moveEntry(fromIndex, toIndex) {
        const source = Number(fromIndex);
        let target = Number(toIndex);

        if (mergePreserving) {
            lastError = "MERGE-PRESERVING TOPOLOGY LOCKED // REORDER DISABLED";
            state = "REBASE // TOPOLOGY LOCKED";
            return false;
        }

        if (executionBusy
                || source < 0
                || source >= plan.length
                || target < 0
                || target >= plan.length
                || source === target)
            return false;

        const next = clonePlan(plan);
        const row = next.splice(source, 1)[0];
        next.splice(target, 0, row);
        plan = next;
        disarm("PLAN CHANGED");
        return true;
    }

    function validatePlan() {
        if (!baseSha || !headSha || !branchName || plan.length === 0) {
            return {
                valid: false,
                reason: "REBASE PLAN IDENTITY IS INCOMPLETE"
            };
        }

        if (plan.length !== originalShas.length) {
            return {
                valid: false,
                reason: "REBASE PLAN COMMIT COUNT CHANGED"
            };
        }

        const expected = {};
        const seen = {};

        for (let i = 0; i < originalShas.length; ++i)
            expected[String(originalShas[i] || "")] = true;

        let firstKeptAction = "";

        for (let i = 0; i < plan.length; ++i) {
            const row = plan[i] || {};
            const sha = String(row.sha || "");
            const action = String(row.action || "").toLowerCase();

            if (!sha || !expected[sha] || seen[sha]) {
                return {
                    valid: false,
                    reason: "REBASE PLAN COMMIT SET CHANGED"
                };
            }

            seen[sha] = true;

            if (mergePreserving
                    && sha !== String(originalShas[i] || "")) {
                return {
                    valid: false,
                    reason: "MERGE-PRESERVING COMMIT ORDER IS TOPOLOGY LOCKED"
                };
            }

            if (!allowedAction(action)) {
                return {
                    valid: false,
                    reason: "UNSUPPORTED REBASE ACTION // " + action
                };
            }

            if (action === "reword"
                    && !String(row.message || "").trim()) {
                return {
                    valid: false,
                    reason: "REWORD REQUIRES A NEW MESSAGE"
                };
            }

            if (action !== "drop" && !firstKeptAction)
                firstKeptAction = action;

            if ((action === "squash" || action === "fixup")
                    && !firstKeptAction) {
                return {
                    valid: false,
                    reason: "FIRST KEPT COMMIT CANNOT SQUASH OR FIXUP"
                };
            }
        }

        if (firstKeptAction === "squash"
                || firstKeptAction === "fixup") {
            return {
                valid: false,
                reason: "FIRST KEPT COMMIT CANNOT SQUASH OR FIXUP"
            };
        }

        return {
            valid: true,
            reason: ""
        };
    }

    function preview(base) {
        if (previewBusy || executionBusy)
            return false;

        const repo = String(repositoryPath || "").trim();
        const target = String(base || "").trim();

        if (!repo || !target) {
            lastError =
                !repo
                ? "REBASE PREVIEW // NO REPOSITORY"
                : "REBASE PREVIEW // BASE REQUIRED";
            state = "REBASE // REFUSED";
            return false;
        }

        disarm("");
        previewBusy = true;
        state = "REBASE // READING RANGE";
        lastError = "";

        previewExitSeen = false;
        previewStdoutSeen = false;
        previewStderrSeen = false;
        previewExitCode = -1;
        previewStdout = "";
        previewStderr = "";

        previewProcess.exec([
            "bash",
            "-lc",
            [
                'repo="$1"',
                'base="$2"',
                'refuse() { printf "REFUSED\\t%s\\n" "$1"; exit 1; }',
                'git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1 || refuse "NOT A GIT WORKTREE"',
                '[ -z "$(git -C "$repo" status --porcelain=v1 --untracked-files=all 2>/dev/null)" ] || refuse "WORKTREE DIRTY // COMMIT OR STASH FIRST"',
                'branch="$(git -C "$repo" branch --show-current 2>/dev/null || true)"',
                '[ -n "$branch" ] || refuse "DETACHED HEAD"',
                'head="$(git -C "$repo" rev-parse HEAD 2>/dev/null || true)"',
                'base_sha="$(git -C "$repo" rev-parse "$base^{commit}" 2>/dev/null || true)"',
                '[ -n "$head" ] && [ -n "$base_sha" ] || refuse "BASE OR HEAD CANNOT BE RESOLVED"',
                '[ "$head" != "$base_sha" ] || refuse "BASE IS CURRENT HEAD"',
                'git -C "$repo" merge-base --is-ancestor "$base_sha" "$head" >/dev/null 2>&1 || refuse "BASE IS NOT AN ANCESTOR OF HEAD"',
                'gitdir="$(git -C "$repo" rev-parse --git-dir 2>/dev/null)"',
                'case "$gitdir" in /*) ;; *) gitdir="$repo/$gitdir" ;; esac',
                '[ ! -f "$gitdir/MERGE_HEAD" ] || refuse "MERGE IN PROGRESS"',
                '[ ! -d "$gitdir/rebase-merge" ] && [ ! -d "$gitdir/rebase-apply" ] || refuse "REBASE IN PROGRESS"',
                '[ ! -f "$gitdir/CHERRY_PICK_HEAD" ] || refuse "CHERRY-PICK IN PROGRESS"',
                '[ ! -f "$gitdir/REVERT_HEAD" ] || refuse "REVERT IN PROGRESS"',
                'merge_count="$(git -C "$repo" rev-list --count --merges "$base_sha..$head" 2>/dev/null || printf 0)"',
                'merge_mode=0; [ "$merge_count" -eq 0 ] || merge_mode=1',
                'printf "META\\t%s\\t%s\\t%s\\t%s\\t%s\\n" "$base_sha" "$branch" "$head" "$merge_mode" "$merge_count"',
                'git -C "$repo" log --reverse --no-merges --format="COMMIT%x09%H%x09%s" "$base_sha..$head"'
            ].join("\n"),
            "git-interactive-rebase-preview",
            repo,
            target
        ]);

        baseRef = target;
        return true;
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
        let meta = null;
        const rows = [];

        for (let i = 0; i < lines.length; ++i) {
            const line = String(lines[i] || "");

            if (line.indexOf("META\t") === 0) {
                meta = line.split("\t");
                continue;
            }

            if (line.indexOf("COMMIT\t") !== 0)
                continue;

            const fields = line.split("\t");
            const sha = fields.length > 1 ? fields[1] : "";
            const subject =
                fields.length > 2
                ? fields.slice(2).join("\t")
                : "";

            if (!sha)
                continue;

            rows.push({
                sha: sha,
                subject: subject,
                action: "pick",
                message: subject
            });
        }

        if (previewExitCode !== 0
                || !meta
                || meta.length < 6
                || rows.length === 0) {
            let refused = "";

            for (let i = 0; i < lines.length; ++i) {
                if (String(lines[i] || "").indexOf("REFUSED\t") === 0) {
                    refused = String(lines[i] || "").slice(8);
                    break;
                }
            }

            baseSha = "";
            branchName = "";
            headSha = "";
            originalShas = [];
            plan = [];
            mergePreserving = false;
            mergeCommitCount = 0;
            lastError =
                refused
                || String(err || out || ("PREVIEW EXIT " + previewExitCode)).trim()
                || "REBASE PREVIEW FAILED";
            state = "REBASE // REFUSED";
            return;
        }

        baseSha = String(meta[1] || "");
        branchName = String(meta[2] || "");
        headSha = String(meta[3] || "");
        mergePreserving = String(meta[4] || "0") === "1";
        mergeCommitCount = Number(meta[5] || 0);
        originalShas = rows.map(function(row) {
            return String((row || {}).sha || "");
        });
        plan = rows;
        lastError = "";
        state =
            mergePreserving
            ? (
                "REBASE // MERGE-PRESERVING PLAN READY // "
                + String(rows.length)
                + " EDITABLE COMMIT"
                + (rows.length === 1 ? "" : "S")
                + " // "
                + String(mergeCommitCount)
                + " MERGE"
                + (mergeCommitCount === 1 ? "" : "S")
                + " // TOPOLOGY LOCKED"
              )
            : (
                "REBASE // PLAN READY // "
                + String(rows.length)
                + " COMMIT"
                + (rows.length === 1 ? "" : "S")
              );
        previewReady(clonePlan(rows));
    }

    function arm() {
        if (previewBusy || executionBusy)
            return false;

        const validation = validatePlan();

        if (!validation.valid) {
            lastError = String(validation.reason || "REBASE PLAN INVALID");
            state = "REBASE // REFUSED";
            return false;
        }

        armedBaseSha = String(baseSha || "");
        armedHeadSha = String(headSha || "");
        armedBranch = String(branchName || "");
        armedPlanJson = JSON.stringify(plan);
        armedMergePreserving = Boolean(mergePreserving);
        armed = true;
        lastError = "";
        state = "REBASE // ARMED";
        return true;
    }

    function requiresPersistentSession() {
        for (let i = 0; i < plan.length; ++i) {
            if (String((plan[i] || {}).action || "").toLowerCase()
                    === "edit")
                return true;
        }

        return false;
    }

    function planStillArmed() {
        return armed
            && armedBaseSha === String(baseSha || "")
            && armedHeadSha === String(headSha || "")
            && armedBranch === String(branchName || "")
            && armedPlanJson === JSON.stringify(plan)
            && armedMergePreserving === Boolean(mergePreserving);
    }

    function journalContext() {
        return {
            source: "GitInteractiveRebaseService",
            operation: "INTERACTIVE_REBASE",
            baseRef: String(baseRef || ""),
            baseSha: String(armedBaseSha || ""),
            branch: String(armedBranch || ""),
            head: String(armedHeadSha || ""),
            mergePreserving: Boolean(armedMergePreserving),
            mergeCommitCount: Number(mergeCommitCount || 0),
            plan: clonePlan(plan)
        };
    }

    function executeArmed() {
        if (previewBusy || executionBusy || !planStillArmed())
            return false;

        if (requiresPersistentSession()) {
            lastError =
                "EDIT REQUIRES THE PERSISTENT REBASE SESSION ENGINE";
            state = "REBASE // SESSION REQUIRED";
            return false;
        }

        if ((operationJournal && !snapshotService)
                || (snapshotService && !operationJournal)) {
            lastError = "JOURNAL + SNAPSHOT SERVICES MUST BE PAIRED";
            state = "REBASE // REFUSED";
            return false;
        }

        executionBusy = true;
        pendingExecutionSuccess = false;
        pendingExecutionDetail = "";
        pendingNewHead = "";
        lastError = "";
        state =
            operationJournal && snapshotService
            ? "REBASE // SNAPSHOT BEFORE"
            : "REBASE // REHEARSING";

        executeExitSeen = false;
        executeStdoutSeen = false;
        executeStderrSeen = false;
        executeExitCode = -1;
        executeStdout = "";
        executeStderr = "";

        if (!operationJournal && !snapshotService)
            return startExecutionProcess();

        snapshotPhase = "BEFORE";
        pendingSnapshotRequest = snapshotService.capture(
            "HISTORY BEFORE // INTERACTIVE REBASE",
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
        lastError =
            "REBASE BEFORE SNAPSHOT FAILED // "
            + String(detail || "UNKNOWN ERROR");
        state = "REBASE // REFUSED";
        executionFinished(false, lastError, "");
    }

    function engineScript() {
        return [
            'import base64, json, os, shlex, shutil, stat, subprocess, sys, tempfile',
            'repo, base_sha, expected_head, branch, plan_json, preserve_arg = sys.argv[1:7]',
            'preserve_merges = preserve_arg == "1"',
            'def run(args, cwd=None, env=None, data=None):',
            '    return subprocess.run(args, cwd=cwd, env=env, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)',
            'def git(repo_path, *args, env=None): return run(["git", "-C", repo_path] + list(args), env=env)',
            'def text(proc): return proc.stdout.decode("utf-8", "surrogateescape").strip()',
            'def refuse(msg, code=1): print("REFUSED\\t" + msg); sys.exit(code)',
            'def active_state(repo_path):',
            '    gd = text(git(repo_path, "rev-parse", "--git-dir"))',
            '    if not os.path.isabs(gd): gd = os.path.join(repo_path, gd)',
            '    if os.path.isfile(os.path.join(gd, "MERGE_HEAD")): return "MERGE"',
            '    if os.path.isdir(os.path.join(gd, "rebase-merge")) or os.path.isdir(os.path.join(gd, "rebase-apply")): return "REBASE"',
            '    if os.path.isfile(os.path.join(gd, "CHERRY_PICK_HEAD")): return "CHERRY_PICK"',
            '    if os.path.isfile(os.path.join(gd, "REVERT_HEAD")): return "REVERT"',
            '    return "NONE"',
            'if git(repo, "rev-parse", "--is-inside-work-tree").returncode: refuse("NOT A GIT WORKTREE")',
            'if text(git(repo, "branch", "--show-current")) != branch: refuse("CURRENT BRANCH CHANGED SINCE ARM")',
            'if text(git(repo, "rev-parse", "HEAD")) != expected_head: refuse("HEAD CHANGED SINCE ARM")',
            'if git(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout.strip(): refuse("WORKTREE DIRTY SINCE ARM")',
            'if active_state(repo) != "NONE": refuse("GIT OPERATION STARTED SINCE ARM")',
            'if git(repo, "merge-base", "--is-ancestor", base_sha, expected_head).returncode: refuse("BASE NO LONGER ANCESTOR")',
            'has_merges = bool(git(repo, "rev-list", "--merges", base_sha + ".." + expected_head).stdout.strip())',
            'if has_merges != preserve_merges: refuse("MERGE TOPOLOGY CHANGED SINCE ARM")',
            'try: rows = json.loads(plan_json)',
            'except Exception: refuse("REBASE PLAN JSON INVALID")',
            'actual_args = ["rev-list", "--reverse"] + (["--no-merges"] if preserve_merges else []) + [base_sha + ".." + expected_head]',
            'actual = text(git(repo, *actual_args)).splitlines()',
            'planned = [str(row.get("sha", "")) for row in rows]',
            'if preserve_merges:',
            '    if planned != actual: refuse("MERGE-PRESERVING COMMIT ORDER OR SET CHANGED")',
            'elif len(planned) != len(actual) or set(planned) != set(actual): refuse("REBASE PLAN COMMIT SET CHANGED")',
            'allowed = {"pick", "reword", "squash", "fixup", "drop"}',
            'first_kept = None',
            'todo = []',
            'for row in rows:',
            '    sha = str(row.get("sha", "")); action = str(row.get("action", "")).lower(); subject = str(row.get("subject", "")).replace("\\n", " ").replace("\\r", " ")',
            '    if action not in allowed: refuse("UNSUPPORTED REBASE ACTION // " + action)',
            '    if action != "drop" and first_kept is None: first_kept = action',
            '    if first_kept in ("squash", "fixup"): refuse("FIRST KEPT COMMIT CANNOT SQUASH OR FIXUP")',
            '    if action == "reword":',
            '        message = str(row.get("message", "")).strip()',
            '        if not message: refuse("REWORD REQUIRES A NEW MESSAGE")',
            '        payload = base64.b64encode(message.encode("utf-8")).decode("ascii")',
            '        todo.append("pick {} {}".format(sha, subject))',
            '        todo.append("exec sh -c \'printf %s {} | base64 -d | git commit --amend --no-verify -F -\'".format(payload))',
            '    else: todo.append("{} {} {}".format(action, sha, subject))',
            'merge_editor = r"""',
            'import base64, json, os, sys',
            'todo_path = sys.argv[1]',
            'rows = json.loads(base64.b64decode(os.environ["PA_REBASE_PLAN64"]).decode("utf-8"))',
            'by_sha = {str(row.get("sha", "")): row for row in rows}',
            'seen = set()',
            'with open(todo_path, "r", encoding="utf-8", errors="replace") as handle:',
            '    lines = handle.read().splitlines()',
            'out = []',
            'for line in lines:',
            '    stripped = line.lstrip()',
            '    indent = line[:len(line) - len(stripped)]',
            '    parts = stripped.split(None, 2)',
            '    if len(parts) >= 2 and parts[0] in ("pick", "p"):',
            '        token = parts[1]',
            '        matches = [sha for sha in by_sha if sha.startswith(token)]',
            '        if len(matches) == 1:',
            '            sha = matches[0]; row = by_sha[sha]',
            '            action = str(row.get("action", "pick")).lower()',
            '            rest = parts[2] if len(parts) > 2 else str(row.get("subject", ""))',
            '            effective = "pick" if action == "reword" else action',
            '            out.append("{}{} {} {}".format(indent, effective, token, rest))',
            '            if action == "reword":',
            '                message = str(row.get("message", "")).strip()',
            '                payload = base64.b64encode(message.encode("utf-8")).decode("ascii")',
            '                out.append("exec sh -c \'printf %s {} | base64 -d | git commit --amend --no-verify -F -\'".format(payload))',
            '            seen.add(sha)',
            '            continue',
            '    out.append(line)',
            'missing = [sha for sha in by_sha if sha not in seen]',
            'if missing:',
            '    print("MERGE-PRESERVING TODO LOST COMMITS // " + ",".join(missing), file=sys.stderr)',
            '    sys.exit(94)',
            'with open(todo_path, "w", encoding="utf-8") as handle:',
            '    handle.write("\\n".join(out) + "\\n")',
            '"""',
            'root = tempfile.mkdtemp(prefix="pa-interactive-rebase-")',
            'wt = os.path.join(root, "worktree")',
            'todo_path = os.path.join(root, "todo")',
            'editor_path = os.path.join(root, "sequence-editor")',
            'try:',
            '    add = git(repo, "worktree", "add", "--detach", wt, expected_head)',
            '    if add.returncode: refuse("REHEARSAL WORKTREE CREATE FAILED // " + add.stderr.decode("utf-8", "replace").strip())',
            '    env = dict(os.environ); env["GIT_EDITOR"] = ":"',
            '    if preserve_merges:',
            '        env["PA_REBASE_PLAN64"] = base64.b64encode(plan_json.encode("utf-8")).decode("ascii")',
            '        env["GIT_SEQUENCE_EDITOR"] = "python3 -c " + shlex.quote(merge_editor)',
            '    else:',
            '        with open(todo_path, "w", encoding="utf-8") as handle: handle.write("\\n".join(todo) + "\\n")',
            '        with open(editor_path, "w", encoding="utf-8") as handle: handle.write("#!/bin/sh\\ncp \\"$PA_REBASE_TODO\\" \\"$1\\"\\n")',
            '        os.chmod(editor_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)',
            '        env["GIT_SEQUENCE_EDITOR"] = editor_path; env["PA_REBASE_TODO"] = todo_path',
            '    rebase_args = ["-c", "commit.gpgSign=false", "rebase", "-i"]',
            '    if preserve_merges: rebase_args.append("--rebase-merges")',
            '    rebase_args += ["--empty=keep", "--reapply-cherry-picks", base_sha]',
            '    rehearse = git(wt, *rebase_args, env=env)',
            '    if rehearse.returncode:',
            '        git(wt, "rebase", "--abort")',
            '        detail = rehearse.stderr.decode("utf-8", "replace").strip() or rehearse.stdout.decode("utf-8", "replace").strip()',
            '        refuse("REHEARSAL CONFLICT OR FAILURE // " + detail)',
            '    new_head = text(git(wt, "rev-parse", "HEAD"))',
            '    if not new_head: refuse("REHEARSAL PRODUCED NO HEAD")',
            'finally:',
            '    git(repo, "worktree", "remove", "--force", wt)',
            '    shutil.rmtree(root, ignore_errors=True)',
            'if text(git(repo, "branch", "--show-current")) != branch: refuse("CURRENT BRANCH CHANGED AFTER REHEARSAL")',
            'if text(git(repo, "rev-parse", "HEAD")) != expected_head: refuse("HEAD CHANGED AFTER REHEARSAL")',
            'if git(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout.strip(): refuse("WORKTREE CHANGED AFTER REHEARSAL")',
            'ref = "refs/heads/" + branch',
            'git(repo, "update-ref", "ORIG_HEAD", expected_head)',
            'move = git(repo, "update-ref", ref, new_head, expected_head)',
            'if move.returncode: refuse("GUARDED BRANCH UPDATE FAILED")',
            'align = git(repo, "reset", "--hard", new_head)',
            'if align.returncode:',
            '    rollback = git(repo, "update-ref", ref, expected_head, new_head)',
            '    git(repo, "reset", "--hard", expected_head)',
            '    if rollback.returncode: refuse("WORKTREE REALIGN FAILED // REF ROLLBACK FAILED", 91)',
            '    refuse("WORKTREE REALIGN FAILED // REF ROLLED BACK", 90)',
            'print("OK\\t{}\\t{}\\t{}".format(expected_head, new_head, len(rows)))'
        ].join("\n");
    }

    function startExecutionProcess() {
        if (!executionBusy)
            return false;

        state = "REBASE // REHEARSING";

        executionProcess.exec([
            "python3",
            "-c",
            engineScript(),
            String(repositoryPath || ""),
            String(armedBaseSha || ""),
            String(armedHeadSha || ""),
            String(armedBranch || ""),
            String(armedPlanJson || ""),
            armedMergePreserving ? "1" : "0"
        ]);

        return true;
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
            : String(err || out || ("REBASE EXIT " + executeExitCode)).trim();
        pendingNewHead =
            pendingExecutionSuccess
            ? String(fields[2] || "")
            : "";

        if (!operationJournal || !snapshotService) {
            finalizeExecution(null, "");
            return;
        }

        state = "REBASE // SNAPSHOT AFTER";
        snapshotPhase = "AFTER";
        pendingSnapshotRequest = snapshotService.capture(
            "HISTORY AFTER // INTERACTIVE REBASE",
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
                recoveryReason:
                    warning || "REBASE AFTER SNAPSHOT UNAVAILABLE"
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
                ? "REBASE // COMPLETE // SNAPSHOT WARNING"
                : "REBASE // COMPLETE";
            lastError = warning;
            headSha = pendingNewHead;
            disarm("");
        } else {
            state = "REBASE // REFUSED";
            lastError = detail || "INTERACTIVE REBASE FAILED";
            disarm("");
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
                        "REBASE REQUIRES CLEAN REF-RECOVERABLE STATE"
                    );
                    return;
                }

                root.pendingJournalId =
                    root.operationJournal.beginOperation(
                        "HISTORY/INTERACTIVE_REBASE",
                        snapshot,
                        root.journalContext()
                    );

                if (root.operationJournal
                        && !root.pendingJournalId) {
                    root.failBeforeSnapshot(
                        "JOURNAL RECORD COULD NOT START"
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
        id: executionProcess

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
