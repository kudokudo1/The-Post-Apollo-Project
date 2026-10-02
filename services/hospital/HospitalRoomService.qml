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

    property bool postOpRunning: false
    property string postOpStatus: ""
    property string postOpOperation: ""
    property string postOpExpectedBaseHead: ""
    property string postOpExpectedRoomHead: ""
    property string postOpCurrentBaseHead: ""
    property string postOpCurrentRoomHead: ""
    property string postOpCurrentRelation: ""
    property bool postOpRoomUnchanged: false
    readonly property string postOpDetail:
        postOpStatus === "POST_OP_CLEAN"
        ? "MAIN " + postOpCurrentBaseHead.slice(0, 8)
          + " // ROOM CONTAINED"
          + (
              postOpRoomUnchanged
              ? " // ROOM HEAD UNCHANGED"
              : " // ROOM ADVANCED AFTER OP"
            )
        : ""

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

    property bool postOpExitSeen: false
    property bool postOpStdoutSeen: false
    property bool postOpStderrSeen: false
    property int postOpExitCode: -1
    property string postOpStdoutText: ""
    property string postOpStderrText: ""

    property bool integrateExitSeen: false
    property bool integrateStdoutSeen: false
    property bool integrateStderrSeen: false
    property int integrateExitCode: -1
    property string integrateStdoutText: ""
    property string integrateStderrText: ""

    signal inspected()
    signal integrated()
    signal postOpFinished()

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
        postOpStatus = "";
        postOpOperation = "";
        postOpExpectedBaseHead = "";
        postOpExpectedRoomHead = "";
        postOpCurrentBaseHead = "";
        postOpCurrentRoomHead = "";
        postOpCurrentRelation = "";
        postOpRoomUnchanged = false;
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

    function certificationSnapshot() {
        return {
            repository: repository,
            team: team,
            branch: branch,
            head: head,
            base: base,
            baseHead: baseHead,
            relation: relation,
            mode: integrationMode,
            diffFileCount: diffFileCount,
            additions: additions,
            deletions: deletions,
            rehearsal: {
                status: rehearsalStatus,
                mergeBase: rehearsalMergeBase,
                resultTree: rehearsalResultTree,
                conflicts: rehearsalConflicts,
                changedFiles: rehearsalChangedFiles,
                fileCount: rehearsalFileCount,
                additions: rehearsalAdditions,
                deletions: rehearsalDeletions
            }
        };
    }

    function postOpSnapshot() {
        const snapshot = certificationSnapshot();

        snapshot.postOp = {
            status: postOpStatus,
            operation: postOpOperation,
            expectedBaseHead: postOpExpectedBaseHead,
            expectedRoomHead: postOpExpectedRoomHead,
            currentBaseHead: postOpCurrentBaseHead,
            currentRoomHead: postOpCurrentRoomHead,
            currentRelation: postOpCurrentRelation,
            roomBranchUnchanged: postOpRoomUnchanged
        };

        return snapshot;
    }

    function runInspection(mode) {
        if (running || rehearsing || integrating || postOpRunning)
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
        if (running || rehearsing || integrating || postOpRunning)
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
        if (integrating || running || rehearsing || postOpRunning)
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

    function startPostOpVerification(
            operation,
            verifyRepository,
            verifyTeam,
            verifyBase,
            expectedBaseHead,
            expectedRoomHead) {
        postOpRunning = true;
        postOpStatus = "VERIFYING";
        postOpOperation = String(operation || "");
        postOpExpectedBaseHead = String(expectedBaseHead || "");
        postOpExpectedRoomHead = String(expectedRoomHead || "");
        postOpCurrentBaseHead = "";
        postOpCurrentRoomHead = "";
        postOpCurrentRelation = "";
        postOpRoomUnchanged = false;
        available = false;
        action = "POST_OP";
        lastError = "";
        summary = "POST-OP // VERIFYING "
                  + postOpOperation
                  + " RESULT";

        postOpExitSeen = false;
        postOpStdoutSeen = false;
        postOpStderrSeen = false;
        postOpExitCode = -1;
        postOpStdoutText = "";
        postOpStderrText = "";

        postOpProcess.exec([
            "bash",
            "-lc",
            'exec "$HOME/.local/bin/px" verify "$1" "$2" "$3" "$4" "$5"',
            "px-post-op",
            String(verifyRepository || ""),
            String(verifyTeam || ""),
            String(verifyBase || ""),
            postOpExpectedBaseHead,
            postOpExpectedRoomHead
        ]);

        postOpWatchdog.restart();
    }

    function maybeFinishPostOp() {
        if (!postOpRunning
                || !postOpExitSeen
                || !postOpStdoutSeen
                || !postOpStderrSeen)
            return;

        postOpRunning = false;
        postOpWatchdog.stop();

        if (postOpExitCode !== 0) {
            available = false;
            postOpStatus = "VERIFY_FAILED";
            lastError = String(
                postOpStderrText
                || postOpStdoutText
                || ("PX POST-OP EXIT " + postOpExitCode)
            ).trim();
            summary = "POST-OP WARNING // " + lastError;
            postOpFinished();
            return;
        }

        try {
            const data = JSON.parse(
                String(postOpStdoutText || "").trim()
            );
            const status =
                String(data.status || "UNKNOWN").toUpperCase();
            const relation = data.current_room_relation || {};

            postOpStatus = status;
            postOpCurrentBaseHead =
                String(data.current_base_head || "");
            postOpCurrentRoomHead =
                String(data.current_room_head || "");
            postOpCurrentRelation =
                String(relation.status || "UNKNOWN").toUpperCase();
            postOpRoomUnchanged =
                Boolean(data.room_branch_unchanged);

            if (status !== "POST_OP_CLEAN")
                throw new Error(
                    "UNEXPECTED POST-OP STATUS // " + status
                );

            available = true;
            lastError = "";
            action = "POST_OP";
            summary = "POST-OP CLEAN // "
                      + postOpOperation
                      + " // "
                      + String(data.base || "")
                      + "@"
                      + postOpCurrentBaseHead.slice(0, 8)
                      + " // ROOM "
                      + postOpCurrentRelation;

            integrated();
            postOpFinished();
        } catch (error) {
            available = false;
            postOpStatus = "VERIFY_FAILED";
            lastError = "POST-OP PARSE // " + String(error);
            summary = lastError;
            postOpFinished();
        }
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

            const verifyRepository =
                String(data.repository || armedRepository);
            const verifyTeam =
                String(data.team || armedTeam);
            const verifyBase =
                String(data.base || armedBase);
            const verifyBaseHead =
                String(data.new_base_head || "");
            const verifyRoomHead =
                String(data.room_head || armedHead);

            if (!verifyRepository
                    || !verifyTeam
                    || !verifyBase
                    || !verifyBaseHead
                    || !verifyRoomHead)
                throw new Error(
                    "MISSING POST-OP VERIFICATION SNAPSHOT"
                );

            const operation = expectedStatus;

            disarm();

            startPostOpVerification(
                operation,
                verifyRepository,
                verifyTeam,
                verifyBase,
                verifyBaseHead,
                verifyRoomHead
            );
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
        id: postOpProcess

        stdout: StdioCollector {
            onStreamFinished: {
                roomService.postOpStdoutText = this.text;
                roomService.postOpStdoutSeen = true;
                roomService.maybeFinishPostOp();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                roomService.postOpStderrText = this.text;
                roomService.postOpStderrSeen = true;
                roomService.maybeFinishPostOp();
            }
        }

        onExited: function(code, exitStatus) {
            roomService.postOpExitCode = Number(code);
            roomService.postOpExitSeen = true;
            roomService.maybeFinishPostOp();
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
        id: postOpWatchdog
        interval: 20000
        repeat: false

        onTriggered: {
            if (!roomService.postOpRunning)
                return;

            roomService.postOpRunning = false;
            roomService.available = false;
            roomService.postOpStatus = "VERIFY_TIMEOUT";
            roomService.lastError = "PX POST-OP VERIFY TIMEOUT";
            roomService.summary = "POST-OP WARNING // "
                                  + roomService.lastError;
            roomService.postOpFinished();

            if (postOpProcess.running)
                postOpProcess.running = false;
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
