import QtQuick
import Quickshell
import Quickshell.Io

// Durable live interactive-rebase session controller.
//
// Git owns the actual rebase state under rebase-merge/rebase-apply.
// Post-Apollo persists only the identity needed to reconnect that Git state
// to its original plan and operation-journal record after a UI restart.
Scope {
    id: root

    property int schemaVersion: 1
    property string repositoryPath: ""
    property var operationJournal: null
    property var snapshotService: null

    property var storedSessions: []
    property bool storageLoaded: false

    property bool busy: false
    property bool refreshing: false
    property string state: "NONE"
    property string lastError: ""

    property bool active: false
    property bool foreignSession: false
    property string sessionId: ""
    property string journalOperationId: ""
    property string originalBranch: ""
    property string originalHead: ""
    property string baseSha: ""
    property string currentHead: ""
    property string stoppedSha: ""
    property var plan: []
    property bool mergePreserving: false
    property var conflictFiles: []
    property int progressCurrent: 0
    property int progressTotal: 0
    property int todoRemaining: 0
    property int doneCount: 0

    property var pendingStart: null
    property string pendingSnapshotRequest: ""
    property string snapshotPhase: ""
    property string pendingAction: ""
    property bool pendingFinalizeSuccess: false
    property string pendingFinalizeDetail: ""

    property bool startExitSeen: false
    property bool startStdoutSeen: false
    property bool startStderrSeen: false
    property int startExitCode: -1
    property string startStdout: ""
    property string startStderr: ""

    property bool inspectExitSeen: false
    property bool inspectStdoutSeen: false
    property bool inspectStderrSeen: false
    property int inspectExitCode: -1
    property string inspectStdout: ""
    property string inspectStderr: ""

    property bool actionExitSeen: false
    property bool actionStdoutSeen: false
    property bool actionStderrSeen: false
    property int actionExitCode: -1
    property string actionStdout: ""
    property string actionStderr: ""

    signal sessionChanged()
    signal sessionFinished(bool success, string detail)
    signal conflictHandoffRequested(var files)

    readonly property bool paused:
        active
        && (
            state === "PAUSED_EDIT"
            || state === "PAUSED"
            || state === "CONFLICT"
        )

    readonly property bool canContinue:
        active
        && !busy
        && state !== "UNCERTAIN"

    readonly property bool canSkip:
        active
        && !busy
        && state !== "UNCERTAIN"

    readonly property bool canAbort:
        active
        && !busy

    function nowIso() {
        return new Date().toISOString();
    }

    function cloneValue(value) {
        if (value === null || typeof value === "undefined")
            return null;

        try {
            return JSON.parse(JSON.stringify(value));
        } catch (error) {
            return null;
        }
    }

    function nextSessionId() {
        return "rebase-"
            + Date.now().toString(36)
            + "-"
            + Math.floor(Math.random() * 1679616).toString(36);
    }

    function sessionIndex(repo) {
        const needle = String(repo || "");

        for (let i = 0; i < storedSessions.length; ++i) {
            if (String((storedSessions[i] || {}).repository || "")
                    === needle)
                return i;
        }

        return -1;
    }

    function storedSession(repo) {
        const index = sessionIndex(repo);
        return index >= 0
            ? cloneValue(storedSessions[index] || {})
            : null;
    }

    function persistSessions() {
        sessionFile.setText(JSON.stringify({
            schemaVersion: schemaVersion,
            sessions: storedSessions
        }, null, 2));
    }

    function upsertSession(record) {
        const row = cloneValue(record || {}) || {};
        const repo = String(row.repository || "");

        if (!repo)
            return false;

        const next = storedSessions.slice();
        const index = sessionIndex(repo);

        if (index >= 0)
            next[index] = row;
        else
            next.unshift(row);

        storedSessions = next;
        persistSessions();
        return true;
    }

    function removeStoredSession(repo) {
        const needle = String(repo || "");
        const next = [];

        for (let i = 0; i < storedSessions.length; ++i) {
            const row = storedSessions[i] || {};
            if (String(row.repository || "") !== needle)
                next.push(row);
        }

        storedSessions = next;
        persistSessions();
    }

    function loadSessions() {
        const raw = String(sessionFile.text() || "").trim();

        if (!raw) {
            storedSessions = [];
            storageLoaded = true;
            Qt.callLater(refresh);
            return;
        }

        try {
            const parsed = JSON.parse(raw);
            storedSessions =
                parsed && Array.isArray(parsed.sessions)
                ? parsed.sessions
                : [];
        } catch (error) {
            storedSessions = [];
        }

        storageLoaded = true;
        Qt.callLater(refresh);
    }

    function clearVisibleState() {
        active = false;
        foreignSession = false;
        sessionId = "";
        journalOperationId = "";
        originalBranch = "";
        originalHead = "";
        baseSha = "";
        currentHead = "";
        stoppedSha = "";
        plan = [];
        mergePreserving = false;
        conflictFiles = [];
        progressCurrent = 0;
        progressTotal = 0;
        todoRemaining = 0;
        doneCount = 0;
    }

    function isEditSha(sha) {
        const needle = String(sha || "");

        for (let i = 0; i < plan.length; ++i) {
            const row = plan[i] || {};
            if (String(row.sha || "") === needle
                    && String(row.action || "").toLowerCase() === "edit")
                return true;
        }

        return false;
    }

    function start(base, branch, head, rows, preserveMerges) {
        if (busy || refreshing || active)
            return false;

        const repo = String(repositoryPath || "").trim();
        const targetBase = String(base || "").trim();
        const targetBranch = String(branch || "").trim();
        const targetHead = String(head || "").trim();
        const nextPlan = cloneValue(rows || []) || [];

        if (!repo
                || !targetBase
                || !targetBranch
                || !targetHead
                || nextPlan.length === 0) {
            lastError = "REBASE SESSION IDENTITY IS INCOMPLETE";
            state = "REFUSED";
            return false;
        }

        if (!operationJournal || !snapshotService) {
            lastError =
                "PERSISTENT REBASE REQUIRES JOURNAL + SNAPSHOT SERVICES";
            state = "REFUSED";
            return false;
        }

        if (storedSession(repo)) {
            lastError =
                "A PERSISTED REBASE SESSION ALREADY EXISTS FOR THIS REPOSITORY";
            state = "REFUSED";
            return false;
        }

        pendingStart = {
            id: nextSessionId(),
            repository: repo,
            originalBranch: targetBranch,
            originalHead: targetHead,
            baseSha: targetBase,
            mergePreserving: Boolean(preserveMerges),
            plan: nextPlan,
            startedAt: nowIso()
        };

        busy = true;
        state = "SNAPSHOT_BEFORE";
        lastError = "";
        pendingSnapshotRequest = snapshotService.capture(
            "HISTORY BEFORE // PERSISTENT REBASE SESSION",
            {
                source: "GitInteractiveRebaseSessionService",
                durableSession: true,
                sessionId: String(pendingStart.id || ""),
                branch: targetBranch,
                head: targetHead,
                baseSha: targetBase,
                mergePreserving: Boolean(preserveMerges),
                plan: cloneValue(nextPlan)
            }
        );
        snapshotPhase = "START_BEFORE";

        if (!pendingSnapshotRequest) {
            busy = false;
            snapshotPhase = "";
            pendingStart = null;
            lastError = "BEFORE SNAPSHOT COULD NOT START";
            state = "REFUSED";
            return false;
        }

        return true;
    }

    function startScript() {
        return [
            'import base64, json, os, shlex, shutil, stat, subprocess, sys, tempfile',
            'repo, base_sha, expected_head, branch, plan_json, preserve_arg = sys.argv[1:7]',
            'preserve_merges = preserve_arg == "1"',
            'def run(args, cwd=None, env=None):',
            '    return subprocess.run(args, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)',
            'def git(repo_path, *args, env=None): return run(["git", "-C", repo_path] + list(args), env=env)',
            'def text(proc): return proc.stdout.decode("utf-8", "surrogateescape").strip()',
            'def refuse(msg, code=1): print("REFUSED\\t" + msg); sys.exit(code)',
            'def gitdir(repo_path):',
            '    value = text(git(repo_path, "rev-parse", "--git-dir"))',
            '    return value if os.path.isabs(value) else os.path.join(repo_path, value)',
            'def rebase_active(repo_path):',
            '    gd = gitdir(repo_path)',
            '    return os.path.isdir(os.path.join(gd, "rebase-merge")) or os.path.isdir(os.path.join(gd, "rebase-apply"))',
            'def conflict_files(repo_path):',
            '    return [x for x in text(git(repo_path, "diff", "--name-only", "--diff-filter=U")).splitlines() if x]',
            'def stopped_sha(repo_path):',
            '    gd = gitdir(repo_path)',
            '    for name in ("rebase-merge", "rebase-apply"):',
            '        path = os.path.join(gd, name, "stopped-sha")',
            '        if os.path.isfile(path):',
            '            return open(path, "r", encoding="utf-8", errors="replace").read().strip()',
            '    return ""',
            'if git(repo, "rev-parse", "--is-inside-work-tree").returncode: refuse("NOT A GIT WORKTREE")',
            'if text(git(repo, "branch", "--show-current")) != branch: refuse("CURRENT BRANCH CHANGED SINCE ARM")',
            'if text(git(repo, "rev-parse", "HEAD")) != expected_head: refuse("HEAD CHANGED SINCE ARM")',
            'if git(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout.strip(): refuse("WORKTREE DIRTY SINCE ARM")',
            'if rebase_active(repo): refuse("REBASE ALREADY ACTIVE")',
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
            'allowed = {"pick", "reword", "squash", "fixup", "drop", "edit"}',
            'first_kept = None',
            'rehearsal_todo, live_todo, edit_shas = [], [], set()',
            'for row in rows:',
            '    sha = str(row.get("sha", "")); action = str(row.get("action", "")).lower(); subject = str(row.get("subject", "")).replace("\\n", " ").replace("\\r", " ")',
            '    if action not in allowed: refuse("UNSUPPORTED REBASE ACTION // " + action)',
            '    if action != "drop" and first_kept is None: first_kept = action',
            '    if first_kept in ("squash", "fixup"): refuse("FIRST KEPT COMMIT CANNOT SQUASH OR FIXUP")',
            '    if action == "reword":',
            '        message = str(row.get("message", "")).strip()',
            '        if not message: refuse("REWORD REQUIRES A NEW MESSAGE")',
            '        payload = base64.b64encode(message.encode("utf-8")).decode("ascii")',
            '        line = "pick {} {}".format(sha, subject)',
            '        exec_line = "exec sh -c \'printf %s {} | base64 -d | git commit --amend --no-verify -F -\'".format(payload)',
            '        rehearsal_todo.extend([line, exec_line]); live_todo.extend([line, exec_line])',
            '    elif action == "edit":',
            '        edit_shas.add(sha)',
            '        rehearsal_todo.append("pick {} {}".format(sha, subject))',
            '        live_todo.append("edit {} {}".format(sha, subject))',
            '    else:',
            '        line = "{} {} {}".format(action, sha, subject)',
            '        rehearsal_todo.append(line); live_todo.append(line)',
            'merge_editor = r"""',
            'import base64, json, os, sys',
            'todo_path = sys.argv[1]',
            'rows = json.loads(base64.b64decode(os.environ["PA_REBASE_PLAN64"]).decode("utf-8"))',
            'edit_mode = os.environ.get("PA_REBASE_EDIT_MODE", "live")',
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
            '            effective = "pick" if action == "reword" or (action == "edit" and edit_mode == "rehearsal") else action',
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
            'root = tempfile.mkdtemp(prefix="pa-rebase-session-")',
            'wt = os.path.join(root, "rehearsal")',
            'todo = os.path.join(root, "todo")',
            'editor = os.path.join(root, "sequence-editor")',
            'try:',
            '    add = git(repo, "worktree", "add", "--detach", wt, expected_head)',
            '    if add.returncode: refuse("REHEARSAL WORKTREE CREATE FAILED // " + add.stderr.decode("utf-8", "replace").strip())',
            '    env = dict(os.environ); env["GIT_EDITOR"] = ":"',
            '    if preserve_merges:',
            '        env["PA_REBASE_PLAN64"] = base64.b64encode(plan_json.encode("utf-8")).decode("ascii")',
            '        env["PA_REBASE_EDIT_MODE"] = "rehearsal"',
            '        env["GIT_SEQUENCE_EDITOR"] = "python3 -c " + shlex.quote(merge_editor)',
            '    else:',
            '        with open(editor, "w", encoding="utf-8") as handle: handle.write("#!/bin/sh\\ncp \\"$PA_REBASE_TODO\\" \\"$1\\"\\n")',
            '        os.chmod(editor, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)',
            '        with open(todo, "w", encoding="utf-8") as handle: handle.write("\\n".join(rehearsal_todo) + "\\n")',
            '        env["GIT_SEQUENCE_EDITOR"] = editor; env["PA_REBASE_TODO"] = todo',
            '    rebase_args = ["-c", "commit.gpgSign=false", "rebase", "-i"]',
            '    if preserve_merges: rebase_args.append("--rebase-merges")',
            '    rebase_args += ["--empty=keep", "--reapply-cherry-picks", base_sha]',
            '    rehearsal = git(wt, *rebase_args, env=env)',
            '    if rehearsal.returncode:',
            '        git(wt, "rebase", "--abort")',
            '        detail = rehearsal.stderr.decode("utf-8", "replace").strip() or rehearsal.stdout.decode("utf-8", "replace").strip()',
            '        refuse("REHEARSAL CONFLICT OR FAILURE // " + detail)',
            '    git(repo, "worktree", "remove", "--force", wt)',
            '    if text(git(repo, "branch", "--show-current")) != branch: refuse("CURRENT BRANCH CHANGED AFTER REHEARSAL")',
            '    if text(git(repo, "rev-parse", "HEAD")) != expected_head: refuse("HEAD CHANGED AFTER REHEARSAL")',
            '    if git(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout.strip(): refuse("WORKTREE CHANGED AFTER REHEARSAL")',
            '    if preserve_merges:',
            '        env["PA_REBASE_EDIT_MODE"] = "live"',
            '    else:',
            '        with open(todo, "w", encoding="utf-8") as handle: handle.write("\\n".join(live_todo) + "\\n")',
            '    live_args = ["-c", "commit.gpgSign=false", "rebase", "-i"]',
            '    if preserve_merges: live_args.append("--rebase-merges")',
            '    live_args += ["--empty=keep", "--reapply-cherry-picks", base_sha]',
            '    live = git(repo, *live_args, env=env)',
            '    if rebase_active(repo):',
            '        conflicts = conflict_files(repo)',
            '        stopped = stopped_sha(repo)',
            '        reason = "CONFLICT" if conflicts else ("EDIT" if stopped in edit_shas else "PAUSED")',
            '        print("PAUSED\\t{}\\t{}\\t{}".format(reason, text(git(repo, "rev-parse", "HEAD")), stopped))',
            '        sys.exit(0)',
            '    if live.returncode:',
            '        detail = live.stderr.decode("utf-8", "replace").strip() or live.stdout.decode("utf-8", "replace").strip()',
            '        refuse("LIVE REBASE FAILED // " + detail)',
            '    print("COMPLETE\\t{}\\t{}".format(expected_head, text(git(repo, "rev-parse", "HEAD"))))',
            'finally:',
            '    if os.path.isdir(wt): git(repo, "worktree", "remove", "--force", wt)',
            '    shutil.rmtree(root, ignore_errors=True)'
        ].join("\n");
    }

    function launchStartProcess() {
        const row = pendingStart || {};

        startExitSeen = false;
        startStdoutSeen = false;
        startStderrSeen = false;
        startExitCode = -1;
        startStdout = "";
        startStderr = "";
        state = "REHEARSING";

        startProcess.exec([
            "python3",
            "-c",
            startScript(),
            String(row.repository || repositoryPath || ""),
            String(row.baseSha || ""),
            String(row.originalHead || ""),
            String(row.originalBranch || ""),
            JSON.stringify(row.plan || []),
            Boolean(row.mergePreserving) ? "1" : "0"
        ]);
    }

    function maybeFinishStart() {
        if (!busy
                || !startExitSeen
                || !startStdoutSeen
                || !startStderrSeen)
            return;

        const out = String(startStdout || "").trim();
        const err = String(startStderr || "").trim();
        const lines = out.split("\n");
        let control = "";

        for (let i = lines.length - 1; i >= 0; --i) {
            const line = String(lines[i] || "");
            if (line.indexOf("PAUSED\t") === 0
                    || line.indexOf("COMPLETE\t") === 0
                    || line.indexOf("REFUSED\t") === 0) {
                control = line;
                break;
            }
        }

        const fields = control.split("\t");
        const kind = String(fields[0] || "");

        if (startExitCode === 0 && kind === "PAUSED") {
            busy = false;
            state =
                String(fields[1] || "") === "CONFLICT"
                ? "CONFLICT"
                : String(fields[1] || "") === "EDIT"
                ? "PAUSED_EDIT"
                : "PAUSED";
            currentHead = String(fields[2] || "");
            stoppedSha = String(fields[3] || "");
            pendingStart = null;
            refresh();
            return;
        }

        if (startExitCode === 0 && kind === "COMPLETE") {
            currentHead = String(fields[2] || "");
            pendingStart = null;
            beginFinalize(
                true,
                "PERSISTENT REBASE COMPLETED WITHOUT A PAUSE"
            );
            return;
        }

        const detail =
            kind === "REFUSED"
            ? fields.slice(1).join("\t")
            : String(err || out || ("REBASE START EXIT " + startExitCode)).trim();

        failRunningOperation(
            detail || "PERSISTENT REBASE START FAILED"
        );
    }

    function inspectScript() {
        return [
            'import os, subprocess, sys',
            'repo = sys.argv[1]',
            'def run(args): return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)',
            'def git(*args): return run(["git", "-C", repo] + list(args))',
            'def text(proc): return proc.stdout.decode("utf-8", "surrogateescape").strip()',
            'if git("rev-parse", "--is-inside-work-tree").returncode:',
            '    print("ERROR\\tNOT A GIT WORKTREE"); sys.exit(1)',
            'gd = text(git("rev-parse", "--git-dir"))',
            'if not os.path.isabs(gd): gd = os.path.join(repo, gd)',
            'rb = ""',
            'for name in ("rebase-merge", "rebase-apply"):',
            '    candidate = os.path.join(gd, name)',
            '    if os.path.isdir(candidate): rb = candidate; break',
            'branch = text(git("branch", "--show-current"))',
            'head = text(git("rev-parse", "HEAD"))',
            'reflog = text(git("reflog", "-1", "--format=%gs", "HEAD"))',
            'if not rb:',
            '    print("NONE\\t{}\\t{}\\t{}".format(branch, head, reflog)); sys.exit(0)',
            'def read_file(name):',
            '    path = os.path.join(rb, name)',
            '    if not os.path.isfile(path): return ""',
            '    return open(path, "r", encoding="utf-8", errors="replace").read().strip()',
            'head_name = read_file("head-name")',
            'saved_branch = head_name[len("refs/heads/"):] if head_name.startswith("refs/heads/") else head_name',
            'orig = read_file("orig-head")',
            'onto = read_file("onto")',
            'stopped = read_file("stopped-sha")',
            'msgnum = read_file("msgnum")',
            'end = read_file("end")',
            'def active_lines(name):',
            '    raw = read_file(name)',
            '    return [line for line in raw.splitlines() if line.strip() and not line.lstrip().startswith("#")]',
            'todo = active_lines("git-rebase-todo")',
            'done = active_lines("done")',
            'print("ACTIVE\\t{}\\t{}\\t{}\\t{}\\t{}\\t{}\\t{}\\t{}\\t{}\\t{}".format(saved_branch, orig, onto, head, stopped, msgnum or "0", end or "0", len(todo), len(done), reflog))',
            'for path in text(git("diff", "--name-only", "--diff-filter=U")).splitlines():',
            '    if path: print("CONFLICT\\t" + path)'
        ].join("\n");
    }

    function refresh() {
        const repo = String(repositoryPath || "").trim();

        if (!storageLoaded || refreshing || busy || !repo)
            return false;

        refreshing = true;
        inspectExitSeen = false;
        inspectStdoutSeen = false;
        inspectStderrSeen = false;
        inspectExitCode = -1;
        inspectStdout = "";
        inspectStderr = "";

        inspectProcess.exec([
            "python3",
            "-c",
            inspectScript(),
            repo
        ]);
        return true;
    }

    function maybeFinishInspect() {
        if (!refreshing
                || !inspectExitSeen
                || !inspectStdoutSeen
                || !inspectStderrSeen)
            return;

        refreshing = false;

        const out = String(inspectStdout || "").trim();
        const err = String(inspectStderr || "").trim();
        const lines = out.split("\n");
        let meta = null;
        const conflicts = [];

        for (let i = 0; i < lines.length; ++i) {
            const line = String(lines[i] || "");
            if (line.indexOf("ACTIVE\t") === 0
                    || line.indexOf("NONE\t") === 0)
                meta = line.split("\t");
            else if (line.indexOf("CONFLICT\t") === 0)
                conflicts.push(line.slice(9));
        }

        if (inspectExitCode !== 0 || !meta) {
            lastError =
                String(err || out || "REBASE SESSION INSPECTION FAILED").trim();
            state = "UNCERTAIN";
            sessionChanged();
            return;
        }

        const repo = String(repositoryPath || "");
        const saved = storedSession(repo);

        if (meta[0] === "ACTIVE") {
            active = true;
            foreignSession = !saved;
            conflictFiles = conflicts;
            originalBranch =
                saved
                ? String(saved.originalBranch || "")
                : String(meta[1] || "");
            originalHead =
                saved
                ? String(saved.originalHead || "")
                : String(meta[2] || "");
            baseSha =
                saved
                ? String(saved.baseSha || "")
                : String(meta[3] || "");
            currentHead = String(meta[4] || "");
            stoppedSha = String(meta[5] || "");
            progressCurrent = Number(meta[6] || 0);
            progressTotal = Number(meta[7] || 0);
            todoRemaining = Number(meta[8] || 0);
            doneCount = Number(meta[9] || 0);
            sessionId = saved ? String(saved.id || "") : "";
            journalOperationId =
                saved ? String(saved.journalOperationId || "") : "";
            plan = saved ? cloneValue(saved.plan || []) || [] : [];
            mergePreserving =
                saved ? Boolean(saved.mergePreserving) : false;

            if (saved
                    && String(meta[1] || "")
                       !== String(saved.originalBranch || "")) {
                state = "UNCERTAIN";
                lastError = "ACTIVE REBASE BRANCH DOES NOT MATCH STORED SESSION";
            } else if (conflicts.length > 0) {
                state = "CONFLICT";
                lastError = "";
            } else if (isEditSha(stoppedSha)) {
                state = "PAUSED_EDIT";
                lastError = "";
            } else {
                state = "PAUSED";
                lastError = "";
            }

            if (saved) {
                const updated = cloneValue(saved) || {};
                updated.lastKnownState = state;
                updated.currentHead = currentHead;
                updated.stoppedSha = stoppedSha;
                updated.progressCurrent = progressCurrent;
                updated.progressTotal = progressTotal;
                upsertSession(updated);
            }

            pendingAction = "";
            busy = false;
            sessionChanged();
            return;
        }

        active = false;
        conflictFiles = [];
        currentHead = String(meta[2] || "");
        stoppedSha = "";

        if (!saved) {
            clearVisibleState();
            state = "NONE";
            lastError = "";
            pendingAction = "";
            busy = false;
            sessionChanged();
            return;
        }

        sessionId = String(saved.id || "");
        journalOperationId = String(saved.journalOperationId || "");
        originalBranch = String(saved.originalBranch || "");
        originalHead = String(saved.originalHead || "");
        baseSha = String(saved.baseSha || "");
        plan = cloneValue(saved.plan || []) || [];
        mergePreserving = Boolean(saved.mergePreserving);

        const currentBranch = String(meta[1] || "");
        const reflog = String(meta[3] || "").toLowerCase();

        if (pendingAction === "abort"
                || reflog.indexOf("rebase (abort)") >= 0) {
            pendingAction = "";
            beginFinalize(false, "PERSISTENT REBASE ABORTED");
            return;
        }

        if (currentBranch === originalBranch
                && (
                    reflog.indexOf("rebase (finish)") >= 0
                    || currentHead !== originalHead
                )) {
            pendingAction = "";
            beginFinalize(true, "PERSISTENT REBASE COMPLETE");
            return;
        }

        state = "UNCERTAIN";
        lastError =
            "STORED REBASE SESSION EXISTS BUT GIT HAS NO ACTIVE REBASE";
        pendingAction = "";
        busy = false;
        sessionChanged();
    }

    function runAction(action, confirmed) {
        const op = String(action || "").toLowerCase();

        if (!active || busy || refreshing)
            return false;

        if (["continue", "skip", "abort"].indexOf(op) < 0)
            return false;

        if (op === "abort" && !confirmed) {
            lastError = "ABORT REQUIRES CONFIRMATION";
            return false;
        }

        busy = true;
        pendingAction = op;
        state = op === "abort"
            ? "ABORTING"
            : op === "skip"
            ? "SKIPPING"
            : "CONTINUING";
        lastError = "";

        actionExitSeen = false;
        actionStdoutSeen = false;
        actionStderrSeen = false;
        actionExitCode = -1;
        actionStdout = "";
        actionStderr = "";

        const command =
            op === "abort"
            ? ["git", "-C", repositoryPath, "rebase", "--abort"]
            : op === "skip"
            ? ["bash", "-lc", 'GIT_EDITOR=: git -C "$1" rebase --skip', "git-rebase-session-action", repositoryPath]
            : ["bash", "-lc", 'GIT_EDITOR=: git -C "$1" rebase --continue', "git-rebase-session-action", repositoryPath];

        actionProcess.exec(command);
        return true;
    }

    function continueSession() {
        return runAction("continue", true);
    }

    function skipSession() {
        return runAction("skip", true);
    }

    function abortSession(confirmed) {
        return runAction("abort", confirmed);
    }

    function requestConflictHandoff() {
        if (!active || conflictFiles.length === 0)
            return false;

        conflictHandoffRequested(cloneValue(conflictFiles) || []);
        return true;
    }

    function maybeFinishAction() {
        if (!busy
                || !actionExitSeen
                || !actionStdoutSeen
                || !actionStderrSeen)
            return;

        const detail =
            String(
                actionStderr
                || actionStdout
                || (
                    pendingAction.toUpperCase()
                    + " EXIT "
                    + actionExitCode
                )
            ).trim();

        if (actionExitCode !== 0)
            lastError = detail;

        busy = false;
        refresh();
    }

    function beginFinalize(success, detail) {
        if (busy && snapshotPhase === "FINAL_AFTER")
            return;

        pendingFinalizeSuccess = Boolean(success);
        pendingFinalizeDetail = String(detail || "");
        busy = true;
        state = success ? "FINALIZING" : "ABORTING";
        snapshotPhase = "FINAL_AFTER";

        if (!snapshotService) {
            finishFinalize(null, "AFTER SNAPSHOT SERVICE UNAVAILABLE");
            return;
        }

        pendingSnapshotRequest = snapshotService.capture(
            "HISTORY AFTER // PERSISTENT REBASE SESSION",
            {
                source: "GitInteractiveRebaseSessionService",
                durableSession: true,
                sessionId: sessionId,
                branch: originalBranch,
                originalHead: originalHead,
                baseSha: baseSha,
                mergePreserving: Boolean(mergePreserving),
                plan: cloneValue(plan)
            }
        );

        if (!pendingSnapshotRequest)
            finishFinalize(null, "AFTER SNAPSHOT COULD NOT START");
    }

    function finishFinalize(snapshot, warningText) {
        const warning = String(warningText || "");
        const after =
            snapshot
            || {
                snapshotVersion: 1,
                repository: String(repositoryPath || ""),
                capturedAt: nowIso(),
                captureFailed: true,
                recoveryClass: "EVIDENCE_ONLY",
                recoveryReason:
                    warning
                    || "PERSISTENT REBASE AFTER SNAPSHOT UNAVAILABLE"
            };
        const detail =
            pendingFinalizeDetail
            + (warning ? " // " + warning : "");
        const opId =
            String(journalOperationId || "");

        if (opId && operationJournal) {
            if (pendingFinalizeSuccess)
                operationJournal.completeOperation(
                    opId,
                    after,
                    detail
                );
            else
                operationJournal.failOperation(
                    opId,
                    after,
                    detail
                );
        }

        const success = pendingFinalizeSuccess;
        removeStoredSession(repositoryPath);
        clearVisibleState();
        busy = false;
        pendingSnapshotRequest = "";
        snapshotPhase = "";
        pendingFinalizeSuccess = false;
        pendingFinalizeDetail = "";
        state = success ? "COMPLETE" : "ABORTED";
        lastError = success ? warning : detail;
        sessionFinished(success, detail);
        sessionChanged();
    }

    function failRunningOperation(detail) {
        const message = String(detail || "PERSISTENT REBASE FAILED");
        const row = storedSession(repositoryPath);
        const opId =
            row
            ? String(row.journalOperationId || "")
            : String(journalOperationId || "");

        if (opId && operationJournal) {
            operationJournal.failOperation(
                opId,
                {
                    snapshotVersion: 1,
                    repository: String(repositoryPath || ""),
                    capturedAt: nowIso(),
                    captureFailed: true,
                    recoveryClass: "EVIDENCE_ONLY",
                    recoveryReason: message
                },
                message
            );
        }

        removeStoredSession(repositoryPath);
        clearVisibleState();
        pendingStart = null;
        busy = false;
        state = "REFUSED";
        lastError = message;
        sessionFinished(false, message);
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

            if (root.snapshotPhase === "START_BEFORE") {
                root.snapshotPhase = "";

                if (String((snapshot || {}).recoveryClass || "")
                        !== "REF_RECOVERABLE") {
                    root.busy = false;
                    root.pendingStart = null;
                    root.state = "REFUSED";
                    root.lastError =
                        "PERSISTENT REBASE REQUIRES CLEAN REF-RECOVERABLE STATE";
                    return;
                }

                const row = root.pendingStart || {};
                const metadata = {
                    source: "GitInteractiveRebaseSessionService",
                    operation: "INTERACTIVE_REBASE_SESSION",
                    durableSession: true,
                    sessionId: String(row.id || ""),
                    baseSha: String(row.baseSha || ""),
                    mergePreserving: Boolean(row.mergePreserving),
                    branch: String(row.originalBranch || ""),
                    head: String(row.originalHead || ""),
                    plan: root.cloneValue(row.plan || [])
                };
                const opId =
                    root.operationJournal.beginOperation(
                        "HISTORY/INTERACTIVE_REBASE_SESSION",
                        snapshot,
                        metadata
                    );

                if (!opId) {
                    root.busy = false;
                    root.pendingStart = null;
                    root.state = "REFUSED";
                    root.lastError =
                        "PERSISTENT REBASE JOURNAL RECORD COULD NOT START";
                    return;
                }

                row.journalOperationId = opId;
                row.lastKnownState = "STARTING";
                root.pendingStart = row;
                root.upsertSession(row);

                root.sessionId = String(row.id || "");
                root.journalOperationId = opId;
                root.originalBranch =
                    String(row.originalBranch || "");
                root.originalHead =
                    String(row.originalHead || "");
                root.baseSha = String(row.baseSha || "");
                root.mergePreserving = Boolean(row.mergePreserving);
                root.plan =
                    root.cloneValue(row.plan || []) || [];

                root.launchStartProcess();
                return;
            }

            if (root.snapshotPhase === "FINAL_AFTER") {
                root.snapshotPhase = "";
                root.finishFinalize(snapshot, "");
            }
        }

        function onSnapshotFailed(requestId, detail) {
            if (String(requestId || "")
                    !== String(root.pendingSnapshotRequest || ""))
                return;

            root.pendingSnapshotRequest = "";

            if (root.snapshotPhase === "START_BEFORE") {
                root.snapshotPhase = "";
                root.busy = false;
                root.pendingStart = null;
                root.state = "REFUSED";
                root.lastError =
                    "PERSISTENT REBASE BEFORE SNAPSHOT FAILED // "
                    + String(detail || "UNKNOWN ERROR");
                return;
            }

            if (root.snapshotPhase === "FINAL_AFTER") {
                root.snapshotPhase = "";
                root.finishFinalize(
                    null,
                    "AFTER SNAPSHOT FAILED // "
                        + String(detail || "UNKNOWN ERROR")
                );
            }
        }
    }

    Process {
        id: startProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.startStdout = this.text;
                root.startStdoutSeen = true;
                root.maybeFinishStart();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.startStderr = this.text;
                root.startStderrSeen = true;
                root.maybeFinishStart();
            }
        }

        onExited: function(code, exitStatus) {
            root.startExitCode = Number(code);
            root.startExitSeen = true;
            root.maybeFinishStart();
        }
    }

    Process {
        id: inspectProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.inspectStdout = this.text;
                root.inspectStdoutSeen = true;
                root.maybeFinishInspect();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.inspectStderr = this.text;
                root.inspectStderrSeen = true;
                root.maybeFinishInspect();
            }
        }

        onExited: function(code, exitStatus) {
            root.inspectExitCode = Number(code);
            root.inspectExitSeen = true;
            root.maybeFinishInspect();
        }
    }

    Process {
        id: actionProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.actionStdout = this.text;
                root.actionStdoutSeen = true;
                root.maybeFinishAction();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.actionStderr = this.text;
                root.actionStderrSeen = true;
                root.maybeFinishAction();
            }
        }

        onExited: function(code, exitStatus) {
            root.actionExitCode = Number(code);
            root.actionExitSeen = true;
            root.maybeFinishAction();
        }
    }

    FileView {
        id: sessionFile

        path: Qt.resolvedUrl("../../git-rebase-sessions.json")
        blockWrites: true
        atomicWrites: true
        printErrors: false

        onLoaded: root.loadSessions()
    }

    onRepositoryPathChanged: {
        if (storageLoaded)
            Qt.callLater(refresh);
    }
}
