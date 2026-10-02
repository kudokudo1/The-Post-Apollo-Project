import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: roomService

    property string repository: ""
    property string team: ""
    property string localRepoPath: ""

    property string integrationMode: ""
    property string base: ""
    property string baseHead: ""

    property bool armed: false
    property string armedRepository: ""
    property string armedTeam: ""
    property string armedBranch: ""
    property string armedHead: ""
    property string armedBase: ""
    property string armedBaseHead: ""
    property string armedMode: ""

    readonly property bool canArm:
        available
        && action === "PREPARE"
        && integrationMode === "FAST_FORWARD"
        && head.length > 0
        && base.length > 0
        && baseHead.length > 0
        && team.length > 0

    property bool integrating: false

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

    property bool integrateExitSeen: false
    property bool integrateStdoutSeen: false
    property bool integrateStderrSeen: false
    property int integrateExitCode: -1
    property string integrateStdoutText: ""
    property string integrateStderrText: ""

    signal inspected()
    signal integrated()

    function disarm() {
        armed = false;
        armedRepository = "";
        armedTeam = "";
        armedBranch = "";
        armedHead = "";
        armedBase = "";
        armedBaseHead = "";
        armedMode = "";
    }

    function clearResult() {
        available = false;
        action = "";
        branch = "";
        relation = "";
        ahead = 0;
        behind = 0;
        head = "";
        base = "";
        baseHead = "";
        integrationMode = "";
        disarm();
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
                && targetMode !== "log"
                && targetMode !== "prepare") {
            lastError = "UNKNOWN ROOM ACTION";
            summary = lastError;
            return;
        }

        if (targetMode === "prepare")
            disarm();

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
        base = String(data.base || "");

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

        if (mode === "PREPARE") {
            integrationMode =
                String(data.mode || "REVIEW_REQUIRED").toUpperCase();
            head = String(data.head || "");
            baseHead = String(data.base_head || "");
            relation =
                String(data.relation || "UNKNOWN").toUpperCase();
            ahead = Number(data.ahead || 0);
            behind = Number(data.behind || 0);

            const totals = data.totals || {};
            diffFileCount = Number(totals.files || 0);
            additions = Number(totals.additions || 0);
            deletions = Number(totals.deletions || 0);

            summary = "PREPARE // " + integrationMode
                      + " // " + diffFileCount + " FILES"
                      + " // +" + ahead
                      + " / -" + behind;
            return;
        }

        summary = "ROOM // UNKNOWN RESPONSE";
    }

    function armPrepared() {
        if (!canArm) {
            if (integrationMode && integrationMode !== "FAST_FORWARD")
                summary = "ARM REFUSED // " + integrationMode;
            else
                summary = "ARM REFUSED // PREPARE FAST_FORWARD FIRST";
            return false;
        }

        armedRepository = String(repository || "");
        armedTeam = String(team || "");
        armedBranch = String(branch || "");
        armedHead = String(head || "");
        armedBase = String(base || "");
        armedBaseHead = String(baseHead || "");
        armedMode = String(integrationMode || "");
        armed = true;
        lastError = "";

        summary = "ARMED // "
                  + armedTeam
                  + " // "
                  + armedHead.slice(0, 8)
                  + " → "
                  + armedBase
                  + "@"
                  + armedBaseHead.slice(0, 8);

        return true;
    }

    function integrateArmed() {
        if (integrating || running)
            return;

        if (!armed) {
            lastError = "INTEGRATE REFUSED // NOT ARMED";
            summary = lastError;
            return;
        }

        const localPath = String(localRepoPath || "").trim();

        if (!localPath) {
            lastError = "INTEGRATE REFUSED // LOCAL PATIENT NOT READY";
            summary = lastError;
            disarm();
            return;
        }

        integrating = true;
        lastError = "";
        summary = "INTEGRATE // VERIFYING ARMED SNAPSHOT";

        integrateExitSeen = false;
        integrateStdoutSeen = false;
        integrateStderrSeen = false;
        integrateExitCode = -1;
        integrateStdoutText = "";
        integrateStderrText = "";

        integrateProcess.exec([
            "bash",
            "-lc",
            'exec "$HOME/.local/bin/px" integrate "$1" "$2" "$3" "$4" "$5" "$6" "$7"',
            "px-integrate",
            armedRepository,
            armedTeam,
            armedBranch,
            armedHead,
            armedBase,
            armedBaseHead,
            localPath
        ]);

        integrateWatchdog.restart();
    }

    function launchLazygit() {
        const repo = String(localRepoPath || "").trim();

        if (!repo) {
            lastError = "LOCAL REPOSITORY NOT READY";
            summary = lastError;
            return;
        }

        Quickshell.execDetached([
            "bash",
            "-lc",
            [
                'repo="$1"',
                'cd "$repo" || exit 1',
                'exec kitty --directory "$PWD" toolbox run -c fedora-toolbox-44 lazygit'
            ].join("\n"),
            "hospital-room-lazygit",
            repo
        ]);

        lastError = "";
        summary = team
                  ? "LAZYGIT // " + team
                  : "LAZYGIT // OPEN";
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

    function maybeFinishIntegrate() {
        if (!integrating
                || !integrateExitSeen
                || !integrateStdoutSeen
                || !integrateStderrSeen)
            return;

        integrating = false;
        integrateWatchdog.stop();

        if (integrateExitCode !== 0) {
            available = false;
            lastError = String(
                integrateStderrText
                || integrateStdoutText
                || ("PX INTEGRATE EXIT " + integrateExitCode)
            ).trim();
            summary = "INTEGRATE REFUSED // " + lastError;
            disarm();
            return;
        }

        try {
            const data = JSON.parse(
                String(integrateStdoutText || "").trim()
            );

            if (String(data.status || "").toUpperCase()
                    !== "INTEGRATED")
                throw new Error("UNEXPECTED INTEGRATE RESPONSE");

            action = "INTEGRATE";
            available = true;
            lastError = "";
            summary = "INTEGRATED // "
                      + String(data.base || armedBase)
                      + " // "
                      + String(data.old_base_head || "")
                            .slice(0, 8)
                      + " → "
                      + String(data.new_base_head || "")
                            .slice(0, 8);

            disarm();
            integrated();
        } catch (error) {
            available = false;
            lastError = "INTEGRATE PARSE // " + String(error);
            summary = lastError;
            disarm();
        }
    }

    Process {
        id: integrateProcess

        stdout: StdioCollector {
            onStreamFinished: {
                roomService.integrateStdoutText = this.text;
                roomService.integrateStdoutSeen = true;
                roomService.maybeFinishIntegrate();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                roomService.integrateStderrText = this.text;
                roomService.integrateStderrSeen = true;
                roomService.maybeFinishIntegrate();
            }
        }

        onExited: function(code, exitStatus) {
            roomService.integrateExitCode = Number(code);
            roomService.integrateExitSeen = true;
            roomService.maybeFinishIntegrate();
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

    Timer {
        id: integrateWatchdog
        interval: 20000
        repeat: false

        onTriggered: {
            if (!roomService.integrating)
                return;

            roomService.integrating = false;
            roomService.available = false;
            roomService.lastError = "PX INTEGRATE TIMEOUT";
            roomService.summary = roomService.lastError;
            roomService.disarm();

            if (integrateProcess.running)
                integrateProcess.running = false;
        }
    }
}
