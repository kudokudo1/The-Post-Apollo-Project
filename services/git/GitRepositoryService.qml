import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property string repositoryPath: ""

    property bool refreshing: false
    property bool actionBusy: false
    property string actionName: ""
    property string actionStatus: "READY"
    property string lastError: ""

    property var remotes: []
    property var configRows: []

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

    signal refreshed()
    signal actionFinished(string action, bool success, string detail)

    readonly property bool available:
        String(repositoryPath || "").trim().length > 0

    function remoteAt(index) {
        if (index < 0 || index >= remotes.length)
            return null;
        return remotes[index];
    }

    function refresh() {
        const repo = String(repositoryPath || "").trim();

        if (!repo || refreshing || actionBusy)
            return false;

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
                'while IFS= read -r name; do',
                '  [ -z "$name" ] && continue',
                '  url="$(git -C "$repo" remote get-url "$name" 2>/dev/null || true)"',
                '  push="$(git -C "$repo" remote get-url --push "$name" 2>/dev/null || true)"',
                '  printf "REMOTE\\t%s\\t%s\\t%s\\n" "$name" "$url" "$push"',
                'done < <(git -C "$repo" remote 2>/dev/null)',
                'for key in user.name user.email fetch.prune pull.rebase pull.ff rebase.autostash core.autocrlf core.filemode; do',
                '  value="$(git -C "$repo" config --local --get "$key" 2>/dev/null || true)"',
                '  [ -n "$value" ] && printf "CONFIG\\t%s\\t%s\\n" "$key" "$value"',
                'done'
            ].join("\n"),
            "git-repository-inspect",
            repo
        ]);

        return true;
    }

    function parseInspection(text) {
        const remoteRows = [];
        const configs = [];
        const lines = String(text || "").split("\n");

        for (let i = 0; i < lines.length; ++i) {
            const line = String(lines[i] || "");
            if (!line)
                continue;

            const parts = line.split("\t");
            const kind = parts.length > 0 ? parts[0] : "";

            if (kind === "REMOTE") {
                remoteRows.push({
                    name: parts.length > 1 ? parts[1] : "",
                    url: parts.length > 2 ? parts[2] : "",
                    pushUrl: parts.length > 3 ? parts[3] : ""
                });
            } else if (kind === "CONFIG") {
                configs.push({
                    key: parts.length > 1 ? parts[1] : "",
                    value: parts.length > 2 ? parts.slice(2).join("\t") : ""
                });
            }
        }

        remotes = remoteRows;
        configRows = configs;
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
                || ("REPOSITORY EXIT " + inspectExitCode)
            ).trim();
            return;
        }

        parseInspection(inspectStdoutText);
        lastError = "";
        refreshed();
    }

    function runAction(operation, a, b) {
        const repo = String(repositoryPath || "").trim();
        const op = String(operation || "").trim();
        const first = String(a || "").trim();
        const second = String(b || "").trim();

        if (!repo || !op || refreshing || actionBusy)
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
                'if ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then',
                '  printf "REFUSED\\tNOT A GIT WORKTREE\\n"',
                '  exit 21',
                'fi',
                'case "$op" in',
                '  fetch)',
                '    [ -n "$a" ] || { printf "REFUSED\\tREMOTE REQUIRED\\n"; exit 22; }',
                '    git -C "$repo" fetch --prune "$a" || exit $?',
                '    printf "OK\\tFETCHED + PRUNED // %s\\n" "$a"',
                '    ;;',
                '  add-remote)',
                '    [ -n "$a" ] && [ -n "$b" ] || { printf "REFUSED\\tREMOTE NAME + URL REQUIRED\\n"; exit 23; }',
                '    git -C "$repo" remote get-url "$a" >/dev/null 2>&1 && { printf "REFUSED\\tREMOTE ALREADY EXISTS // %s\\n" "$a"; exit 24; }',
                '    git -C "$repo" remote add "$a" "$b" || exit $?',
                '    printf "OK\\tADDED REMOTE // %s\\n" "$a"',
                '    ;;',
                '  set-url)',
                '    [ -n "$a" ] && [ -n "$b" ] || { printf "REFUSED\\tREMOTE NAME + URL REQUIRED\\n"; exit 25; }',
                '    git -C "$repo" remote get-url "$a" >/dev/null 2>&1 || { printf "REFUSED\\tREMOTE NOT FOUND // %s\\n" "$a"; exit 26; }',
                '    git -C "$repo" remote set-url "$a" "$b" || exit $?',
                '    printf "OK\\tUPDATED REMOTE URL // %s\\n" "$a"',
                '    ;;',
                '  set-config)',
                '    [ -n "$a" ] || { printf "REFUSED\\tCONFIG KEY REQUIRED\\n"; exit 27; }',
                '    [ -n "$b" ] || { printf "REFUSED\\tCONFIG VALUE REQUIRED\\n"; exit 28; }',
                '    case "$a" in *[!A-Za-z0-9._-]*|"") printf "REFUSED\\tINVALID CONFIG KEY\\n"; exit 29 ;; esac',
                '    git -C "$repo" config --local "$a" "$b" || exit $?',
                '    printf "OK\\tCONFIG // %s = %s\\n" "$a" "$b"',
                '    ;;',
                '  unset-config)',
                '    [ -n "$a" ] || { printf "REFUSED\\tCONFIG KEY REQUIRED\\n"; exit 30; }',
                '    git -C "$repo" config --local --unset-all "$a" >/dev/null 2>&1 || true',
                '    printf "OK\\tUNSET CONFIG // %s\\n" "$a"',
                '    ;;',
                '  *)',
                '    printf "REFUSED\\tUNKNOWN OPERATION // %s\\n" "$op"',
                '    exit 90',
                '    ;;',
                'esac'
            ].join("\n"),
            "git-repository-action",
            repo,
            op,
            first,
            second
        ]);

        return true;
    }

    function fetchRemote(name) {
        return runAction("fetch", name, "");
    }

    function addRemote(name, url) {
        return runAction("add-remote", name, url);
    }

    function setRemoteUrl(name, url) {
        return runAction("set-url", name, url);
    }

    function setConfig(key, value) {
        return runAction("set-config", key, value);
    }

    function unsetConfig(key) {
        return runAction("unset-config", key, "");
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
}
