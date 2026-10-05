import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: presenceService

    property string repoPath: ""
    property string branchName: ""

    property bool running: false
    property bool available: false
    property string location: "UNKNOWN"
    property string syncState: ""
    property string localHead: ""
    property string remoteHead: ""
    property int localAhead: 0
    property int remoteAhead: 0
    property string lastError: ""

    readonly property string summary: {
        if (!branchName)
            return "NO ROOM";

        if (running && !available)
            return "READING";

        if (!available)
            return lastError ? "ERROR" : "UNKNOWN";

        if (location === "BOTH") {
            if (syncState === "SYNCED")
                return "BOTH // SYNCED";

            if (syncState === "LOCAL_AHEAD")
                return "BOTH // LOCAL +" + String(localAhead);

            if (syncState === "REMOTE_AHEAD")
                return "BOTH // REMOTE +" + String(remoteAhead);

            if (syncState === "DIVERGED")
                return "BOTH // DIVERGED +"
                    + String(localAhead)
                    + "/-"
                    + String(remoteAhead);

            return "BOTH";
        }

        return location;
    }

    signal refreshed()

    function clearResult() {
        running = false;
        available = false;
        location = "UNKNOWN";
        syncState = "";
        localHead = "";
        remoteHead = "";
        localAhead = 0;
        remoteAhead = 0;
        lastError = "";
    }

    function refresh() {
        if (running)
            return;

        const repo = String(repoPath || "").trim();
        const branch = String(branchName || "").trim();

        if (!repo || !branch) {
            clearResult();
            return;
        }

        running = true;
        available = false;
        location = "UNKNOWN";
        syncState = "";
        localHead = "";
        remoteHead = "";
        localAhead = 0;
        remoteAhead = 0;
        lastError = "";
        watchdog.restart();

        inspectProcess.exec([
            "bash",
            "-lc",
            [
                'repo="$1"',
                'branch="$2"',
                'if ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then',
                '  printf "ERROR\\tBED CHECKOUT NOT FOUND\\n"',
                '  printf "DONE\\t\\n"',
                '  exit 0',
                'fi',
                'local="$(git -C "$repo" show-ref --verify --hash "refs/heads/$branch" 2>/dev/null || true)"',
                'remote="$(git -C "$repo" show-ref --verify --hash "refs/remotes/origin/$branch" 2>/dev/null || true)"',
                'printf "LOCAL\\t%s\\n" "$local"',
                'printf "REMOTE\\t%s\\n" "$remote"',
                'if [ -n "$local" ] && [ -n "$remote" ]; then',
                '  counts="$(git -C "$repo" rev-list --left-right --count "$local...$remote" 2>/dev/null || true)"',
                '  set -- $counts',
                '  printf "COUNTS\\t%s\\t%s\\n" "${1:-0}" "${2:-0}"',
                'fi',
                'printf "DONE\\t\\n"'
            ].join("\n"),
            "hospital-room-presence",
            repo,
            branch
        ]);
    }

    function finishSnapshot() {
        const hasLocal = localHead.length > 0;
        const hasRemote = remoteHead.length > 0;

        if (hasLocal && hasRemote) {
            location = "BOTH";

            if (localHead === remoteHead)
                syncState = "SYNCED";
            else if (localAhead > 0 && remoteAhead === 0)
                syncState = "LOCAL_AHEAD";
            else if (remoteAhead > 0 && localAhead === 0)
                syncState = "REMOTE_AHEAD";
            else
                syncState = "DIVERGED";
        } else if (hasLocal) {
            location = "LOCAL";
            syncState = "";
        } else if (hasRemote) {
            location = "REMOTE";
            syncState = "";
        } else {
            location = "MISSING";
            syncState = "";
        }

        running = false;
        available = lastError.length === 0;
        watchdog.stop();

        if (available)
            refreshed();
    }

    function consumeLine(line) {
        const raw = String(line || "");
        const parts = raw.split("\t");
        const key = parts.length > 0 ? parts[0] : "";
        const value = parts.length > 1 ? parts[1] : "";

        if (key === "LOCAL")
            localHead = value;
        else if (key === "REMOTE")
            remoteHead = value;
        else if (key === "COUNTS") {
            localAhead = Number(parts.length > 1 ? parts[1] : 0);
            remoteAhead = Number(parts.length > 2 ? parts[2] : 0);
        } else if (key === "ERROR")
            lastError = value;
        else if (key === "DONE")
            finishSnapshot();
    }

    onRepoPathChanged: refreshKick.restart()
    onBranchNameChanged: refreshKick.restart()

    Timer {
        id: refreshKick
        interval: 40
        repeat: false

        onTriggered: presenceService.refresh()
    }

    Process {
        id: inspectProcess

        stdout: SplitParser {
            onRead: function(line) {
                presenceService.consumeLine(line);
            }
        }

        stderr: SplitParser {
            onRead: function(line) {
                const message = String(line || "").trim();

                if (message.length > 0)
                    presenceService.lastError = message;
            }
        }

        onExited: function(code, exitStatus) {
            if (!presenceService.running)
                return;

            if (Number(code) !== 0) {
                presenceService.running = false;
                presenceService.available = false;
                presenceService.lastError =
                    "ROOM PRESENCE EXIT " + String(code);
                watchdog.stop();
            }
        }
    }

    Timer {
        id: watchdog
        interval: 10000
        repeat: false

        onTriggered: {
            if (!presenceService.running)
                return;

            presenceService.running = false;
            presenceService.available = false;
            presenceService.lastError = "ROOM PRESENCE TIMEOUT";

            if (inspectProcess.running)
                inspectProcess.running = false;
        }
    }
}
