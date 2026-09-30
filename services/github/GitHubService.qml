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
    property int pendingReads: 0

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

        refreshing = true;
        pendingReads = 2;
        lastError = "";

        workflowsProcess.exec([
            "toolbox",
            "run",
            "-c",
            "fedora-toolbox-44",
            "gh",
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
            "toolbox",
            "run",
            "-c",
            "fedora-toolbox-44",
            "gh",
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

    function finishRead() {
        pendingReads = Math.max(0, pendingReads - 1);

        if (pendingReads === 0) {
            refreshing = false;
            watchdog.stop();

            if (!lastError)
                available = true;
        }
    }

    function consumeWorkflows(line) {
        const raw = String(line || "").trim();

        if (!raw)
            return;

        try {
            const rows = JSON.parse(raw);

            if (Array.isArray(rows)) {
                workflowCount = rows.length;
                latestWorkflow = rows.length > 0
                    ? String(rows[0].name || rows[0].path || "UNKNOWN")
                    : "NO WORKFLOWS";
                finishRead();
            }
        } catch (error) {
            lastError = "WORKFLOW PARSE: " + String(error);
            finishRead();
        }
    }

    function consumeRuns(line) {
        const raw = String(line || "").trim();

        if (!raw)
            return;

        try {
            const rows = JSON.parse(raw);

            if (Array.isArray(rows)) {
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

                finishRead();
            }
        } catch (error) {
            lastError = "RUN PARSE: " + String(error);
            finishRead();
        }
    }

    Process {
        id: workflowsProcess

        stdout: SplitParser {
            onRead: function(line) {
                githubService.consumeWorkflows(line);
            }
        }

        stderr: SplitParser {
            onRead: function(line) {
                const message = String(line || "").trim();

                if (message.length > 0)
                    githubService.lastError = message;
            }
        }
    }

    Process {
        id: runsProcess

        stdout: SplitParser {
            onRead: function(line) {
                githubService.consumeRuns(line);
            }
        }

        stderr: SplitParser {
            onRead: function(line) {
                const message = String(line || "").trim();

                if (message.length > 0)
                    githubService.lastError = message;
            }
        }
    }

    Timer {
        id: watchdog
        interval: 10000
        repeat: false

        onTriggered: {
            githubService.refreshing = false;
            githubService.pendingReads = 0;
            githubService.available = false;

            if (!githubService.lastError)
                githubService.lastError = "GITHUB READ TIMEOUT";
        }
    }
}
