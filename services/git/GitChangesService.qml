import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property string repositoryPath: ""

    property bool refreshing: false
    property bool actionBusy: false
    property bool previewBusy: false
    property bool hunkBusy: false

    property string actionName: ""
    property string actionStatus: "READY"
    property string lastError: ""

    property var files: []
    property var stashes: []
    property var conflicts: []
    property var hunks: []

    property int stagedCount: 0
    property int unstagedCount: 0
    property int untrackedCount: 0
    property int conflictCount: 0

    property string currentBranch: ""
    property string upstreamBranch: ""
    property int upstreamAhead: 0
    property int upstreamBehind: 0
    property string headSha: ""
    property string headSubject: ""
    property var headTrailers: []
    property int stagedInsertions: 0
    property int stagedDeletions: 0
    property int stagedBinaryFiles: 0
    property bool signingDefault: false
    property string signingKey: ""
    property string signingFormat: "openpgp"
    property string hooksPath: ""
    property var commitHooks: []
    property string commitTemplate: ""

    property string operationState: "NONE"

    property string previewPath: ""
    property string previewText: "SELECT A CHANGED FILE"
    property string previewMode: "combined"

    property string hunkPath: ""
    property string hunkMode: "worktree"
    property string hunkHeader: ""

    property bool inspectExitSeen: false
    property bool inspectStdoutSeen: false
    property bool inspectStderrSeen: false
    property int inspectExitCode: -1
    property string inspectStdoutText: ""
    property string inspectStderrText: ""

    property bool actionExitSeen: false
    property bool actionStdoutSeen: false
    property bool actionStderrSeen: false
    property int actionExitCode: -1
    property string actionStdoutText: ""
    property string actionStderrText: ""

    property bool previewExitSeen: false
    property bool previewStdoutSeen: false
    property bool previewStderrSeen: false
    property int previewExitCode: -1
    property string previewStdoutText: ""
    property string previewStderrText: ""

    property bool hunkExitSeen: false
    property bool hunkStdoutSeen: false
    property bool hunkStderrSeen: false
    property int hunkExitCode: -1
    property string hunkStdoutText: ""
    property string hunkStderrText: ""

    signal refreshed()
    signal actionFinished(string action, bool success, string detail)

    readonly property bool available:
        String(repositoryPath || "").trim().length > 0

    readonly property int changedCount: files.length

    function fileAt(index) {
        if (index < 0 || index >= files.length)
            return null;
        return files[index];
    }

    function stashAt(index) {
        if (index < 0 || index >= stashes.length)
            return null;
        return stashes[index];
    }

    function hunkAt(index) {
        if (index < 0 || index >= hunks.length)
            return null;
        return hunks[index];
    }

    function statusLabel(indexStatus, worktreeStatus) {
        if (indexStatus === "?" && worktreeStatus === "?")
            return "NEW";
        if (indexStatus === "R" || worktreeStatus === "R")
            return "RENAMED";
        if (indexStatus === "C" || worktreeStatus === "C")
            return "COPIED";
        if (indexStatus === "D" || worktreeStatus === "D")
            return "DELETED";
        if (indexStatus === "A")
            return "ADDED";
        if (indexStatus === "U" || worktreeStatus === "U"
                || indexStatus + worktreeStatus === "AA"
                || indexStatus + worktreeStatus === "DD")
            return "CONFLICT";
        if (indexStatus === "M" || worktreeStatus === "M")
            return "MODIFIED";
        return "CHANGED";
    }

    function isConflictStatus(x, y) {
        const pair = String(x || " ") + String(y || " ");
        return x === "U"
            || y === "U"
            || pair === "AA"
            || pair === "DD"
            || pair === "AU"
            || pair === "UA"
            || pair === "DU"
            || pair === "UD";
    }

    function refresh() {
        const repo = String(repositoryPath || "").trim();

        if (refreshing || actionBusy)
            return false;

        if (!repo) {
            files = [];
            stashes = [];
            conflicts = [];
            hunks = [];
            stagedCount = 0;
            unstagedCount = 0;
            untrackedCount = 0;
            conflictCount = 0;
            currentBranch = "";
            upstreamBranch = "";
            upstreamAhead = 0;
            upstreamBehind = 0;
            headSha = "";
            headSubject = "";
            headTrailers = [];
            stagedInsertions = 0;
            stagedDeletions = 0;
            stagedBinaryFiles = 0;
            signingDefault = false;
            signingKey = "";
            signingFormat = "openpgp";
            hooksPath = "";
            commitHooks = [];
            commitTemplate = "";
            operationState = "NONE";
            lastError = "NO REPOSITORY";
            return false;
        }

        refreshing = true;
        lastError = "";

        inspectExitSeen = false;
        inspectStdoutSeen = false;
        inspectStderrSeen = false;
        inspectExitCode = -1;
        inspectStdoutText = "";
        inspectStderrText = "";

        inspectProcess.exec([
            "bash",
            "-lc",
            [
                'repo="$1"',
                'if ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then',
                '  printf "ERROR\\tNOT A GIT WORKTREE\\n"',
                '  exit 21',
                'fi',
                'gitdir="$(git -C "$repo" rev-parse --git-dir 2>/dev/null)"',
                'case "$gitdir" in /*) ;; *) gitdir="$repo/$gitdir" ;; esac',
                'state="NONE"',
                'if [ -f "$gitdir/MERGE_HEAD" ]; then state="MERGE";',
                'elif [ -d "$gitdir/rebase-merge" ] || [ -d "$gitdir/rebase-apply" ]; then state="REBASE";',
                'elif [ -f "$gitdir/CHERRY_PICK_HEAD" ]; then state="CHERRY_PICK";',
                'elif [ -f "$gitdir/REVERT_HEAD" ]; then state="REVERT";',
                'elif [ -f "$gitdir/BISECT_LOG" ]; then state="BISECT"; fi',
                'printf "STATE\\t%s\\n" "$state"',
                'branch="$(git -C "$repo" branch --show-current 2>/dev/null || true)"',
                'printf "BRANCH\\t%s\\n" "$branch"',
                'upstream="$(git -C "$repo" rev-parse --abbrev-ref --symbolic-full-name "@{upstream}" 2>/dev/null || true)"',
                'printf "UPSTREAM\\t%s\\n" "$upstream"',
                'behind=0; ahead=0',
                'if [ -n "$upstream" ]; then read -r behind ahead < <(git -C "$repo" rev-list --left-right --count "$upstream"...HEAD 2>/dev/null || printf "0 0"); fi',
                'printf "AHEADBEHIND\\t%s\\t%s\\n" "$ahead" "$behind"',
                'if git -C "$repo" rev-parse --verify HEAD >/dev/null 2>&1; then',
                '  git -C "$repo" log -1 --format="HEAD%x09%H%x09%s" HEAD',
                'else',
                '  printf "HEAD\\t\\tNO COMMITS YET\\n"',
                'fi',
                'if git -C "$repo" rev-parse --verify HEAD >/dev/null 2>&1; then',
                '  git -C "$repo" log -1 --format=%B HEAD | git interpret-trailers --parse | while IFS= read -r trailer; do',
                '    [ -n "$trailer" ] && printf "HEADTRAILER\\t%s\\n" "$trailer"',
                '  done',
                'fi',
                "git -C \"$repo\" diff --cached --numstat 2>/dev/null | awk 'BEGIN{a=0;d=0;b=0} $1==\"-\" || $2==\"-\" {b++; next} {a+=$1; d+=$2} END{printf \"STAGEDSTAT\\\\t%d\\\\t%d\\\\t%d\\\\n\",a,d,b}'",
                'sign_default="$(git -C "$repo" config --bool commit.gpgSign 2>/dev/null || true)"',
                'sign_key="$(git -C "$repo" config user.signingkey 2>/dev/null || true)"',
                'sign_format="$(git -C "$repo" config gpg.format 2>/dev/null || true)"',
                '[ -n "$sign_format" ] || sign_format="openpgp"',
                'printf "SIGNING\\t%s\\t%s\\t%s\\n" "$sign_default" "$sign_key" "$sign_format"',
                'hooks_dir="$(git -C "$repo" rev-parse --git-path hooks 2>/dev/null || true)"',
                'case "$hooks_dir" in /*) ;; "") ;; *) hooks_dir="$repo/$hooks_dir" ;; esac',
                'printf "HOOKSPATH\\t%s\\n" "$hooks_dir"',
                'for hook in pre-commit prepare-commit-msg commit-msg post-commit; do',
                '  [ -n "$hooks_dir" ] && [ -x "$hooks_dir/$hook" ] && printf "HOOK\\t%s\\n" "$hook"',
                'done',
                'template="$(git -C "$repo" config --path commit.template 2>/dev/null || true)"',
                'printf "TEMPLATE\\t%s\\n" "$template"',
                'git -C "$repo" status --porcelain=v1 --untracked-files=all | while IFS= read -r line; do',
                '  printf "STATUS\\t%s\\n" "$line"',
                'done',
                'git -C "$repo" stash list --format="STASH%x09%gd%x09%H%x09%ct%x09%gs" 2>/dev/null || true'
            ].join("\n"),
            "git-changes-inspect",
            repo
        ]);

        return true;
    }

    function parseInspection(text) {
        const rows = [];
        const stashRows = [];
        const conflictRows = [];
        let staged = 0;
        let unstaged = 0;
        let untracked = 0;
        let state = "NONE";
        let branch = "";
        let upstream = "";
        let ahead = 0;
        let behind = 0;
        let nextHeadSha = "";
        let nextHeadSubject = "";
        const nextHeadTrailers = [];
        let insertions = 0;
        let deletions = 0;
        let binaryFiles = 0;
        let defaultSigning = false;
        let nextSigningKey = "";
        let nextSigningFormat = "openpgp";
        let nextHooksPath = "";
        const nextCommitHooks = [];
        let nextCommitTemplate = "";

        const lines = String(text || "").split("\n");

        for (let i = 0; i < lines.length; ++i) {
            const line = String(lines[i] || "");
            if (!line)
                continue;

            if (line.indexOf("STATE\t") === 0) {
                state = line.slice(6).trim() || "NONE";
                continue;
            }

            if (line.indexOf("BRANCH\t") === 0) {
                branch = line.slice(7).trim();
                continue;
            }

            if (line.indexOf("UPSTREAM\t") === 0) {
                upstream = line.slice(9).trim();
                continue;
            }

            if (line.indexOf("AHEADBEHIND\t") === 0) {
                const p = line.split("\t");
                ahead = p.length > 1 ? Number(p[1] || 0) : 0;
                behind = p.length > 2 ? Number(p[2] || 0) : 0;
                continue;
            }

            if (line.indexOf("HEAD\t") === 0) {
                const p = line.split("\t");
                nextHeadSha = p.length > 1 ? p[1] : "";
                nextHeadSubject =
                    p.length > 2 ? p.slice(2).join("\t") : "";
                continue;
            }

            if (line.indexOf("HEADTRAILER\t") === 0) {
                const trailer = line.slice(12).trim();
                if (trailer)
                    nextHeadTrailers.push(trailer);
                continue;
            }

            if (line.indexOf("STAGEDSTAT\t") === 0) {
                const p = line.split("\t");
                insertions = p.length > 1 ? Number(p[1] || 0) : 0;
                deletions = p.length > 2 ? Number(p[2] || 0) : 0;
                binaryFiles = p.length > 3 ? Number(p[3] || 0) : 0;
                continue;
            }

            if (line.indexOf("SIGNING\t") === 0) {
                const p = line.split("\t");
                defaultSigning =
                    String(p.length > 1 ? p[1] : "").toLowerCase()
                    === "true";
                nextSigningKey = p.length > 2 ? p[2] : "";
                nextSigningFormat =
                    (p.length > 3 ? p[3] : "") || "openpgp";
                continue;
            }

            if (line.indexOf("HOOKSPATH\t") === 0) {
                nextHooksPath = line.slice(10).trim();
                continue;
            }

            if (line.indexOf("HOOK\t") === 0) {
                const hook = line.slice(5).trim();
                if (hook)
                    nextCommitHooks.push(hook);
                continue;
            }

            if (line.indexOf("TEMPLATE\t") === 0) {
                nextCommitTemplate = line.slice(9).trim();
                continue;
            }

            if (line.indexOf("STASH\t") === 0) {
                const p = line.split("\t");
                stashRows.push({
                    ref: p.length > 1 ? p[1] : "",
                    sha: p.length > 2 ? p[2] : "",
                    epoch: p.length > 3 ? Number(p[3] || 0) : 0,
                    message: p.length > 4 ? p.slice(4).join("\t") : ""
                });
                continue;
            }

            if (line.indexOf("STATUS\t") !== 0)
                continue;

            const raw = line.slice(7);
            if (raw.length < 3)
                continue;

            const x = raw.charAt(0);
            const y = raw.charAt(1);
            let pathText = raw.slice(3);
            let originalPath = "";

            const arrow = pathText.indexOf(" -> ");
            if (arrow >= 0) {
                originalPath = pathText.slice(0, arrow);
                pathText = pathText.slice(arrow + 4);
            }

            const isUntracked = x === "?" && y === "?";
            const isStaged = !isUntracked && x !== " ";
            const isUnstaged = isUntracked || y !== " ";
            const isConflict = isConflictStatus(x, y);

            if (isStaged)
                staged += 1;
            if (isUnstaged)
                unstaged += 1;
            if (isUntracked)
                untracked += 1;

            const row = {
                path: pathText,
                originalPath: originalPath,
                indexStatus: x,
                worktreeStatus: y,
                staged: isStaged,
                unstaged: isUnstaged,
                untracked: isUntracked,
                conflict: isConflict,
                label: statusLabel(x, y)
            };

            rows.push(row);

            if (isConflict)
                conflictRows.push(row);
        }

        files = rows;
        stashes = stashRows;
        conflicts = conflictRows;
        stagedCount = staged;
        unstagedCount = unstaged;
        untrackedCount = untracked;
        conflictCount = conflictRows.length;
        currentBranch = branch;
        upstreamBranch = upstream;
        upstreamAhead = ahead;
        upstreamBehind = behind;
        headSha = nextHeadSha;
        headSubject = nextHeadSubject;
        headTrailers = nextHeadTrailers;
        stagedInsertions = insertions;
        stagedDeletions = deletions;
        stagedBinaryFiles = binaryFiles;
        signingDefault = defaultSigning;
        signingKey = nextSigningKey;
        signingFormat = nextSigningFormat;
        hooksPath = nextHooksPath;
        commitHooks = nextCommitHooks;
        commitTemplate = nextCommitTemplate;
        operationState = state;

        if (previewPath) {
            let stillExists = false;
            for (let i = 0; i < rows.length; ++i) {
                if (String(rows[i].path || "") === previewPath) {
                    stillExists = true;
                    break;
                }
            }

            if (!stillExists) {
                previewPath = "";
                previewText = rows.length > 0
                    ? "SELECT A CHANGED FILE"
                    : "WORKTREE CLEAN";
                hunks = [];
                hunkPath = "";
            }
        } else if (rows.length === 0) {
            previewText = "WORKTREE CLEAN";
        }
    }

    function maybeFinishInspection() {
        if (!refreshing
                || !inspectExitSeen
                || !inspectStdoutSeen
                || !inspectStderrSeen)
            return;

        refreshing = false;

        if (inspectExitCode !== 0) {
            lastError = String(
                inspectStderrText
                || inspectStdoutText
                || ("STATUS EXIT " + inspectExitCode)
            ).trim();
            return;
        }

        parseInspection(inspectStdoutText);
        lastError = "";
        refreshed();
    }

    function preview(path, mode) {
        const repo = String(repositoryPath || "").trim();
        const target = String(path || "").trim();
        const requestedMode = String(mode || previewMode || "combined");

        if (!repo || !target || previewBusy)
            return false;

        previewBusy = true;
        previewPath = target;
        previewMode = requestedMode;
        previewText = "READING DIFF // " + target;

        previewExitSeen = false;
        previewStdoutSeen = false;
        previewStderrSeen = false;
        previewExitCode = -1;
        previewStdoutText = "";
        previewStderrText = "";

        previewProcess.exec([
            "bash",
            "-lc",
            [
                'repo="$1"',
                'path="$2"',
                'mode="$3"',
                'case "$mode" in',
                '  staged)',
                '    git -C "$repo" diff --cached --stat -- "$path"',
                '    git -C "$repo" diff --cached --no-ext-diff -- "$path"',
                '    ;;',
                '  worktree)',
                '    git -C "$repo" diff --stat -- "$path"',
                '    git -C "$repo" diff --no-ext-diff -- "$path"',
                '    if ! git -C "$repo" ls-files --error-unmatch -- "$path" >/dev/null 2>&1 && [ -f "$repo/$path" ]; then',
                '      git diff --no-index -- /dev/null "$repo/$path" 2>/dev/null || true',
                '    fi',
                '    ;;',
                '  word)',
                '    git -C "$repo" diff --cached --word-diff=color -- "$path" 2>/dev/null || true',
                '    git -C "$repo" diff --word-diff=color -- "$path" 2>/dev/null || true',
                '    ;;',
                '  *)',
                '    printf "=== STAGED ========================================\\n"',
                '    git -C "$repo" diff --cached --no-ext-diff -- "$path" 2>/dev/null || true',
                '    printf "\\n=== WORKTREE ======================================\\n"',
                '    git -C "$repo" diff --no-ext-diff -- "$path" 2>/dev/null || true',
                '    if ! git -C "$repo" ls-files --error-unmatch -- "$path" >/dev/null 2>&1 && [ -f "$repo/$path" ]; then',
                '      printf "\\n=== UNTRACKED =====================================\\n"',
                '      git diff --no-index -- /dev/null "$repo/$path" 2>/dev/null || true',
                '    fi',
                '    ;;',
                'esac'
            ].join("\n"),
            "git-changes-preview",
            repo,
            target,
            requestedMode
        ]);

        return true;
    }

    function previewStash(ref) {
        const repo = String(repositoryPath || "").trim();
        const target = String(ref || "").trim();

        if (!repo || !target || previewBusy)
            return false;

        previewBusy = true;
        previewPath = target;
        previewMode = "stash";
        previewText = "READING STASH // " + target;

        previewExitSeen = false;
        previewStdoutSeen = false;
        previewStderrSeen = false;
        previewExitCode = -1;
        previewStdoutText = "";
        previewStderrText = "";

        previewProcess.exec([
            "bash",
            "-lc",
            'git -C "$1" stash show --stat -p "$2" 2>/dev/null || true',
            "git-stash-preview",
            repo,
            target
        ]);

        return true;
    }

    function maybeFinishPreview() {
        if (!previewBusy
                || !previewExitSeen
                || !previewStdoutSeen
                || !previewStderrSeen)
            return;

        previewBusy = false;

        const out = String(previewStdoutText || "").trim();
        const err = String(previewStderrText || "").trim();

        previewText = out || err || "NO TEXT DIFF // " + previewPath;
    }

    function loadHunks(path, mode) {
        const repo = String(repositoryPath || "").trim();
        const target = String(path || "").trim();
        const requestedMode = String(mode || "worktree");

        if (!repo || !target || hunkBusy)
            return false;

        hunkBusy = true;
        hunkPath = target;
        hunkMode = requestedMode;
        hunks = [];
        hunkHeader = "";

        hunkExitSeen = false;
        hunkStdoutSeen = false;
        hunkStderrSeen = false;
        hunkExitCode = -1;
        hunkStdoutText = "";
        hunkStderrText = "";

        hunkProcess.exec([
            "bash",
            "-lc",
            [
                'repo="$1"',
                'path="$2"',
                'mode="$3"',
                'if [ "$mode" = "staged" ]; then',
                '  git -C "$repo" diff --cached --no-ext-diff --binary -- "$path"',
                'else',
                '  git -C "$repo" diff --no-ext-diff --binary -- "$path"',
                'fi'
            ].join("\n"),
            "git-changes-hunks",
            repo,
            target,
            requestedMode
        ]);

        return true;
    }

    function parseHunks(text) {
        const sourceLines = String(text || "").split("\n");
        const header = [];
        const rows = [];
        let current = null;
        let oldLine = 0;
        let newLine = 0;

        for (let i = 0; i < sourceLines.length; ++i) {
            const line = sourceLines[i];

            if (line.indexOf("@@") === 0) {
                if (current)
                    rows.push(current);

                const match = line.match(
                    /^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@/
                );

                oldLine = match ? Number(match[1] || 0) : 0;
                newLine = match ? Number(match[3] || 0) : 0;

                current = {
                    index: rows.length,
                    header: line,
                    text: line + "\n",
                    added: 0,
                    removed: 0,
                    lines: []
                };
                continue;
            }

            if (!current) {
                header.push(line);
                continue;
            }

            current.text += line + "\n";

            const kind =
                line.length > 0
                ? line.charAt(0)
                : " ";
            const payload =
                line.length > 0
                ? line.slice(1)
                : "";
            const patchIndex = current.lines.length;

            if (kind === "+") {
                current.lines.push({
                    patchIndex: patchIndex,
                    kind: "+",
                    text: payload,
                    oldLine: 0,
                    newLine: newLine,
                    selectable: true
                });
                current.added += 1;
                newLine += 1;
            } else if (kind === "-") {
                current.lines.push({
                    patchIndex: patchIndex,
                    kind: "-",
                    text: payload,
                    oldLine: oldLine,
                    newLine: 0,
                    selectable: true
                });
                current.removed += 1;
                oldLine += 1;
            } else if (kind === " ") {
                current.lines.push({
                    patchIndex: patchIndex,
                    kind: " ",
                    text: payload,
                    oldLine: oldLine,
                    newLine: newLine,
                    selectable: false
                });
                oldLine += 1;
                newLine += 1;
            } else {
                current.lines.push({
                    patchIndex: patchIndex,
                    kind: kind,
                    text: payload,
                    oldLine: 0,
                    newLine: 0,
                    selectable: false
                });
            }
        }

        if (current)
            rows.push(current);

        hunkHeader = header.join("\n");
        hunks = rows;
    }

    function maybeFinishHunks() {
        if (!hunkBusy
                || !hunkExitSeen
                || !hunkStdoutSeen
                || !hunkStderrSeen)
            return;

        hunkBusy = false;

        if (hunkExitCode !== 0) {
            lastError = String(
                hunkStderrText
                || hunkStdoutText
                || ("HUNK EXIT " + hunkExitCode)
            ).trim();
            hunks = [];
            return;
        }

        lastError = "";
        parseHunks(hunkStdoutText);
    }

    function runAction(operation, a, b, c, d) {
        const repo = String(repositoryPath || "").trim();
        const op = String(operation || "").trim();

        if (!repo || !op || actionBusy || refreshing)
            return false;

        actionBusy = true;
        actionName = op.toUpperCase();
        actionStatus = actionName + " // RUNNING";
        lastError = "";

        actionExitSeen = false;
        actionStdoutSeen = false;
        actionStderrSeen = false;
        actionExitCode = -1;
        actionStdoutText = "";
        actionStderrText = "";

        actionProcess.exec([
            "bash",
            "-lc",
            [
                'repo="$1"',
                'op="$2"',
                'a="$3"',
                'b="$4"',
                'c="$5"',
                'd="$6"',
                'if ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then',
                '  printf "REFUSED\\tNOT A GIT WORKTREE\\n"',
                '  exit 21',
                'fi',
                'case "$op" in',
                '  stage)',
                '    [ -n "$a" ] || { printf "REFUSED\\tNO FILE SELECTED\\n"; exit 22; }',
                '    git -C "$repo" add -- "$a" || exit $?',
                '    printf "OK\\tSTAGED // %s\\n" "$a"',
                '    ;;',
                '  unstage)',
                '    [ -n "$a" ] || { printf "REFUSED\\tNO FILE SELECTED\\n"; exit 23; }',
                '    git -C "$repo" restore --staged -- "$a" 2>/dev/null || git -C "$repo" reset -q HEAD -- "$a" || exit $?',
                '    printf "OK\\tUNSTAGED // %s\\n" "$a"',
                '    ;;',
                '  stage-all)',
                '    git -C "$repo" add -A || exit $?',
                '    printf "OK\\tSTAGED ALL CHANGES\\n"',
                '    ;;',
                '  unstage-all)',
                '    git -C "$repo" restore --staged . 2>/dev/null || git -C "$repo" reset -q HEAD -- . || exit $?',
                '    printf "OK\\tUNSTAGED ALL CHANGES\\n"',
                '    ;;',
                '  commit)',
                '    message="$a"; amend="$b"; commit_opts="$c"; allow_empty="$d"',
                '    sign_arg=""',
                '    verify_arg=""',
                '    case ":$commit_opts:" in *:sign:*) sign_arg="-S" ;; esac',
                '    case ":$commit_opts:" in *:no-verify:*) verify_arg="--no-verify" ;; esac',
                '    if [ "$amend" = "1" ]; then',
                '      if [ -n "$message" ]; then',
                '        git -C "$repo" commit --amend $sign_arg $verify_arg -m "$message" || exit $?',
                '      else',
                '        git -C "$repo" commit --amend $sign_arg $verify_arg --no-edit || exit $?',
                '      fi',
                '      printf "OK\\tAMENDED HEAD\\n"',
                '    else',
                '      [ -n "$message" ] || { printf "REFUSED\\tCOMMIT MESSAGE REQUIRED\\n"; exit 24; }',
                '      if [ "$allow_empty" = "1" ]; then',
                '        git -C "$repo" commit $sign_arg $verify_arg --allow-empty -m "$message" || exit $?',
                '      else',
                '        if git -C "$repo" diff --cached --quiet --exit-code; then',
                '          printf "REFUSED\\tNO STAGED CHANGES\\n"',
                '          exit 25',
                '        fi',
                '        git -C "$repo" commit $sign_arg $verify_arg -m "$message" || exit $?',
                '      fi',
                '      printf "OK\\tCOMMITTED // %s\\n" "$message"',
                '    fi',
                '    ;;',
                '  stash)',
                '    message="$a"; mode="$b"',
                '    if [ -z "$(git -C "$repo" status --porcelain=v1 2>/dev/null)" ]; then',
                '      printf "REFUSED\\tWORKTREE CLEAN\\n"',
                '      exit 26',
                '    fi',
                '    [ -n "$message" ] || message="Post-Apollo stash"',
                '    case "$mode" in',
                '      staged) git -C "$repo" stash push --staged -m "$message" || exit $? ;;',
                '      keep-index) git -C "$repo" stash push -u --keep-index -m "$message" || exit $? ;;',
                '      all|"") git -C "$repo" stash push -u -m "$message" || exit $? ;;',
                '      *) printf "REFUSED\\tUNKNOWN STASH MODE // %s\\n" "$mode"; exit 26 ;;',
                '    esac',
                '    printf "OK\\tSTASHED %s // %s\\n" "${mode:-all}" "$message"',
                '    ;;',
                '  stash-apply)',
                '    [ -n "$a" ] || { printf "REFUSED\\tSTASH REF REQUIRED\\n"; exit 27; }',
                '    if [ "$b" = "index" ]; then',
                '      git -C "$repo" stash apply --index "$a" || exit $?',
                '    else',
                '      git -C "$repo" stash apply "$a" || exit $?',
                '    fi',
                '    printf "OK\\tAPPLIED // %s\\n" "$a"',
                '    ;;',
                '  stash-pop)',
                '    ref="$a"; [ -n "$ref" ] || ref="stash@{0}"',
                '    git -C "$repo" rev-parse --verify "$ref" >/dev/null 2>&1 || { printf "REFUSED\\tSTASH NOT FOUND // %s\\n" "$ref"; exit 28; }',
                '    if [ "$b" = "index" ]; then',
                '      git -C "$repo" stash pop --index "$ref" || exit $?',
                '    else',
                '      git -C "$repo" stash pop "$ref" || exit $?',
                '    fi',
                '    printf "OK\\tPOPPED // %s\\n" "$ref"',
                '    ;;',
                '  stash-drop)',
                '    [ "$b" = "CONFIRM" ] || { printf "REFUSED\\tDROP REQUIRES CONFIRMATION\\n"; exit 29; }',
                '    [ -n "$a" ] || { printf "REFUSED\\tSTASH REF REQUIRED\\n"; exit 30; }',
                '    git -C "$repo" stash drop "$a" || exit $?',
                '    printf "OK\\tDROPPED // %s\\n" "$a"',
                '    ;;',
                '  discard-file)',
                '    [ "$b" = "CONFIRM" ] || { printf "REFUSED\\tDISCARD REQUIRES CONFIRMATION\\n"; exit 31; }',
                '    [ -n "$a" ] || { printf "REFUSED\\tFILE REQUIRED\\n"; exit 32; }',
                '    if git -C "$repo" ls-files --error-unmatch -- "$a" >/dev/null 2>&1; then',
                '      git -C "$repo" restore --worktree -- "$a" || exit $?',
                '    else',
                '      git -C "$repo" clean -f -- "$a" >/dev/null 2>&1 || exit $?',
                '    fi',
                '    printf "OK\\tDISCARDED WORKTREE COPY // %s\\n" "$a"',
                '    ;;',
                '  resolve-ours)',
                '    git -C "$repo" checkout --ours -- "$a" || exit $?',
                '    git -C "$repo" add -- "$a" || exit $?',
                '    printf "OK\\tRESOLVED OURS // %s\\n" "$a"',
                '    ;;',
                '  resolve-theirs)',
                '    git -C "$repo" checkout --theirs -- "$a" || exit $?',
                '    git -C "$repo" add -- "$a" || exit $?',
                '    printf "OK\\tRESOLVED THEIRS // %s\\n" "$a"',
                '    ;;',
                '  mark-resolved)',
                '    git -C "$repo" add -- "$a" || exit $?',
                '    printf "OK\\tMARKED RESOLVED // %s\\n" "$a"',
                '    ;;',
                '  continue-operation)',
                '    state="$a"',
                '    case "$state" in',
                '      MERGE) GIT_EDITOR=true git -C "$repo" commit --no-edit || exit $? ;;',
                '      REBASE) GIT_EDITOR=true git -C "$repo" rebase --continue || exit $? ;;',
                '      CHERRY_PICK) GIT_EDITOR=true git -C "$repo" cherry-pick --continue || exit $? ;;',
                '      REVERT) GIT_EDITOR=true git -C "$repo" revert --continue || exit $? ;;',
                '      *) printf "REFUSED\\tNO CONTINUABLE OPERATION\\n"; exit 33 ;;',
                '    esac',
                '    printf "OK\\tCONTINUED // %s\\n" "$state"',
                '    ;;',
                '  abort-operation)',
                '    [ "$b" = "CONFIRM" ] || { printf "REFUSED\\tABORT REQUIRES CONFIRMATION\\n"; exit 34; }',
                '    state="$a"',
                '    case "$state" in',
                '      MERGE) git -C "$repo" merge --abort || exit $? ;;',
                '      REBASE) git -C "$repo" rebase --abort || exit $? ;;',
                '      CHERRY_PICK) git -C "$repo" cherry-pick --abort || exit $? ;;',
                '      REVERT) git -C "$repo" revert --abort || exit $? ;;',
                '      *) printf "REFUSED\\tNO ABORTABLE OPERATION\\n"; exit 35 ;;',
                '    esac',
                '    printf "OK\\tABORTED // %s\\n" "$state"',
                '    ;;',
                '  skip-operation)',
                '    state="$a"',
                '    case "$state" in',
                '      REBASE) GIT_EDITOR=true git -C "$repo" rebase --skip || exit $? ;;',
                '      CHERRY_PICK) GIT_EDITOR=true git -C "$repo" cherry-pick --skip || exit $? ;;',
                '      REVERT) GIT_EDITOR=true git -C "$repo" revert --skip || exit $? ;;',
                '      *) printf "REFUSED\\tNO SKIPPABLE OPERATION\\n"; exit 35 ;;',
                '    esac',
                '    printf "OK\\tSKIPPED CURRENT STEP // %s\\n" "$state"',
                '    ;;',
                '  stage-line|unstage-line|discard-line)',
                '    [ -n "$a" ] || { printf "REFUSED\\tFILE REQUIRED\\n"; exit 40; }',
                '    [ -n "$b" ] || { printf "REFUSED\\tHUNK INDEX REQUIRED\\n"; exit 41; }',
                '    [ -n "$c" ] || { printf "REFUSED\\tLINE INDEX REQUIRED\\n"; exit 42; }',
                '    if [ "$op" = "discard-line" ] && [ "$d" != "CONFIRM" ]; then',
                '      printf "REFUSED\\tLINE DISCARD REQUIRES CONFIRMATION\\n"',
                '      exit 43',
                '    fi',
                '    python3 - "$repo" "$a" "$op" "$b" "$c" <<\'PY\'',
                'import difflib, os, re, subprocess, sys',
                'repo, path, op, hunk_text, line_text = sys.argv[1:6]',
                'hunk_index = int(hunk_text)',
                'line_index = int(line_text)',
                '',
                'def run(cmd):',
                '    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)',
                '',
                'def git_bytes(args):',
                '    p = run(["git", "-C", repo] + args)',
                '    if p.returncode != 0:',
                '        return None',
                '    return p.stdout',
                '',
                'def split_bytes(data):',
                '    if data is None:',
                '        return []',
                '    return data.decode("utf-8", "surrogateescape").splitlines(True)',
                '',
                'if op == "unstage-line":',
                '    diff_args = ["diff", "--cached", "--no-ext-diff", "--", path]',
                'else:',
                '    diff_args = ["diff", "--no-ext-diff", "--", path]',
                '',
                'diff_proc = run(["git", "-C", repo] + diff_args)',
                'if diff_proc.returncode != 0:',
                '    sys.stderr.buffer.write(diff_proc.stderr)',
                '    sys.exit(diff_proc.returncode)',
                '',
                'diff_lines = diff_proc.stdout.decode("utf-8", "surrogateescape").splitlines(True)',
                'hunks, current = [], None',
                'for raw in diff_lines:',
                '    if raw.startswith("@@"):',
                '        if current is not None:',
                '            hunks.append(current)',
                '        current = [raw]',
                '    elif current is not None:',
                '        current.append(raw)',
                'if current is not None:',
                '    hunks.append(current)',
                '',
                'if hunk_index < 0 or hunk_index >= len(hunks):',
                '    print("HUNK NOT FOUND", file=sys.stderr)',
                '    sys.exit(44)',
                '',
                'hunk = hunks[hunk_index]',
                'body = hunk[1:]',
                'if line_index < 0 or line_index >= len(body):',
                '    print("LINE NOT FOUND", file=sys.stderr)',
                '    sys.exit(45)',
                '',
                'selected = body[line_index]',
                'if not selected or selected[0] not in "+-":',
                '    print("LINE IS NOT A CHANGE", file=sys.stderr)',
                '    sys.exit(46)',
                '',
                'match = re.match(r"^@@ -(\\d+)(?:,(\\d+))? \\+(\\d+)(?:,(\\d+))? @@", hunk[0])',
                'if not match:',
                '    print("HUNK HEADER INVALID", file=sys.stderr)',
                '    sys.exit(47)',
                '',
                'old_cursor = int(match.group(1))',
                'new_cursor = int(match.group(3))',
                'selected_old = 0',
                'selected_new = 0',
                '',
                'for idx, raw in enumerate(body):',
                '    prefix = raw[:1]',
                '    if idx == line_index:',
                '        selected_old = old_cursor',
                '        selected_new = new_cursor',
                '        break',
                '    if prefix == " ":',
                '        old_cursor += 1',
                '        new_cursor += 1',
                '    elif prefix == "-":',
                '        old_cursor += 1',
                '    elif prefix == "+":',
                '        new_cursor += 1',
                '',
                'if op == "stage-line":',
                '    base = split_bytes(git_bytes(["show", ":" + path]))',
                '    if not base and git_bytes(["ls-files", "--error-unmatch", "--", path]) is None:',
                '        print("UNTRACKED FILE // STAGE WHOLE FILE FIRST", file=sys.stderr)',
                '        sys.exit(48)',
                '    target = list(base)',
                '    apply_cached = True',
                '    pos = max(0, selected_old - 1)',
                '    if selected[0] == "+":',
                '        target.insert(min(pos, len(target)), selected[1:])',
                '    else:',
                '        if pos >= len(target):',
                '            print("SOURCE LINE OUT OF RANGE", file=sys.stderr)',
                '            sys.exit(49)',
                '        target.pop(pos)',
                'elif op == "unstage-line":',
                '    base = split_bytes(git_bytes(["show", ":" + path]))',
                '    target = list(base)',
                '    apply_cached = True',
                '    pos = max(0, selected_new - 1)',
                '    if selected[0] == "+":',
                '        if pos >= len(target):',
                '            print("INDEX LINE OUT OF RANGE", file=sys.stderr)',
                '            sys.exit(50)',
                '        target.pop(pos)',
                '    else:',
                '        target.insert(min(pos, len(target)), selected[1:])',
                'else:',
                '    full_path = os.path.join(repo, path)',
                '    try:',
                '        with open(full_path, "rb") as fh:',
                '            base = split_bytes(fh.read())',
                '    except FileNotFoundError:',
                '        base = []',
                '    target = list(base)',
                '    apply_cached = False',
                '    pos = max(0, selected_new - 1)',
                '    if selected[0] == "+":',
                '        if pos >= len(target):',
                '            print("WORKTREE LINE OUT OF RANGE", file=sys.stderr)',
                '            sys.exit(51)',
                '        target.pop(pos)',
                '    else:',
                '        target.insert(min(pos, len(target)), selected[1:])',
                '',
                'from_name = "a/" + path',
                'to_name = "b/" + path',
                'patch = "".join(difflib.unified_diff(base, target, fromfile=from_name, tofile=to_name, n=3))',
                'if not patch:',
                '    print("NO LINE PATCH PRODUCED", file=sys.stderr)',
                '    sys.exit(52)',
                '',
                'apply_cmd = ["git", "-C", repo, "apply", "--whitespace=nowarn"]',
                'if apply_cached:',
                '    apply_cmd.append("--cached")',
                'apply_cmd.append("-")',
                'result = subprocess.run(apply_cmd, input=patch.encode("utf-8", "surrogateescape"), stdout=subprocess.PIPE, stderr=subprocess.PIPE)',
                'sys.stdout.buffer.write(result.stdout)',
                'sys.stderr.buffer.write(result.stderr)',
                'sys.exit(result.returncode)',
                'PY',
                '    rc=$?',
                '    [ "$rc" -eq 0 ] || exit "$rc"',
                '    printf "OK\\t%s // %s // HUNK %s // LINE %s\\n" "$op" "$a" "$b" "$c"',
                '    ;;',
                '  stage-hunk|unstage-hunk|discard-hunk)',
                '    [ -n "$a" ] || { printf "REFUSED\\tFILE REQUIRED\\n"; exit 36; }',
                '    [ -n "$b" ] || { printf "REFUSED\\tHUNK INDEX REQUIRED\\n"; exit 37; }',
                '    if [ "$op" = "discard-hunk" ] && [ "$c" != "CONFIRM" ]; then',
                '      printf "REFUSED\\tHUNK DISCARD REQUIRES CONFIRMATION\\n"',
                '      exit 38',
                '    fi',
                '    python3 - "$repo" "$a" "$op" "$b" <<\'PY\'',
                'import subprocess, sys',
                'repo, path, op, idx_text = sys.argv[1:5]',
                'idx = int(idx_text)',
                'cached = op == "unstage-hunk"',
                'cmd = ["git", "-C", repo, "diff", "--no-ext-diff", "--binary"]',
                'if cached: cmd.append("--cached")',
                'cmd += ["--", path]',
                'proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)',
                'if proc.returncode != 0:',
                '    sys.stderr.buffer.write(proc.stderr); sys.exit(proc.returncode)',
                'text = proc.stdout.decode("utf-8", "surrogateescape").splitlines(True)',
                'header, hunks, current = [], [], None',
                'for line in text:',
                '    if line.startswith("@@"):',
                '        if current is not None: hunks.append(current)',
                '        current = [line]',
                '    elif current is None:',
                '        header.append(line)',
                '    else:',
                '        current.append(line)',
                'if current is not None: hunks.append(current)',
                'if idx < 0 or idx >= len(hunks):',
                '    print("HUNK NOT FOUND", file=sys.stderr); sys.exit(39)',
                'patch = "".join(header + hunks[idx]).encode("utf-8", "surrogateescape")',
                'apply = ["git", "-C", repo, "apply", "--whitespace=nowarn"]',
                'if op == "stage-hunk": apply.append("--cached")',
                'elif op == "unstage-hunk": apply += ["--cached", "-R"]',
                'elif op == "discard-hunk": apply.append("-R")',
                'apply.append("-")',
                'result = subprocess.run(apply, input=patch, stdout=subprocess.PIPE, stderr=subprocess.PIPE)',
                'sys.stdout.buffer.write(result.stdout)',
                'sys.stderr.buffer.write(result.stderr)',
                'sys.exit(result.returncode)',
                'PY',
                '    rc=$?',
                '    [ "$rc" -eq 0 ] || exit "$rc"',
                '    printf "OK\\t%s // %s // HUNK %s\\n" "$op" "$a" "$b"',
                '    ;;',
                '  *)',
                '    printf "REFUSED\\tUNKNOWN OPERATION // %s\\n" "$op"',
                '    exit 90',
                '    ;;',
                'esac'
            ].join("\n"),
            "git-changes-action",
            repo,
            op,
            String(a || ""),
            String(b || ""),
            String(c || ""),
            String(d || "")
        ]);

        return true;
    }

    function stage(path) {
        return runAction("stage", path, "", "", "");
    }

    function unstage(path) {
        return runAction("unstage", path, "", "", "");
    }

    function stageAll() {
        return runAction("stage-all", "", "", "", "");
    }

    function unstageAll() {
        return runAction("unstage-all", "", "", "", "");
    }

    function commit(message, amend, sign, allowEmpty, noVerify) {
        const options = [];
        if (sign)
            options.push("sign");
        if (noVerify)
            options.push("no-verify");

        return runAction(
            "commit",
            String(message || "").trim(),
            amend ? "1" : "0",
            options.join(":"),
            allowEmpty ? "1" : "0"
        );
    }

    function stash(message, mode) {
        return runAction(
            "stash",
            String(message || "").trim(),
            String(mode || "all"),
            "",
            ""
        );
    }

    function applyStash(ref, restoreIndex) {
        return runAction(
            "stash-apply",
            ref,
            restoreIndex ? "index" : "",
            "",
            ""
        );
    }

    function popStash(ref, restoreIndex) {
        return runAction(
            "stash-pop",
            ref || "stash@{0}",
            restoreIndex ? "index" : "",
            "",
            ""
        );
    }

    function dropStash(ref, confirmed) {
        return runAction(
            "stash-drop",
            ref,
            confirmed ? "CONFIRM" : "",
            "",
            ""
        );
    }

    function discardFile(path, confirmed) {
        return runAction(
            "discard-file",
            path,
            confirmed ? "CONFIRM" : "",
            "",
            ""
        );
    }

    function resolveOurs(path) {
        return runAction("resolve-ours", path, "", "", "");
    }

    function resolveTheirs(path) {
        return runAction("resolve-theirs", path, "", "", "");
    }

    function markResolved(path) {
        return runAction("mark-resolved", path, "", "", "");
    }

    function continueOperation() {
        return runAction(
            "continue-operation",
            operationState,
            "",
            "",
            ""
        );
    }

    function abortOperation(confirmed) {
        return runAction(
            "abort-operation",
            operationState,
            confirmed ? "CONFIRM" : "",
            "",
            ""
        );
    }

    function skipOperation() {
        return runAction(
            "skip-operation",
            operationState,
            "",
            "",
            ""
        );
    }

    function stageLine(path, hunkIndex, lineIndex) {
        return runAction(
            "stage-line",
            path,
            String(hunkIndex),
            String(lineIndex),
            ""
        );
    }

    function unstageLine(path, hunkIndex, lineIndex) {
        return runAction(
            "unstage-line",
            path,
            String(hunkIndex),
            String(lineIndex),
            ""
        );
    }

    function discardLine(path, hunkIndex, lineIndex, confirmed) {
        return runAction(
            "discard-line",
            path,
            String(hunkIndex),
            String(lineIndex),
            confirmed ? "CONFIRM" : ""
        );
    }

    function stageHunk(path, index) {
        return runAction(
            "stage-hunk",
            path,
            String(index),
            "",
            ""
        );
    }

    function unstageHunk(path, index) {
        return runAction(
            "unstage-hunk",
            path,
            String(index),
            "",
            ""
        );
    }

    function discardHunk(path, index, confirmed) {
        return runAction(
            "discard-hunk",
            path,
            String(index),
            confirmed ? "CONFIRM" : "",
            ""
        );
    }

    function maybeFinishAction() {
        if (!actionBusy
                || !actionExitSeen
                || !actionStdoutSeen
                || !actionStderrSeen)
            return;

        actionBusy = false;

        const out = String(actionStdoutText || "").trim();
        const err = String(actionStderrText || "").trim();
        const lines = out.split("\n");
        let controlLine = "";

        for (let i = lines.length - 1; i >= 0; --i) {
            const line = String(lines[i] || "");
            if (line.indexOf("OK\t") === 0
                    || line.indexOf("REFUSED\t") === 0) {
                controlLine = line;
                break;
            }
        }

        const parts = controlLine.split("\t");
        const kind = parts.length > 0 ? parts[0] : "";
        const detail =
            parts.length > 1
            ? parts.slice(1).join("\t")
            : String(err || out || ("EXIT " + actionExitCode)).trim();

        if (actionExitCode === 0 && kind === "OK") {
            actionStatus = detail || (actionName + " // OK");
            lastError = "";
            actionFinished(actionName, true, detail || "OK");
            refresh();

            if (hunkPath)
                Qt.callLater(function() {
                    loadHunks(hunkPath, hunkMode);
                });

            return;
        }

        lastError = detail || (actionName + " FAILED");
        actionStatus = actionName + " // REFUSED";
        actionFinished(actionName, false, lastError);
    }

    Process {
        id: inspectProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.inspectStdoutText = this.text;
                root.inspectStdoutSeen = true;
                root.maybeFinishInspection();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.inspectStderrText = this.text;
                root.inspectStderrSeen = true;
                root.maybeFinishInspection();
            }
        }

        onExited: function(code, exitStatus) {
            root.inspectExitCode = Number(code);
            root.inspectExitSeen = true;
            root.maybeFinishInspection();
        }
    }

    Process {
        id: actionProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.actionStdoutText = this.text;
                root.actionStdoutSeen = true;
                root.maybeFinishAction();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.actionStderrText = this.text;
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

    Process {
        id: previewProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.previewStdoutText = this.text;
                root.previewStdoutSeen = true;
                root.maybeFinishPreview();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.previewStderrText = this.text;
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
        id: hunkProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.hunkStdoutText = this.text;
                root.hunkStdoutSeen = true;
                root.maybeFinishHunks();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.hunkStderrText = this.text;
                root.hunkStderrSeen = true;
                root.maybeFinishHunks();
            }
        }

        onExited: function(code, exitStatus) {
            root.hunkExitCode = Number(code);
            root.hunkExitSeen = true;
            root.maybeFinishHunks();
        }
    }
}
