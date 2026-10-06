import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property string repositoryPath: ""

    property bool refreshing: false
    property bool actionBusy: false
    property bool previewBusy: false

    property string actionName: ""
    property string actionStatus: "READY"
    property string lastError: ""

    property var files: []
    property int stagedCount: 0
    property int unstagedCount: 0
    property int untrackedCount: 0

    property string previewPath: ""
    property string previewText: "SELECT A CHANGED FILE"
    property bool previewStaged: false

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

    signal refreshed()
    signal actionFinished(string action, bool success, string detail)

    readonly property bool available:
        String(repositoryPath || "").trim().length > 0

    readonly property int changedCount: files.length

    function statusLabel(indexStatus, worktreeStatus) {
        if (indexStatus === "?" && worktreeStatus === "?")
            return "NEW";

        if (indexStatus === "A")
            return "ADDED";
        if (indexStatus === "D" || worktreeStatus === "D")
            return "DELETED";
        if (indexStatus === "R")
            return "RENAMED";
        if (indexStatus === "C")
            return "COPIED";
        if (indexStatus === "U" || worktreeStatus === "U")
            return "CONFLICT";
        if (indexStatus === "M" || worktreeStatus === "M")
            return "MODIFIED";

        return "CHANGED";
    }

    function refresh() {
        const repo = String(repositoryPath || "").trim();

        if (refreshing || actionBusy)
            return false;

        if (!repo) {
            files = [];
            stagedCount = 0;
            unstagedCount = 0;
            untrackedCount = 0;
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
                '  printf "NOT A GIT WORKTREE\\n"',
                '  exit 21',
                'fi',
                'git -C "$repo" status --porcelain=v1 --untracked-files=all'
            ].join("\n"),
            "git-changes-inspect",
            repo
        ]);

        return true;
    }

    function parseInspection(text) {
        const rows = [];
        let staged = 0;
        let unstaged = 0;
        let untracked = 0;

        const lines = String(text || "").split("\n");

        for (let i = 0; i < lines.length; ++i) {
            const line = String(lines[i] || "");
            if (line.length < 3)
                continue;

            const x = line.charAt(0);
            const y = line.charAt(1);
            let path = line.slice(3);

            const arrow = path.indexOf(" -> ");
            if (arrow >= 0)
                path = path.slice(arrow + 4);

            const isUntracked = x === "?" && y === "?";
            const isStaged = !isUntracked && x !== " ";
            const isUnstaged = isUntracked || y !== " ";

            if (isStaged)
                staged += 1;
            if (isUnstaged)
                unstaged += 1;
            if (isUntracked)
                untracked += 1;

            rows.push({
                path: path,
                indexStatus: x,
                worktreeStatus: y,
                staged: isStaged,
                unstaged: isUnstaged,
                untracked: isUntracked,
                label: statusLabel(x, y)
            });
        }

        files = rows;
        stagedCount = staged;
        unstagedCount = unstaged;
        untrackedCount = untracked;

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

    function preview(path) {
        const repo = String(repositoryPath || "").trim();
        const target = String(path || "").trim();

        if (!repo || !target || previewBusy)
            return false;

        previewBusy = true;
        previewPath = target;
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
                'printf "=== STAGED ========================================\\n"',
                'git -C "$repo" diff --cached -- "$path" 2>/dev/null || true',
                'printf "\\n=== WORKTREE ======================================\\n"',
                'git -C "$repo" diff -- "$path" 2>/dev/null || true',
                'if git -C "$repo" ls-files --error-unmatch -- "$path" >/dev/null 2>&1; then',
                '  :',
                'elif [ -f "$repo/$path" ]; then',
                '  printf "\\n=== UNTRACKED =====================================\\n"',
                'git diff --no-index -- /dev/null "$repo/$path" 2>/dev/null || true',
                'fi'
            ].join("\n"),
            "git-changes-preview",
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

    function runAction(operation, argument) {
        const repo = String(repositoryPath || "").trim();
        const op = String(operation || "").trim();
        const arg = String(argument || "");

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
                'arg="$3"',
                'if ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then',
                '  printf "REFUSED\\tNOT A GIT WORKTREE\\n"',
                '  exit 21',
                'fi',
                'case "$op" in',
                '  stage)',
                '    [ -n "$arg" ] || { printf "REFUSED\\tNO FILE SELECTED\\n"; exit 22; }',
                '    git -C "$repo" add -- "$arg" || exit $?',
                '    printf "OK\\tSTAGED // %s\\n" "$arg"',
                '    ;;',
                '  unstage)',
                '    [ -n "$arg" ] || { printf "REFUSED\\tNO FILE SELECTED\\n"; exit 23; }',
                '    git -C "$repo" restore --staged -- "$arg" 2>/dev/null || git -C "$repo" reset -q HEAD -- "$arg" || exit $?',
                '    printf "OK\\tUNSTAGED // %s\\n" "$arg"',
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
                '    [ -n "$arg" ] || { printf "REFUSED\\tCOMMIT MESSAGE REQUIRED\\n"; exit 24; }',
                '    if git -C "$repo" diff --cached --quiet --exit-code; then',
                '      printf "REFUSED\\tNO STAGED CHANGES\\n"',
                '      exit 25',
                '    fi',
                '    git -C "$repo" commit -m "$arg" || exit $?',
                '    printf "OK\\tCOMMITTED // %s\\n" "$arg"',
                '    ;;',
                '  stash)',
                '    if [ -z "$(git -C "$repo" status --porcelain=v1 2>/dev/null)" ]; then',
                '      printf "REFUSED\\tWORKTREE CLEAN\\n"',
                '      exit 26',
                '    fi',
                '    if [ -z "$arg" ]; then arg="Post-Apollo stash"; fi',
                '    git -C "$repo" stash push -u -m "$arg" || exit $?',
                '    printf "OK\\tSTASHED // %s\\n" "$arg"',
                '    ;;',
                '  stash-pop)',
                '    git -C "$repo" rev-parse --verify refs/stash >/dev/null 2>&1 || { printf "REFUSED\\tNO STASH AVAILABLE\\n"; exit 27; }',
                '    git -C "$repo" stash pop || exit $?',
                '    printf "OK\\tPOPPED LATEST STASH\\n"',
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
            arg
        ]);

        return true;
    }

    function stage(path) {
        return runAction("stage", path);
    }

    function unstage(path) {
        return runAction("unstage", path);
    }

    function stageAll() {
        return runAction("stage-all", "");
    }

    function unstageAll() {
        return runAction("unstage-all", "");
    }

    function commit(message) {
        return runAction("commit", String(message || "").trim());
    }

    function stash(message) {
        return runAction("stash", String(message || "").trim());
    }

    function stashPop() {
        return runAction("stash-pop", "");
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
        const first = out.split("\n")[0] || "";
        const parts = first.split("\t");
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
}
