import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: gitService

    // First live target: the Quickshell repo that is actually driving the desktop.
    readonly property string repoLabel: "~/.config/quickshell"

    property bool available: false
    property bool refreshing: false
    property bool actionBusy: false

    property string repoRoot: ""
    property string repository: "NOT CONNECTED"
    property string branch: "NOT CONNECTED"
    property string head: "NOT CONNECTED"
    property string worktree: "NOT CONNECTED"
    property string origin: "NOT CONNECTED"

    property string lastError: ""
    property string actionTitle: "READY"
    property string actionOutput: "Select STATUS, DIFF, or LOG."

    signal refreshed()

    function refresh() {
        if (refreshing)
            return;

        refreshing = true;
        lastError = "";
        refreshWatchdog.restart();

        refreshProcess.exec([
            "bash",
            "-lc",
            [
                'repo="$HOME/.config/quickshell"',
                'if ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then',
                '  printf "ERROR\\tNOT A GIT REPOSITORY\\n"',
                '  printf "DONE\\t\\n"',
                '  exit 0',
                'fi',
                'root="$(git -C "$repo" rev-parse --show-toplevel)"',
                'name="$(basename "$root")"',
                'branch="$(git -C "$repo" branch --show-current)"',
                'if [ -z "$branch" ]; then branch="DETACHED"; fi',
                'head="$(git -C "$repo" rev-parse --short=10 HEAD)"',
                'count="$(git -C "$repo" status --porcelain=v1 | wc -l | tr -d " ")"',
                'if [ "$count" -eq 0 ]; then worktree="CLEAN"; else worktree="DIRTY • $count CHANGES"; fi',
                'origin="$(git -C "$repo" remote get-url origin 2>/dev/null || true)"',
                'if [ -z "$origin" ]; then origin="NO ORIGIN"; fi',
                'printf "ROOT\\t%s\\n" "$root"',
                'printf "REPO\\t%s\\n" "$name"',
                'printf "BRANCH\\t%s\\n" "$branch"',
                'printf "HEAD\\t%s\\n" "$head"',
                'printf "WORKTREE\\t%s\\n" "$worktree"',
                'printf "ORIGIN\\t%s\\n" "$origin"',
                'printf "DONE\\t\\n"'
            ].join("; ")
        ]);
    }

    function consumeRefreshLine(line) {
        const raw = String(line || "");
        const tab = raw.indexOf("\t");
        const key = tab >= 0 ? raw.slice(0, tab) : raw;
        const value = tab >= 0 ? raw.slice(tab + 1) : "";

        if (key === "ROOT")
            repoRoot = value;
        else if (key === "REPO")
            repository = value;
        else if (key === "BRANCH")
            branch = value;
        else if (key === "HEAD")
            head = value;
        else if (key === "WORKTREE")
            worktree = value;
        else if (key === "ORIGIN")
            origin = value;
        else if (key === "ERROR") {
            available = false;
            lastError = value;
        } else if (key === "DONE") {
            refreshing = false;
            refreshWatchdog.stop();

            if (!lastError) {
                available = true;
                refreshed();
            }
        }
    }

    function runReadAction(kind) {
        if (actionBusy)
            return;

        const action = String(kind || "").toLowerCase();

        if (action !== "status" && action !== "diff" && action !== "log")
            return;

        actionBusy = true;
        actionTitle = action.toUpperCase();
        actionOutput = "";
        actionWatchdog.restart();

        actionProcess.exec([
            "bash",
            "-lc",
            [
                'repo="$HOME/.config/quickshell"',
                'kind="$1"',
                'if ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then',
                '  printf "NOT A GIT REPOSITORY\\n"',
                '  printf "__PA_DONE__\\n"',
                '  exit 0',
                'fi',
                'case "$kind" in',
                '  status)',
                '    git -C "$repo" status --short --branch',
                '    ;;',
                '  diff)',
                '    output="$(git -C "$repo" diff --stat; git -C "$repo" diff --name-status)"',
                '    if [ -n "$output" ]; then printf "%s\\n" "$output"; else printf "NO UNSTAGED DIFF\\n"; fi',
                '    ;;',
                '  log)',
                '    git -C "$repo" log --oneline --decorate -n 20',
                '    ;;',
                'esac',
                'printf "__PA_DONE__\\n"'
            ].join("; "),
            "_",
            action
        ]);
    }

    function consumeActionLine(line) {
        const raw = String(line || "");

        if (raw === "__PA_DONE__") {
            actionBusy = false;
            actionWatchdog.stop();
            refresh();
            return;
        }

        if (actionOutput.length > 12000)
            return;

        actionOutput += (actionOutput.length > 0 ? "\n" : "") + raw;
    }

    function launchLazygit() {
        Quickshell.execDetached([
            "bash",
            "-lc",
            'cd "$HOME/.config/quickshell" && exec kitty --directory "$PWD" lazygit'
        ]);
    }

    Process {
        id: refreshProcess

        stdout: SplitParser {
            onRead: function(line) {
                gitService.consumeRefreshLine(line);
            }
        }

        stderr: SplitParser {
            onRead: function(line) {
                const message = String(line || "").trim();

                if (message.length > 0)
                    gitService.lastError = message;
            }
        }
    }

    Process {
        id: actionProcess

        stdout: SplitParser {
            onRead: function(line) {
                gitService.consumeActionLine(line);
            }
        }

        stderr: SplitParser {
            onRead: function(line) {
                const message = String(line || "").trim();

                if (message.length > 0)
                    gitService.actionOutput += (gitService.actionOutput.length > 0 ? "\n" : "") + "ERR: " + message;
            }
        }
    }

    Timer {
        id: refreshWatchdog
        interval: 4000
        repeat: false

        onTriggered: {
            gitService.refreshing = false;
            gitService.available = false;
            gitService.lastError = "GIT READ TIMEOUT";
        }
    }

    Timer {
        id: actionWatchdog
        interval: 8000
        repeat: false

        onTriggered: {
            gitService.actionBusy = false;
            gitService.actionOutput += (gitService.actionOutput.length > 0 ? "\n" : "") + "ACTION TIMEOUT";
        }
    }
}
