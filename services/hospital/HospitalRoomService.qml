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
    property string armedResultTree: ""

    readonly property bool canArm:
        available
        && action === "PREPARE"
        && integrationMode === "FAST_FORWARD"
        && head.length > 0
        && base.length > 0
        && baseHead.length > 0
        && team.length > 0

    readonly property bool canRehearse:
        available
        && action === "PREPARE"
        && integrationMode === "DIVERGED"
        && head.length > 0
        && base.length > 0
        && baseHead.length > 0
        && team.length > 0

    readonly property bool canArmMerge:
        available
        && action === "PREPARE"
        && integrationMode === "DIVERGED"
        && rehearsalStatus === "CLEAN_MERGE"
        && rehearsalResultTree.length > 0
        && head.length > 0
        && base.length > 0
        && baseHead.length > 0
        && team.length > 0

    property bool rehearsing: false
    property string rehearsalStatus: ""
    property var rehearsalConflicts: []
    property var rehearsalChangedFiles: []
    property int rehearsalFileCount: 0
    property int rehearsalAdditions: 0
    property int rehearsalDeletions: 0
    property string rehearsalMergeBase: ""
    property string rehearsalResultTree: ""
    readonly property string rehearsalDetail:
        rehearsalConflicts.length > 0
        ? rehearsalConflicts.slice(0, 3).join(" • ")
        : rehearsalStatus === "CLEAN_MERGE"
        ? "TEMP MERGE CLEAN // PATIENT UNTOUCHED"
        : ""

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

    property bool rehearseExitSeen: false
    property bool rehearseStdoutSeen: false
    property bool rehearseStderrSeen: false
    property int rehearseExitCode: -1
    property string rehearseStdoutText: ""
    property string rehearseStderrText: ""

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
        armedResultTree = "";
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
        rehearsalStatus = "";
        rehearsalConflicts = [];
        rehearsalChangedFiles = [];
        rehearsalFileCount = 0;
        rehearsalAdditions = 0;
        rehearsalDeletions = 0;
        rehearsalMergeBase = "";
        rehearsalResultTree = "";
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
        if (running || rehearsing || integrating)
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

        if (targetMode === "prepare") {
            disarm();
            rehearsalStatus = "";
            rehearsalConflicts = [];
            rehearsalChangedFiles = [];
            rehearsalFileCount = 0;
            rehearsalAdditions = 0;
            rehearsalDeletions = 0;
            rehearsalMergeBase = "";
            rehearsalResultTree = "";
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

    function rehearsePrepared() {
        if (running || rehearsing || integrating)
            return;

        if (!canRehearse) {
            if (integrationMode && integrationMode !== "DIVERGED")
                summary = "REHEARSE REFUSED // " + integrationMode;
            else
                summary = "REHEARSE REFUSED // PREPARE DIVERGED FIRST";
            return;
        }

        const localPath = String(localRepoPath || "").trim();

        if (!localPath) {
            lastError = "REHEARSE REFUSED // LOCAL PATIENT NOT READY";
            summary = lastError;
            return;
        }

        rehearsing = true;
        lastError = "";
        rehearsalStatus = "";
        rehearsalConflicts = [];
        rehearsalChangedFiles = [];
        rehearsalFileCount = 0;
        rehearsalAdditions = 0;
        rehearsalDeletions = 0;
        rehearsalMergeBase = "";
        rehearsalResultTree = "";
        summary = "REHEARSE // ISOLATED TEMP PATIENT";

        rehearseExitSeen = false;
        rehearseStdoutSeen = false;
        rehearseStderrSeen = false;
        rehearseExitCode = -1;
        rehearseStdoutText = "";
        rehearseStderrText = "";

        rehearseProcess.exec([
            "bash",
            "-lc",
            'exec "$HOME/.local/bin/px" rehearse "$1" "$2" "$3" "$4" "$5" "$6" "$7"',
            "px-rehearse",
            repository,
            team,
            branch,
            head,
            base,
            baseHead,
            localPath
        ]);

        rehearseWatchdog.restart();
    }

    function maybeFinishRehearse() {
        if (!rehearsing
                || !rehearseExitSeen
                || !rehearseStdoutSeen
                || !rehearseStderrSeen)
            return;

        rehearsing = false;
        rehearseWatchdog.stop();

        if (rehearseExitCode !== 0) {
            available = false;
            lastError = String(
                rehearseStderrText
                || rehearseStdoutText
                || ("PX REHEARSE EXIT " + rehearseExitCode)
            ).trim();
            summary = "REHEARSE REFUSED // " + lastError;
            return;
        }

        try {
            const data = JSON.parse(
                String(rehearseStdoutText || "").trim()
            );

            const status =
                String(data.status || "UNKNOWN").toUpperCase();
            const totals = data.totals || {};

            rehearsalStatus = status;
            rehearsalConflicts =
                Array.isArray(data.conflicts)
                ? data.conflicts
                : [];
            rehearsalChangedFiles =
                Array.isArray(data.changed_files)
                ? data.changed_files
                : [];
            rehearsalFileCount = Number(totals.files || 0);
            rehearsalAdditions = Number(totals.additions || 0);
            rehearsalDeletions = Number(totals.deletions || 0);
            rehearsalMergeBase = String(data.merge_base || "");
            rehearsalResultTree = String(data.result_tree || "");

            available = true;
            lastError = "";

            if (status === "CLEAN_MERGE") {
                summary = "REHEARSE // CLEAN MERGE // "
                          + rehearsalFileCount
                          + " FILES // +"
                          + rehearsalAdditions
                          + " / -"
                          + rehearsalDeletions;
            } else if (status === "CONFLICTS") {
                summary = "REHEARSE // CONFLICTS // "
                          + rehearsalConflicts.length
                          + " FILES";
            } else {
                summary = "REHEARSE // " + status;
            }
        } catch (error) {
            available = false;
            lastError = "REHEARSE PARSE // " + String(error);
            summary = lastError;
        }
    }

    function armPrepared() {
        const mergeArm = canArmMerge;
        const fastForwardArm = canArm;

        if (!mergeArm && !fastForwardArm) {
            if (rehearsalStatus === "CONFLICTS")
                summary = "ARM MERGE REFUSED // REHEARSAL CONFLICTS";
            else if (integrationMode === "DIVERGED")
                summary = "ARM MERGE REFUSED // CLEAN REHEARSAL REQUIRED";
            else if (integrationMode
                    && integrationMode !== "FAST_FORWARD")
                summary = "ARM REFUSED // " + integrationMode;
            else
                summary = "ARM REFUSED // PREPARE FIRST";

            return false;
        }

        armedRepository = String(repository || "");
        armedTeam = String(team || "");
        armedBranch = String(branch || "");
        armedHead = String(head || "");
        armedBase = String(base || "");
        armedBaseHead = String(baseHead || "");
        armedMode = mergeArm ? "MERGE" : "FAST_FORWARD";
        armedResultTree =
            mergeArm
            ? String(rehearsalResultTree || "")
            : "";
        armed = true;
        lastError = "";

        summary = (mergeArm ? "MERGE ARMED // " : "ARMED // ")
                  + armedTeam
                  + " // "
                  + armedHead.slice(0, 8)
                  + " → "
                  + armedBase
                  + "@"
                  + armedBaseHead.slice(0, 8)
                  + (
                      mergeArm
                      ? " // TREE "
                        + armedResultTree.slice(0, 8)
                      : ""
                  );

        return true;
    }

    function integrateArmed() {
        if (integrating || running || rehearsing)
            return;

        if (!armed) {
            lastError = "EXECUTE REFUSED // NOT ARMED";
            summary = lastError;
            return;
        }

        const localPath = String(localRepoPath || "").trim();
        const mergeMode = armedMode === "MERGE";

        if (!localPath) {
            lastError = (mergeMode ? "MERGE" : "INTEGRATE")
                        + " REFUSED // LOCAL PATIENT NOT READY";
            summary = lastError;
            disarm();
            return;
        }

        if (mergeMode && !armedResultTree) {
            lastError = "MERGE REFUSED // NO ARMED REHEARSAL TREE";
            summary = lastError;
            disarm();
            return;
        }

        integrating = true;
        lastError = "";
        summary = (mergeMode ? "MERGE" : "INTEGRATE")
                  + " // VERIFYING ARMED SNAPSHOT";

        integrateExitSeen = false;
        integrateStdoutSeen = false;
        integrateStderrSeen = false;
        integrateExitCode = -1;
        integrateStdoutText = "";
        integrateStderrText = "";

        if (mergeMode) {
            integrateProcess.exec([
                "bash",
                "-lc",
                'exec "$HOME/.local/bin/px" merge "$1" "$2" "$3" "$4" "$5" "$6" "$7" "$8"',
                "px-merge",
                armedRepository,
                armedTeam,
                armedBranch,
                armedHead,
                armedBase,
                armedBaseHead,
                armedResultTree,
                localPath
            ]);
        } else {
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
        }

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

        const mergeMode = armedMode === "MERGE";
        const operationLabel = mergeMode ? "MERGE" : "INTEGRATE";

        integrating = false;
        integrateWatchdog.stop();

        if (integrateExitCode !== 0) {
            available = false;
            lastError = String(
                integrateStderrText
                || integrateStdoutText
                || ("PX " + operationLabel
                    + " EXIT " + integrateExitCode)
            ).trim();
            summary = operationLabel + " REFUSED // " + lastError;
            disarm();
            return;
        }

        try {
            const data = JSON.parse(
                String(integrateStdoutText || "").trim()
            );
            const status =
                String(data.status || "").toUpperCase();
            const expectedStatus =
                mergeMode ? "MERGED" : "INTEGRATED";

            if (status !== expectedStatus)
                throw new Error(
                    "UNEXPECTED " + operationLabel + " RESPONSE"
                );

            action = mergeMode ? "MERGE" : "INTEGRATE";
            available = true;
            lastError = "";
            summary = expectedStatus + " // "
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
            lastError = operationLabel
                        + " PARSE // "
                        + String(error);
            summary = lastError;
            disarm();
        }
    }

    Process {
        id: rehearseProcess

        stdout: StdioCollector {
            onStreamFinished: {
                roomService.rehearseStdoutText = this.text;
                roomService.rehearseStdoutSeen = true;
                roomService.maybeFinishRehearse();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                roomService.rehearseStderrText = this.text;
                roomService.rehearseStderrSeen = true;
                roomService.maybeFinishRehearse();
            }
        }

        onExited: function(code, exitStatus) {
            roomService.rehearseExitCode = Number(code);
            roomService.rehearseExitSeen = true;
            roomService.maybeFinishRehearse();
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
        id: rehearseWatchdog
        interval: 30000
        repeat: false

        onTriggered: {
            if (!roomService.rehearsing)
                return;

            roomService.rehearsing = false;
            roomService.available = false;
            roomService.lastError = "PX REHEARSE TIMEOUT";
            roomService.summary = roomService.lastError;

            if (rehearseProcess.running)
                rehearseProcess.running = false;
        }
    }

    Timer {
        id: integrateWatchdog
        interval: 45000
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
