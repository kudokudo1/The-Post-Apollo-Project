import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: auditService

    property string repository: ""

    property bool running: false
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

    property string lastError: ""

    property bool exitSeen: false
    property bool stdoutSeen: false
    property bool stderrSeen: false
    property int exitCode: -1
    property string stdoutText: ""
    property string stderrText: ""

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
        lastError = "";
    }

    function runAudit() {
        if (running)
            return;

        const target = String(repository || "").trim();

        resetResult();

        if (!target) {
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
            'exec "$HOME/.local/bin/px" audit "$1"',
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

        const latest = runs.latest || null;

        if (latest) {
            latestWorkflow = String(latest.workflow || "");
            latestRunStatus = String(latest.status || "").toUpperCase();
            latestRunConclusion = String(latest.conclusion || "").toUpperCase();
            latestRunBranch = String(latest.branch || "");
        }
    }

    function maybeFinish() {
        if (!running || !exitSeen || !stdoutSeen || !stderrSeen)
            return;

        running = false;
        watchdog.stop();

        if (exitCode !== 0) {
            available = false;
            lastError = String(stderrText || stdoutText || ("PX AUDIT EXIT " + exitCode)).trim();
            return;
        }

        try {
            parseAudit(stdoutText);
            available = true;
            lastError = "";
            audited();
        } catch (error) {
            available = false;
            lastError = "AUDIT PARSE // " + String(error);
        }
    }

    Process {
        id: auditProcess

        stdout: StdioCollector {
            onStreamFinished: {
                auditService.stdoutText = this.text;
                auditService.stdoutSeen = true;
                auditService.maybeFinish();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                auditService.stderrText = this.text;
                auditService.stderrSeen = true;
                auditService.maybeFinish();
            }
        }

        onExited: function(code, exitStatus) {
            auditService.exitCode = Number(code);
            auditService.exitSeen = true;
            auditService.maybeFinish();
        }
    }

    Timer {
        id: watchdog
        interval: 10000
        repeat: false

        onTriggered: {
            if (!auditService.running)
                return;

            auditService.running = false;
            auditService.available = false;
            auditService.lastError = "PX AUDIT TIMEOUT";

            if (auditProcess.running)
                auditProcess.running = false;
        }
    }
}
