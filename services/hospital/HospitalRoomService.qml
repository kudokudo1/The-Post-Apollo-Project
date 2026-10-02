import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: roomService

    property string repository: ""
    property string team: ""

    property bool running: false
    property bool available: false
    property string action: ""
    property string branch: ""
    property string relation: ""
    property int ahead: 0
    property int behind: 0
    property string head: ""

    property int diffFileCount: 0
    property int additions: 0
    property int deletions: 0

    property var commits: []
    property string latestCommitShort: ""
    property string latestCommitMessage: ""

    property string summary: "SELECT A ROOM"
    property string lastError: ""

    property bool exitSeen: false
    property bool stdoutSeen: false
    property bool stderrSeen: false
    property int exitCode: -1
    property string stdoutText: ""
    property string stderrText: ""

    signal inspected()

    function clearResult() {
        available = false;
        action = "";
        branch = "";
        relation = "";
        ahead = 0;
        behind = 0;
        head = "";
        diffFileCount = 0;
        additions = 0;
        deletions = 0;
        commits = [];
        latestCommitShort = "";
        latestCommitMessage = "";
        summary = team ? "ROOM READY" : "SELECT A ROOM";
        lastError = "";
    }

    function runInspection(mode) {
        if (running)
            return;

        const targetRepo = String(repository || "").trim();
        const targetTeam = String(team || "").trim();
        const targetMode = String(mode || "").trim().toLowerCase();

        if (!targetRepo || !targetTeam) {
            lastError = "SELECT A ROOM";
            summary = lastError;
            return;
        }

        if (targetMode !== "status"
                && targetMode !== "diff"
                && targetMode !== "log") {
            lastError = "UNKNOWN ROOM ACTION";
            summary = lastError;
            return;
        }

        running = true;
        available = false;
        action = targetMode.toUpperCase();
        summary = action + " // READING";
        lastError = "";

        exitSeen = false;
        stdoutSeen = false;
        stderrSeen = false;
        exitCode = -1;
        stdoutText = "";
        stderrText = "";

        inspectProcess.exec([
            "bash",
            "-lc",
            'exec "$HOME/.local/bin/px" room "$1" "$2" "$3"',
            "px-room",
            targetRepo,
            targetTeam,
            targetMode
        ]);

        watchdog.restart();
    }

    function parseResult(payload) {
        const raw = String(payload || "").trim();

        if (!raw)
            throw new Error("EMPTY ROOM RESPONSE");

        const data = JSON.parse(raw);
        const mode = String(data.action || "").toUpperCase();

        action = mode;
        branch = String(data.branch || "");

        if (mode === "STATUS") {
            relation = String(data.relation || "UNKNOWN").toUpperCase();
            ahead = Number(data.ahead || 0);
            behind = Number(data.behind || 0);
            head = String(data.head || "");

            summary = "STATUS // " + relation
                      + " // +" + ahead
                      + " / -" + behind;
            return;
        }

        if (mode === "DIFF") {
            relation = String(data.relation || "UNKNOWN").toUpperCase();
            ahead = Number(data.ahead || 0);
            behind = Number(data.behind || 0);

            const totals = data.totals || {};
            diffFileCount = Number(totals.files || 0);
            additions = Number(totals.additions || 0);
            deletions = Number(totals.deletions || 0);

            summary = "DIFF // " + diffFileCount + " FILES"
                      + " // +" + additions
                      + " / -" + deletions;
            return;
        }

        if (mode === "LOG") {
            commits = Array.isArray(data.commits)
                      ? data.commits
                      : [];

            if (commits.length > 0) {
                const latest = commits[0] || {};
                latestCommitShort = String(latest.short || "");
                latestCommitMessage = String(latest.message || "");

                summary = "LOG // " + latestCommitShort
                          + " // " + latestCommitMessage;
            } else {
                summary = "LOG // NO COMMITS";
            }
            return;
        }

        summary = "ROOM // UNKNOWN RESPONSE";
    }

    function maybeFinish() {
        if (!running || !exitSeen || !stdoutSeen || !stderrSeen)
            return;

        running = false;
        watchdog.stop();

        if (exitCode !== 0) {
            available = false;
            lastError = String(
                stderrText
                || stdoutText
                || ("PX ROOM EXIT " + exitCode)
            ).trim();
            summary = "ROOM ERROR // " + lastError;
            return;
        }

        try {
            parseResult(stdoutText);
            available = true;
            lastError = "";
            inspected();
        } catch (error) {
            available = false;
            lastError = "ROOM PARSE // " + String(error);
            summary = lastError;
        }
    }

    Process {
        id: inspectProcess

        stdout: StdioCollector {
            onStreamFinished: {
                roomService.stdoutText = this.text;
                roomService.stdoutSeen = true;
                roomService.maybeFinish();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                roomService.stderrText = this.text;
                roomService.stderrSeen = true;
                roomService.maybeFinish();
            }
        }

        onExited: function(code, exitStatus) {
            roomService.exitCode = Number(code);
            roomService.exitSeen = true;
            roomService.maybeFinish();
        }
    }

    Timer {
        id: watchdog
        interval: 20000
        repeat: false

        onTriggered: {
            if (!roomService.running)
                return;

            roomService.running = false;
            roomService.available = false;
            roomService.lastError = "PX ROOM TIMEOUT";
            roomService.summary = roomService.lastError;

            if (inspectProcess.running)
                inspectProcess.running = false;
        }
    }
}
