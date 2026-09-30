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

    function finishWorkflow(exitCode, stdoutText, stderrText) {
        if (!refreshing || workflowDone)
            return;

        if (Number(exitCode) !== 0) {
            recordError("WORKFLOWS EXIT " + String(exitCode) + " // ", stderrText || "NO STDERR");
        } else {
            try {
                parseWorkflows(stdoutText);
            } catch (error) {
                recordError("WORKFLOW PARSE // ", String(error));
            }
        }

        workflowDone = true;
        finishIfComplete();
    }

    function finishRuns(exitCode, stdoutText, stderrText) {
        if (!refreshing || runsDone)
            return;

        if (Number(exitCode) !== 0) {
            recordError("RUNS EXIT " + String(exitCode) + " // ", stderrText || "NO STDERR");
        } else {
            try {
                parseRuns(stdoutText);
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
            id: workflowsStdout
        }

        stderr: StdioCollector {
            id: workflowsStderr
        }

        onExited: function(exitCode, exitStatus) {
            githubService.finishWorkflow(
                exitCode,
                workflowsStdout.text,
                workflowsStderr.text
            );
        }
    }

    Process {
        id: runsProcess

        stdout: StdioCollector {
            id: runsStdout
        }

        stderr: StdioCollector {
            id: runsStderr
        }

        onExited: function(exitCode, exitStatus) {
            githubService.finishRuns(
                exitCode,
                runsStdout.text,
                runsStderr.text
            );
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
