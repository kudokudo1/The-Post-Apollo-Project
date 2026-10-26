import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: auditService

    readonly property bool subprocessLagProbeEnabled:
        String(Quickshell.env("POST_APOLLO_SUBPROCESS_LAG_PROBE") || "").trim() === "1"

    // Opt-in only; static stage IDs and counts, never subprocess output.
    function traceSubprocessLag(stage, size) {
        if (!subprocessLagProbeEnabled)
            return;
        console.warn("SYNTAGMA_SUBPROCESS_PROBE // service=hospital-audit"
                     + " stage=" + stage + " size=" + Number(size || 0)
                     + " tsMs=" + Date.now());
    }

    property string repository: ""

    property bool running: false
    property bool quietRun: false
    readonly property bool visibleRunning: running && !quietRun
    property bool available: false

    property string status: "NOT RUN"
    property string defaultBranch: ""
    property int workflowCount: 0
    property int activeWorkflowCount: 0
    property int runCount: 0
    property string latestWorkflow: ""
    property string latestRunStatus: ""
    property string latestRunConclusion: ""
    property string latestRunBranch: ""
    property var rooms: []

    property string lastError: ""

    property bool exitSeen: false
    property bool stdoutSeen: false
    property bool stderrSeen: false
    property int exitCode: -1
    property string stdoutText: ""
    property string stderrText: ""
    property string lastAuditPayload: ""

    signal audited()

    function resetResult() {
        available = false;
        status = "NOT RUN";
        defaultBranch = "";
        workflowCount = 0;
        activeWorkflowCount = 0;
        runCount = 0;
        latestWorkflow = "";
        latestRunStatus = "";
        latestRunConclusion = "";
        latestRunBranch = "";
        rooms = [];
        lastAuditPayload = "";
        lastError = "";
    }

    function runAudit(quiet) {
        if (running)
            return;

        quietRun = Boolean(quiet);

        const target = String(repository || "").trim();

        // Preserve the last good room/audit snapshot while a background
        // refresh is in flight. Floor changes call resetResult() explicitly,
        // so stale data cannot leak between repositories.
        lastError = "";

        if (!target) {
            resetResult();
            quietRun = false;
            lastError = "NO GITHUB REPOSITORY";
            return;
        }

        running = true;
        exitSeen = false;
        stdoutSeen = false;
        stderrSeen = false;
        exitCode = -1;
        stdoutText = "";
        stderrText = "";

        auditProcess.exec([
            "bash",
            "-lc",
            'px="$HOME/.local/share/post-apollo-dev-runtime/bin/px"; '
                + '[ -x "$px" ] || px="$HOME/.local/bin/px"; '
                + 'exec "$px" audit "$1"',
            "px-audit",
            target
        ]);

        watchdog.restart();
    }

    function parseAudit(payload) {
        const raw = String(payload || "").trim();

        if (!raw)
            throw new Error("EMPTY AUDIT RESPONSE");

        const data = JSON.parse(raw);

        status = String(data.status || "UNKNOWN").toUpperCase();
        defaultBranch = String(data.default_branch || "");

        const workflows = data.workflows || {};
        workflowCount = Number(workflows.count || 0);
        activeWorkflowCount = Number(workflows.active || 0);

        const runs = data.runs || {};
        runCount = Number(runs.count || 0);

        const roomBlock = data.rooms || {};
        rooms = Array.isArray(roomBlock.items) ? roomBlock.items : [];

        const latest = runs.latest || null;

        if (latest) {
            latestWorkflow = String(latest.workflow || "");
            latestRunStatus = String(latest.status || "").toUpperCase();
            latestRunConclusion = String(latest.conclusion || "").toUpperCase();
            latestRunBranch = String(latest.branch || "");
        }
    }

    function roomFor(team) {
        const wanted = String(team || "");

        for (let i = 0; i < rooms.length; ++i) {
            const room = rooms[i] || {};

            if (String(room.team || "") === wanted)
                return room;
        }

        return null;
    }

    function roomState(team) {
        const room = roomFor(team);
        return room ? String(room.state || "UNKNOWN").toUpperCase() : "WAITING";
    }

    function roomLabel(team) {
        if (visibleRunning)
            return "READING";

        const room = roomFor(team);

        if (!room)
            return available ? "NO DATA" : "WAITING AUDIT";

        const state = String(room.state || "UNKNOWN").toUpperCase();
        const ahead = Number(room.ahead || 0);
        const behind = Number(room.behind || 0);
        const head = String(room.head || "").slice(0, 8);

        if (state === "IN_MAIN")
            return head ? "IN MAIN • " + head : "IN MAIN";

        if (state === "AT_MAIN")
            return "AT MAIN";

        if (state === "AHEAD")
            return "AHEAD +" + ahead;

        if (state === "DIVERGED")
            return "DIVERGED +" + ahead + "/-" + behind;

        if (state === "MISSING")
            return "MISSING";

        return state;
    }

    function roomBranch(team) {
        const room = roomFor(team);
        return room ? String(room.branch || "") : "";
    }

    function maybeFinish() {
        if (!running || !exitSeen || !stdoutSeen || !stderrSeen)
            return;

        traceSubprocessLag("complete:begin", stdoutText.length);
        const wasQuiet = quietRun;
        const payload = String(stdoutText || "").trim();

        running = false;
        quietRun = false;
        watchdog.stop();

        if (exitCode !== 0) {
            available = false;
            lastError = String(stderrText || stdoutText || ("PX AUDIT EXIT " + exitCode)).trim();
            return;
        }

        // Background audits are observation-only until the result actually
        // differs from the last published audit snapshot.
        if (wasQuiet
                && available
                && payload.length > 0
                && payload === lastAuditPayload) {
            lastError = "";
            return;
        }

        try {
            traceSubprocessLag("parse:begin", payload.length);
            parseAudit(payload);
            traceSubprocessLag("parse:end", rooms.length);
            lastAuditPayload = payload;
            available = true;
            lastError = "";
            traceSubprocessLag("audited:begin", rooms.length);
            audited();
            traceSubprocessLag("audited:end", rooms.length);
        } catch (error) {
            available = false;
            lastError = "AUDIT PARSE // " + String(error);
        }
    }

    Process {
        id: auditProcess

        stdout: StdioCollector {
            onStreamFinished: {
                auditService.traceSubprocessLag("stdout:begin", this.text.length);
                auditService.stdoutText = this.text;
                auditService.stdoutSeen = true;
                auditService.maybeFinish();
                auditService.traceSubprocessLag("stdout:end", 0);
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                auditService.traceSubprocessLag("stderr:begin", this.text.length);
                auditService.stderrText = this.text;
                auditService.stderrSeen = true;
                auditService.maybeFinish();
                auditService.traceSubprocessLag("stderr:end", 0);
            }
        }

        onExited: function(code, exitStatus) {
            auditService.traceSubprocessLag("exit:begin", 0);
            auditService.exitCode = Number(code);
            auditService.exitSeen = true;
            auditService.maybeFinish();
            auditService.traceSubprocessLag("exit:end", 0);
        }
    }

    Timer {
        id: watchdog
        interval: 20000
        repeat: false

        onTriggered: {
            if (!auditService.running)
                return;

            auditService.running = false;
            auditService.quietRun = false;
            auditService.available = false;
            auditService.lastError = "PX AUDIT TIMEOUT";

            if (auditProcess.running)
                auditProcess.running = false;
        }
    }
}
