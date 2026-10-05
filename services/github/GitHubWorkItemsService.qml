import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property string repoSlug: ""

    property bool issuesBusy: false
    property bool pullsBusy: false

    property var issues: []
    property var pulls: []

    property string issuesStateText: "ISSUES // READY"
    property string pullsStateText: "PULLS // READY"
    property string issuesError: ""
    property string pullsError: ""

    property bool issuesStdoutSeen: false
    property bool issuesStderrSeen: false
    property bool issuesExitSeen: false
    property int issuesExitCode: -1
    property string issuesStdout: ""
    property string issuesStderr: ""

    property bool pullsStdoutSeen: false
    property bool pullsStderrSeen: false
    property bool pullsExitSeen: false
    property int pullsExitCode: -1
    property string pullsStdout: ""
    property string pullsStderr: ""

    signal issuesRefreshed()
    signal pullsRefreshed()

    function rowNumber(row) {
        return Number((row || {}).number || 0);
    }

    function rowTitle(row) {
        return String((row || {}).title || "UNTITLED");
    }

    function rowState(row) {
        return String((row || {}).state || "UNKNOWN").toUpperCase();
    }

    function rowUrl(row) {
        return String((row || {}).url || "");
    }

    function rowAuthor(row) {
        const author = (row || {}).author || {};
        return String(author.login || author.name || "");
    }

    function rowUpdated(row) {
        return String((row || {}).updatedAt || "");
    }

    function issueLabels(row) {
        const labels = Array.isArray((row || {}).labels)
            ? row.labels
            : [];
        const out = [];

        for (let i = 0; i < labels.length; ++i) {
            const label = labels[i] || {};
            const name = String(label.name || "").trim();

            if (name)
                out.push(name);
        }

        return out;
    }

    function pullBranches(row) {
        const source = String((row || {}).headRefName || "");
        const target = String((row || {}).baseRefName || "");

        if (!source && !target)
            return "";

        return (source || "?") + " → " + (target || "?");
    }

    function pullIsDraft(row) {
        return !!((row || {}).isDraft);
    }

    function refreshIssues(repo) {
        const cleanRepo = String(repo || repoSlug || "").trim();

        if (issuesBusy)
            return false;

        if (!cleanRepo) {
            issuesError = "ISSUES UNAVAILABLE // ACTIVE REPOSITORY MISSING";
            issuesStateText = issuesError;
            issues = [];
            return false;
        }

        issuesBusy = true;
        issuesError = "";
        issuesStateText = "READING ISSUES";
        issuesStdoutSeen = false;
        issuesStderrSeen = false;
        issuesExitSeen = false;
        issuesExitCode = -1;
        issuesStdout = "";
        issuesStderr = "";

        issuesProcess.exec([
            "bash",
            "-lc",
            'exec gh issue list --repo "$1" --state all --limit 1000 --json number,title,state,url,labels,author,updatedAt',
            "pa-github-issues",
            cleanRepo
        ]);
        issuesWatchdog.restart();
        return true;
    }

    function refreshPulls(repo) {
        const cleanRepo = String(repo || repoSlug || "").trim();

        if (pullsBusy)
            return false;

        if (!cleanRepo) {
            pullsError = "PULLS UNAVAILABLE // ACTIVE REPOSITORY MISSING";
            pullsStateText = pullsError;
            pulls = [];
            return false;
        }

        pullsBusy = true;
        pullsError = "";
        pullsStateText = "READING PULL REQUESTS";
        pullsStdoutSeen = false;
        pullsStderrSeen = false;
        pullsExitSeen = false;
        pullsExitCode = -1;
        pullsStdout = "";
        pullsStderr = "";

        pullsProcess.exec([
            "bash",
            "-lc",
            'exec gh pr list --repo "$1" --state all --limit 1000 --json number,title,state,url,isDraft,author,headRefName,baseRefName,updatedAt',
            "pa-github-pulls",
            cleanRepo
        ]);
        pullsWatchdog.restart();
        return true;
    }

    function maybeFinishIssues() {
        if (!issuesBusy
                || !issuesStdoutSeen
                || !issuesStderrSeen
                || !issuesExitSeen)
            return;

        issuesBusy = false;
        issuesWatchdog.stop();

        const output = String(issuesStdout || "").trim();
        const error = String(issuesStderr || "").trim();

        if (issuesExitCode !== 0) {
            issuesError = error || output || "ISSUE LIST FAILED";
            issuesStateText = "ERROR // " + issuesError;
            issues = [];
            issuesRefreshed();
            return;
        }

        try {
            const parsed = JSON.parse(output || "[]");
            issues = Array.isArray(parsed) ? parsed : [];
            issuesStateText =
                "ISSUES READY // "
                + String(issues.length);
            issuesError = "";
        } catch (parseError) {
            issues = [];
            issuesError = "ISSUE RESPONSE PARSE // " + String(parseError);
            issuesStateText = "ERROR // " + issuesError;
        }

        issuesRefreshed();
    }

    function maybeFinishPulls() {
        if (!pullsBusy
                || !pullsStdoutSeen
                || !pullsStderrSeen
                || !pullsExitSeen)
            return;

        pullsBusy = false;
        pullsWatchdog.stop();

        const output = String(pullsStdout || "").trim();
        const error = String(pullsStderr || "").trim();

        if (pullsExitCode !== 0) {
            pullsError = error || output || "PULL REQUEST LIST FAILED";
            pullsStateText = "ERROR // " + pullsError;
            pulls = [];
            pullsRefreshed();
            return;
        }

        try {
            const parsed = JSON.parse(output || "[]");
            pulls = Array.isArray(parsed) ? parsed : [];
            pullsStateText =
                "PULLS READY // "
                + String(pulls.length);
            pullsError = "";
        } catch (parseError) {
            pulls = [];
            pullsError = "PULL RESPONSE PARSE // " + String(parseError);
            pullsStateText = "ERROR // " + pullsError;
        }

        pullsRefreshed();
    }

    Process {
        id: issuesProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.issuesStdout = this.text;
                root.issuesStdoutSeen = true;
                root.maybeFinishIssues();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.issuesStderr = this.text;
                root.issuesStderrSeen = true;
                root.maybeFinishIssues();
            }
        }

        onExited: function(exitCode, exitStatus) {
            root.issuesExitCode = Number(exitCode);
            root.issuesExitSeen = true;
            root.maybeFinishIssues();
        }
    }

    Process {
        id: pullsProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.pullsStdout = this.text;
                root.pullsStdoutSeen = true;
                root.maybeFinishPulls();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.pullsStderr = this.text;
                root.pullsStderrSeen = true;
                root.maybeFinishPulls();
            }
        }

        onExited: function(exitCode, exitStatus) {
            root.pullsExitCode = Number(exitCode);
            root.pullsExitSeen = true;
            root.maybeFinishPulls();
        }
    }

    Timer {
        id: issuesWatchdog
        interval: 120000
        repeat: false

        onTriggered: {
            root.issuesBusy = false;
            root.issuesError = "ISSUE LIST TIMEOUT";
            root.issuesStateText = "ERROR // " + root.issuesError;

            if (issuesProcess.running)
                issuesProcess.running = false;

            root.issuesRefreshed();
        }
    }

    Timer {
        id: pullsWatchdog
        interval: 120000
        repeat: false

        onTriggered: {
            root.pullsBusy = false;
            root.pullsError = "PULL REQUEST LIST TIMEOUT";
            root.pullsStateText = "ERROR // " + root.pullsError;

            if (pullsProcess.running)
                pullsProcess.running = false;

            root.pullsRefreshed();
        }
    }
}
