import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: githubService

    property string originUrl: ""

    readonly property string repoSlug: {
        const raw = String(originUrl || "").trim();

        if (!raw || raw === "NOT CONNECTED" || raw === "NO ORIGIN")
            return "";

        let value = raw;

        if (value.indexOf("git@github.com:") === 0)
            value = value.slice("git@github.com:".length);
        else if (value.indexOf("ssh://git@github.com/") === 0)
            value = value.slice("ssh://git@github.com/".length);
        else if (value.indexOf("https://github.com/") === 0)
            value = value.slice("https://github.com/".length);
        else if (value.indexOf("http://github.com/") === 0)
            value = value.slice("http://github.com/".length);
        else
            return "";

        if (value.endsWith(".git"))
            value = value.slice(0, -4);

        return value;
    }

    property bool available: false
    property bool refreshing: false
    property bool workflowDone: false
    property bool runsDone: false

    property bool workflowExitSeen: false
    property bool workflowStdoutSeen: false
    property bool workflowStderrSeen: false
    property int workflowExitCode: -1
    property string workflowStdoutText: ""
    property string workflowStderrText: ""

    property bool runsExitSeen: false
    property bool runsStdoutSeen: false
    property bool runsStderrSeen: false
    property int runsExitCode: -1
    property string runsStdoutText: ""
    property string runsStderrText: ""

    property int workflowCount: 0
    property string latestWorkflow: "NOT REQUESTED"
    property string latestRunStatus: "NOT REQUESTED"
    property string latestRunConclusion: ""
    property string latestRunBranch: ""

    property string lastError: ""

    function refresh() {
        if (refreshing)
            return;

        if (!repoSlug) {
            available = false;
            lastError = "ORIGIN IS NOT A GITHUB REPOSITORY";
            return;
        }

        available = false;
        refreshing = true;
        workflowDone = false;
        runsDone = false;
        lastError = "";

        workflowExitSeen = false;
        workflowStdoutSeen = false;
        workflowStderrSeen = false;
        workflowExitCode = -1;
        workflowStdoutText = "";
        workflowStderrText = "";

        runsExitSeen = false;
        runsStdoutSeen = false;
        runsStderrSeen = false;
        runsExitCode = -1;
        runsStdoutText = "";
        runsStderrText = "";

        workflowsProcess.exec([
            "/usr/bin/toolbox",
            "run",
            "-c",
            "fedora-toolbox-44",
            "/usr/bin/gh",
            "workflow",
            "list",
            "-R",
            repoSlug,
            "--limit",
            "100",
            "--json",
            "name,state,path"
        ]);

        runsProcess.exec([
            "/usr/bin/toolbox",
            "run",
            "-c",
            "fedora-toolbox-44",
            "/usr/bin/gh",
            "run",
            "list",
            "-R",
            repoSlug,
            "--limit",
            "8",
            "--json",
            "databaseId,workflowName,status,conclusion,headBranch,createdAt"
        ]);

        watchdog.restart();
    }

    function recordError(prefix, message) {
        const clean = String(message || "").trim();

        if (!clean)
            return;

        if (!lastError)
            lastError = prefix + clean;
    }

    function parseWorkflows(payload) {
        const raw = String(payload || "").trim();

        if (!raw)
            throw new Error("EMPTY WORKFLOW RESPONSE");

        const rows = JSON.parse(raw);

        if (!Array.isArray(rows))
            throw new Error("WORKFLOW RESPONSE IS NOT AN ARRAY");

        workflowCount = rows.length;
        latestWorkflow = rows.length > 0
            ? String(rows[0].name || rows[0].path || "UNKNOWN")
            : "NO WORKFLOWS";
    }

    function parseRuns(payload) {
        const raw = String(payload || "").trim();

        if (!raw)
            throw new Error("EMPTY RUN RESPONSE");

        const rows = JSON.parse(raw);

        if (!Array.isArray(rows))
            throw new Error("RUN RESPONSE IS NOT AN ARRAY");

        if (rows.length > 0) {
            const run = rows[0];

            latestWorkflow = String(run.workflowName || latestWorkflow || "UNKNOWN");
            latestRunStatus = String(run.status || "UNKNOWN").toUpperCase();
            latestRunConclusion = String(run.conclusion || "").toUpperCase();
            latestRunBranch = String(run.headBranch || "");
        } else {
            latestRunStatus = "NO RUNS";
            latestRunConclusion = "";
            latestRunBranch = "";
        }
    }

    function maybeFinishWorkflow() {
        if (!refreshing || workflowDone)
            return;

        if (!workflowExitSeen || !workflowStdoutSeen || !workflowStderrSeen)
            return;

        if (workflowExitCode !== 0) {
            recordError(
                "WORKFLOWS EXIT " + String(workflowExitCode) + " // ",
                workflowStderrText || "NO STDERR"
            );
        } else {
            try {
                parseWorkflows(workflowStdoutText);
            } catch (error) {
                recordError("WORKFLOW PARSE // ", String(error));
            }
        }

        workflowDone = true;
        finishIfComplete();
    }

    function maybeFinishRuns() {
        if (!refreshing || runsDone)
            return;

        if (!runsExitSeen || !runsStdoutSeen || !runsStderrSeen)
            return;

        if (runsExitCode !== 0) {
            recordError(
                "RUNS EXIT " + String(runsExitCode) + " // ",
                runsStderrText || "NO STDERR"
            );
        } else {
            try {
                parseRuns(runsStdoutText);
            } catch (error) {
                recordError("RUN PARSE // ", String(error));
            }
        }

        runsDone = true;
        finishIfComplete();
    }

    function finishIfComplete() {
        if (!workflowDone || !runsDone)
            return;

        refreshing = false;
        watchdog.stop();
        available = !lastError;
    }

    Process {
        id: workflowsProcess

        stdout: StdioCollector {
            onStreamFinished: {
                githubService.workflowStdoutText = this.text;
                githubService.workflowStdoutSeen = true;
                githubService.maybeFinishWorkflow();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                githubService.workflowStderrText = this.text;
                githubService.workflowStderrSeen = true;
                githubService.maybeFinishWorkflow();
            }
        }

        onExited: function(exitCode, exitStatus) {
            githubService.workflowExitCode = Number(exitCode);
            githubService.workflowExitSeen = true;
            githubService.maybeFinishWorkflow();
        }
    }

    Process {
        id: runsProcess

        stdout: StdioCollector {
            onStreamFinished: {
                githubService.runsStdoutText = this.text;
                githubService.runsStdoutSeen = true;
                githubService.maybeFinishRuns();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                githubService.runsStderrText = this.text;
                githubService.runsStderrSeen = true;
                githubService.maybeFinishRuns();
            }
        }

        onExited: function(exitCode, exitStatus) {
            githubService.runsExitCode = Number(exitCode);
            githubService.runsExitSeen = true;
            githubService.maybeFinishRuns();
        }
    }

    Timer {
        id: watchdog
        interval: 12000
        repeat: false

        onTriggered: {
            if (!githubService.refreshing)
                return;

            githubService.refreshing = false;
            githubService.available = false;
            githubService.lastError = "GITHUB PROCESS TIMEOUT";

            if (workflowsProcess.running)
                workflowsProcess.running = false;

            if (runsProcess.running)
                runsProcess.running = false;
        }
    }
}
