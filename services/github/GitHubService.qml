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
    property int runCount: 0
    property var workflows: []
    property var runs: []
    property string latestWorkflow: "NOT REQUESTED"
    property string latestRunStatus: "NOT REQUESTED"
    property string latestRunConclusion: ""
    property string latestRunBranch: ""

    // Exact-SHA evidence query state. This is separate from the normal
    // recent-runs surface so evidence collection never changes GitW's view.
    property bool evidenceRunsBusy: false
    property string evidenceRunsSha: ""
    property var evidenceRuns: []
    property string evidenceRunsError: ""
    property bool evidenceRunsExitSeen: false
    property bool evidenceRunsStdoutSeen: false
    property bool evidenceRunsStderrSeen: false
    property int evidenceRunsExitCode: -1
    property string evidenceRunsStdoutText: ""
    property string evidenceRunsStderrText: ""

    signal evidenceRunsReady(string sha, var runs, string error)

    property bool inspectorBusy: false
    property string inspectorRunId: ""
    property var inspectedRun: ({})
    property var inspectorJobs: []
    property string inspectorLogText: ""
    property string inspectorError: ""

    property bool inspectorMetaExitSeen: false
    property bool inspectorMetaStdoutSeen: false
    property bool inspectorMetaStderrSeen: false
    property int inspectorMetaExitCode: -1
    property string inspectorMetaStdoutText: ""
    property string inspectorMetaStderrText: ""

    property bool inspectorLogsExitSeen: false
    property bool inspectorLogsStdoutSeen: false
    property bool inspectorLogsStderrSeen: false
    property int inspectorLogsExitCode: -1
    property string inspectorLogsStdoutText: ""
    property string inspectorLogsStderrText: ""

    property bool factoryBusy: false
    property string factoryMode: ""
    property bool factoryExitSeen: false
    property bool factoryStdoutSeen: false
    property bool factoryStderrSeen: false
    property int factoryExitCode: -1
    property string factoryStdoutText: ""
    property string factoryStderrText: ""
    property string factoryYaml: ""
    property string factoryPath: ""
    property string factoryValidationStatus: "NOT PREVIEWED"
    property string factoryValidationValidator: ""
    property string factoryValidationMessage: ""
    property string factoryInstallBranch: ""
    property string factoryPullRequest: ""
    property string factoryInstallCommit: ""
    property string factoryLastTemplate: ""
    property string factoryLastTrigger: ""
    property string factoryLastSlug: ""

    property bool actionBusy: false
    property string actionKind: ""
    property string actionResult: "READY"
    property bool actionExitSeen: false
    property bool actionStdoutSeen: false
    property bool actionStderrSeen: false
    property int actionExitCode: -1
    property string actionStdoutText: ""
    property string actionStderrText: ""

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
        runCount = 0;

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

        // GitHub semantics belong to PX. This surface only supplies the
        // repository identity and consumes PX's stable JSON contract.
        workflowsProcess.exec([
            "bash",
            "-lc",
            'exec "$HOME/.local/bin/px" workflows "$1"',
            "px-workflows",
            repoSlug
        ]);

        runsProcess.exec([
            "bash",
            "-lc",
            'exec "$HOME/.local/bin/px" runs "$1" 8',
            "px-runs",
            repoSlug
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

        if (!raw) {
            workflows = [];
            workflowCount = 0;
            latestWorkflow = "NO WORKFLOWS";
            return;
        }

        const rows = JSON.parse(raw);

        if (!Array.isArray(rows))
            throw new Error("WORKFLOW RESPONSE IS NOT AN ARRAY");

        workflows = rows;
        workflowCount = rows.length;
        latestWorkflow = rows.length > 0
            ? String(rows[0].name || rows[0].path || "UNKNOWN")
            : "NO WORKFLOWS";
    }

    function parseRuns(payload) {
        const raw = String(payload || "").trim();

        if (!raw) {
            runs = [];
            runCount = 0;
            latestRunStatus = "NO RUNS";
            latestRunConclusion = "";
            latestRunBranch = "";
            return;
        }

        const rows = JSON.parse(raw);

        if (!Array.isArray(rows))
            throw new Error("RUN RESPONSE IS NOT AN ARRAY");

        runs = rows;
        runCount = rows.length;

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

    function requestEvidenceRuns(sha) {
        const cleanSha = String(sha || "").trim();

        if (!repoSlug) {
            evidenceRunsError = "ORIGIN IS NOT A GITHUB REPOSITORY";
            evidenceRunsReady(cleanSha, [], evidenceRunsError);
            return false;
        }

        if (!cleanSha) {
            evidenceRunsError = "COMMIT SHA REQUIRED";
            evidenceRunsReady("", [], evidenceRunsError);
            return false;
        }

        if (evidenceRunsBusy)
            return false;

        evidenceRunsBusy = true;
        evidenceRunsSha = cleanSha;
        evidenceRuns = [];
        evidenceRunsError = "";
        evidenceRunsExitSeen = false;
        evidenceRunsStdoutSeen = false;
        evidenceRunsStderrSeen = false;
        evidenceRunsExitCode = -1;
        evidenceRunsStdoutText = "";
        evidenceRunsStderrText = "";

        evidenceRunsProcess.exec([
            "bash",
            "-lc",
            'exec "$HOME/.local/bin/px" runs "$1" 100 "$2"',
            "px-evidence-runs",
            repoSlug,
            cleanSha
        ]);

        evidenceRunsWatchdog.restart();
        return true;
    }

    function maybeFinishEvidenceRuns() {
        if (!evidenceRunsBusy)
            return;

        if (!evidenceRunsExitSeen
                || !evidenceRunsStdoutSeen
                || !evidenceRunsStderrSeen) {
            return;
        }

        const requestSha = evidenceRunsSha;
        let rows = [];
        let error = "";

        if (evidenceRunsExitCode === 0) {
            try {
                const raw = String(evidenceRunsStdoutText || "").trim();
                rows = raw ? JSON.parse(raw) : [];

                if (!Array.isArray(rows))
                    throw new Error("EVIDENCE RUN RESPONSE IS NOT AN ARRAY");
            } catch (parseError) {
                error = "EVIDENCE RUN PARSE // " + String(parseError);
                rows = [];
            }
        } else {
            error = String(
                evidenceRunsStderrText
                || evidenceRunsStdoutText
                || "PX EVIDENCE RUN QUERY FAILED"
            ).trim();
        }

        evidenceRuns = rows;
        evidenceRunsError = error;
        evidenceRunsBusy = false;
        evidenceRunsWatchdog.stop();
        evidenceRunsReady(requestSha, rows, error);
    }

    function inspectRun(runId) {
        const cleanRunId = String(runId || "").trim();

        if (!repoSlug || !cleanRunId)
            return;

        inspectorBusy = true;
        inspectorRunId = cleanRunId;
        inspectedRun = ({});
        inspectorJobs = [];
        inspectorLogText = "";
        inspectorError = "";

        inspectorMetaExitSeen = false;
        inspectorMetaStdoutSeen = false;
        inspectorMetaStderrSeen = false;
        inspectorMetaExitCode = -1;
        inspectorMetaStdoutText = "";
        inspectorMetaStderrText = "";

        inspectorLogsExitSeen = false;
        inspectorLogsStdoutSeen = false;
        inspectorLogsStderrSeen = false;
        inspectorLogsExitCode = -1;
        inspectorLogsStdoutText = "";
        inspectorLogsStderrText = "";

        inspectorProcess.exec([
            "bash",
            "-lc",
            'exec "$HOME/.local/bin/px" inspect "$1" "$2"',
            "px-inspect",
            repoSlug,
            cleanRunId
        ]);

        inspectorLogsProcess.exec([
            "bash",
            "-lc",
            'exec "$HOME/.local/bin/px" logs "$1" "$2"',
            "px-logs",
            repoSlug,
            cleanRunId
        ]);

        inspectorWatchdog.restart();
    }

    function parseInspectorMetadata(payload) {
        const raw = String(payload || "").trim();

        if (!raw)
            throw new Error("PX INSPECT RETURNED NO JSON");

        const data = JSON.parse(raw);

        inspectedRun = data || ({});
        inspectorJobs =
            data && Array.isArray(data.jobs)
            ? data.jobs
            : [];
    }

    function maybeFinishInspector() {
        if (!inspectorBusy)
            return;

        const metaDone =
            inspectorMetaExitSeen
            && inspectorMetaStdoutSeen
            && inspectorMetaStderrSeen;

        const logsDone =
            inspectorLogsExitSeen
            && inspectorLogsStdoutSeen
            && inspectorLogsStderrSeen;

        if (!metaDone || !logsDone)
            return;

        if (inspectorMetaExitCode === 0) {
            try {
                parseInspectorMetadata(inspectorMetaStdoutText);
            } catch (error) {
                inspectorError = "INSPECT PARSE // " + String(error);
            }
        } else {
            inspectorError =
                String(
                    inspectorMetaStderrText
                    || inspectorMetaStdoutText
                    || "PX INSPECT FAILED"
                ).trim();
        }

        if (inspectorLogsExitCode === 0) {
            inspectorLogText = String(inspectorLogsStdoutText || "");
        } else {
            const logError =
                String(
                    inspectorLogsStderrText
                    || inspectorLogsStdoutText
                    || "RUN LOGS UNAVAILABLE"
                ).trim();

            inspectorLogText =
                "LOGS UNAVAILABLE // "
                + logError;
        }

        inspectorBusy = false;
        inspectorWatchdog.stop();
    }

    function runWorkflow(workflowPath) {
        runRemoteAction("run", workflowPath);
    }

    function runWorkflowBatch(workflowPaths) {
        if (actionBusy || refreshing)
            return;

        if (!repoSlug) {
            actionResult = "ERROR // NO GITHUB REPOSITORY";
            return;
        }

        const targets = Array.isArray(workflowPaths)
            ? workflowPaths
                .map(function(path) { return String(path || "").trim(); })
                .filter(function(path) { return path.length > 0; })
            : [];

        if (targets.length === 0) {
            actionResult = "ERROR // QUEUE EMPTY";
            return;
        }

        actionBusy = true;
        actionKind = "batch";
        actionResult = "QUEUE // DISPATCHING " + String(targets.length);
        actionExitSeen = false;
        actionStdoutSeen = false;
        actionStderrSeen = false;
        actionExitCode = -1;
        actionStdoutText = "";
        actionStderrText = "";

        const args = [
            "bash",
            "-lc",
            'repo="$1"; shift; for workflow in "$@"; do "$HOME/.local/bin/px" run "$repo" "$workflow" || exit $?; done',
            "px-batch",
            repoSlug
        ];

        for (let i = 0; i < targets.length; ++i)
            args.push(targets[i]);

        remoteActionProcess.exec(args);
        actionWatchdog.restart();
    }

    function rerunRun(runId) {
        runRemoteAction("rerun", String(runId || ""));
    }

    function cancelRun(runId) {
        runRemoteAction("cancel", String(runId || ""));
    }

    function runRemoteAction(kind, target) {
        if (actionBusy || refreshing)
            return;

        if (!repoSlug) {
            actionResult = "ERROR // NO GITHUB REPOSITORY";
            return;
        }

        const cleanTarget = String(target || "").trim();

        if (!cleanTarget) {
            actionResult = "ERROR // TARGET REQUIRED";
            return;
        }

        if (kind !== "run" && kind !== "rerun" && kind !== "cancel") {
            actionResult = "ERROR // UNKNOWN ACTION";
            return;
        }

        actionBusy = true;
        actionKind = kind;
        actionResult = kind.toUpperCase() + " // RUNNING";
        actionExitSeen = false;
        actionStdoutSeen = false;
        actionStderrSeen = false;
        actionExitCode = -1;
        actionStdoutText = "";
        actionStderrText = "";

        remoteActionProcess.exec([
            "bash",
            "-lc",
            'exec "$HOME/.local/bin/px" "$1" "$2" "$3"',
            "px-action",
            kind,
            repoSlug,
            cleanTarget
        ]);

        actionWatchdog.restart();
    }

    function maybeFinishRemoteAction() {
        if (!actionBusy)
            return;

        if (!actionExitSeen || !actionStdoutSeen || !actionStderrSeen)
            return;

        actionBusy = false;
        actionWatchdog.stop();

        if (actionExitCode === 0) {
            actionResult =
                actionKind === "batch"
                ? "QUEUE // DISPATCHED"
                : actionKind.toUpperCase() + " // OK";
            refresh();
            return;
        }

        const error = String(actionStderrText || actionStdoutText || "PX ACTION FAILED").trim();
        actionResult = "ERROR // " + error;
    }

    function clearFactoryResult() {
        if (factoryBusy)
            return;

        factoryMode = "";
        factoryYaml = "";
        factoryPath = "";
        factoryValidationStatus = "NOT PREVIEWED";
        factoryValidationValidator = "";
        factoryValidationMessage = "";
        factoryInstallBranch = "";
        factoryPullRequest = "";
        factoryInstallCommit = "";
        factoryLastTemplate = "";
        factoryLastTrigger = "";
        factoryLastSlug = "";
    }

    function friendlyFactoryMessage(message) {
        const raw = String(message || "").trim();
        const lower = raw.toLowerCase();

        if (!raw)
            return "PX COULD NOT BUILD THE WORKFLOW.";

        if (lower.indexOf("workflow slug must match") >= 0)
            return "WORKFLOW NAME // use lowercase letters, numbers, and hyphens only. Example: t6-audit";

        if (lower.indexOf("workflow slug required") >= 0)
            return "WORKFLOW NAME // type a name first. Example: t6-audit";

        if (lower.indexOf("template and name required") >= 0)
            return "WORKFLOW FACTORY // choose an operation and give the workflow a name.";

        if (lower.indexOf("no github repository") >= 0)
            return "GITHUB CONNECTION // this repo is not connected to a GitHub repository.";

        if (lower.indexOf("factory timeout") >= 0)
            return "PX FACTORY // GitHub took too long to answer. Try PREVIEW again.";

        return raw;
    }

    function previewWorkflow(templateId, slug, triggerId) {
        runFactory("preview", templateId, slug, triggerId);
    }

    function installWorkflow(templateId, slug, triggerId) {
        runFactory("install", templateId, slug, triggerId);
    }

    function runFactory(mode, templateId, slug, triggerId) {
        if (factoryBusy)
            return;

        if (!repoSlug) {
            factoryValidationStatus = "ERROR";
            factoryValidationMessage = "NO GITHUB REPOSITORY";
            return;
        }

        const cleanTemplate = String(templateId || "").trim();
        const cleanSlug = String(slug || "").trim();
        const cleanTrigger = String(triggerId || "manual").trim();

        if (!cleanTemplate || !cleanSlug) {
            factoryValidationStatus = "ERROR";
            factoryValidationMessage = "WORKFLOW FACTORY // choose an operation and give the workflow a name.";
            return;
        }

        if (!/^[a-z0-9][a-z0-9-]*$/.test(cleanSlug)) {
            factoryValidationStatus = "ERROR";
            factoryValidationMessage = "WORKFLOW NAME // use lowercase letters, numbers, and hyphens only. Example: t6-audit";
            return;
        }

        factoryBusy = true;
        factoryMode = mode;
        factoryExitSeen = false;
        factoryStdoutSeen = false;
        factoryStderrSeen = false;
        factoryExitCode = -1;
        factoryStdoutText = "";
        factoryStderrText = "";
        factoryYaml = "";
        factoryPath = "";
        factoryValidationStatus = mode === "install" ? "INSTALLING" : "PREVIEWING";
        factoryValidationValidator = "";
        factoryValidationMessage = "";
        factoryInstallBranch = "";
        factoryPullRequest = "";
        factoryInstallCommit = "";
        factoryLastTemplate = cleanTemplate;
        factoryLastTrigger = cleanTrigger;
        factoryLastSlug = cleanSlug;

        factoryProcess.exec([
            "bash",
            "-lc",
            'exec "$HOME/.local/bin/px" create "$1" "$2" "$3" "$4" "$5" --json',
            "px-factory",
            repoSlug,
            cleanTemplate,
            cleanSlug,
            cleanTrigger,
            mode === "install" ? "--install" : "--preview"
        ]);

        factoryWatchdog.restart();
    }

    function parseFactory(payload) {
        const raw = String(payload || "").trim();

        if (!raw)
            throw new Error("PX FACTORY RETURNED NO JSON");

        const data = JSON.parse(raw);
        const validation = data.validation || {};
        const install = data.install || {};

        factoryYaml = String(data.yaml || "");
        factoryPath = String(data.path || "");
        factoryValidationStatus = String(validation.status || "unknown").toUpperCase();
        factoryValidationValidator = String(validation.validator || "");
        factoryValidationMessage = String(validation.message || "");
        factoryInstallBranch = String(install.branch || "");
        factoryPullRequest = String(install.pull_request || "");
        factoryInstallCommit = String(install.commit || "");
    }

    function maybeFinishFactory() {
        if (!factoryBusy)
            return;

        if (!factoryExitSeen || !factoryStdoutSeen || !factoryStderrSeen)
            return;

        let parsed = false;

        if (String(factoryStdoutText || "").trim()) {
            try {
                parseFactory(factoryStdoutText);
                parsed = true;
            } catch (error) {
                factoryValidationStatus = "ERROR";
                factoryValidationMessage = "FACTORY PARSE // " + String(error);
            }
        }

        if (factoryExitCode !== 0 && !parsed) {
            factoryValidationStatus = "ERROR";
            factoryValidationMessage = friendlyFactoryMessage(
                String(factoryStderrText || "PX FACTORY FAILED").trim()
            );
        } else if (factoryExitCode !== 0 && !factoryValidationMessage) {
            factoryValidationMessage = friendlyFactoryMessage(
                String(factoryStderrText || "").trim()
            );
        }

        factoryBusy = false;
        factoryWatchdog.stop();

        if (factoryMode === "install"
                && factoryExitCode === 0
                && (factoryInstallCommit || factoryPullRequest))
            refresh();
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
        id: evidenceRunsProcess

        stdout: StdioCollector {
            onStreamFinished: {
                githubService.evidenceRunsStdoutText = this.text;
                githubService.evidenceRunsStdoutSeen = true;
                githubService.maybeFinishEvidenceRuns();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                githubService.evidenceRunsStderrText = this.text;
                githubService.evidenceRunsStderrSeen = true;
                githubService.maybeFinishEvidenceRuns();
            }
        }

        onExited: function(exitCode, exitStatus) {
            githubService.evidenceRunsExitCode = Number(exitCode);
            githubService.evidenceRunsExitSeen = true;
            githubService.maybeFinishEvidenceRuns();
        }
    }

    Process {
        id: inspectorProcess

        stdout: StdioCollector {
            onStreamFinished: {
                githubService.inspectorMetaStdoutText = this.text;
                githubService.inspectorMetaStdoutSeen = true;
                githubService.maybeFinishInspector();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                githubService.inspectorMetaStderrText = this.text;
                githubService.inspectorMetaStderrSeen = true;
                githubService.maybeFinishInspector();
            }
        }

        onExited: function(exitCode, exitStatus) {
            githubService.inspectorMetaExitCode = Number(exitCode);
            githubService.inspectorMetaExitSeen = true;
            githubService.maybeFinishInspector();
        }
    }

    Process {
        id: inspectorLogsProcess

        stdout: StdioCollector {
            onStreamFinished: {
                githubService.inspectorLogsStdoutText = this.text;
                githubService.inspectorLogsStdoutSeen = true;
                githubService.maybeFinishInspector();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                githubService.inspectorLogsStderrText = this.text;
                githubService.inspectorLogsStderrSeen = true;
                githubService.maybeFinishInspector();
            }
        }

        onExited: function(exitCode, exitStatus) {
            githubService.inspectorLogsExitCode = Number(exitCode);
            githubService.inspectorLogsExitSeen = true;
            githubService.maybeFinishInspector();
        }
    }

    Process {
        id: remoteActionProcess

        stdout: StdioCollector {
            onStreamFinished: {
                githubService.actionStdoutText = this.text;
                githubService.actionStdoutSeen = true;
                githubService.maybeFinishRemoteAction();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                githubService.actionStderrText = this.text;
                githubService.actionStderrSeen = true;
                githubService.maybeFinishRemoteAction();
            }
        }

        onExited: function(exitCode, exitStatus) {
            githubService.actionExitCode = Number(exitCode);
            githubService.actionExitSeen = true;
            githubService.maybeFinishRemoteAction();
        }
    }

    Process {
        id: factoryProcess

        stdout: StdioCollector {
            onStreamFinished: {
                githubService.factoryStdoutText = this.text;
                githubService.factoryStdoutSeen = true;
                githubService.maybeFinishFactory();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                githubService.factoryStderrText = this.text;
                githubService.factoryStderrSeen = true;
                githubService.maybeFinishFactory();
            }
        }

        onExited: function(exitCode, exitStatus) {
            githubService.factoryExitCode = Number(exitCode);
            githubService.factoryExitSeen = true;
            githubService.maybeFinishFactory();
        }
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
        id: evidenceRunsWatchdog
        interval: 15000
        repeat: false

        onTriggered: {
            if (!githubService.evidenceRunsBusy)
                return;

            const requestSha = githubService.evidenceRunsSha;
            githubService.evidenceRunsBusy = false;
            githubService.evidenceRuns = [];
            githubService.evidenceRunsError = "PX EVIDENCE RUN QUERY TIMEOUT";

            if (evidenceRunsProcess.running)
                evidenceRunsProcess.running = false;

            githubService.evidenceRunsReady(
                requestSha,
                [],
                githubService.evidenceRunsError
            );
        }
    }

    Timer {
        id: inspectorWatchdog
        interval: 25000
        repeat: false

        onTriggered: {
            if (!githubService.inspectorBusy)
                return;

            githubService.inspectorBusy = false;
            githubService.inspectorError = "PX RUN INSPECTOR TIMEOUT";

            if (inspectorProcess.running)
                inspectorProcess.running = false;

            if (inspectorLogsProcess.running)
                inspectorLogsProcess.running = false;
        }
    }

    Timer {
        id: actionWatchdog
        interval: 15000
        repeat: false

        onTriggered: {
            if (!githubService.actionBusy)
                return;

            githubService.actionBusy = false;
            githubService.actionResult = "ERROR // PX ACTION TIMEOUT";

            if (remoteActionProcess.running)
                remoteActionProcess.running = false;
        }
    }

    Timer {
        id: factoryWatchdog
        interval: 30000
        repeat: false

        onTriggered: {
            if (!githubService.factoryBusy)
                return;

            githubService.factoryBusy = false;
            githubService.factoryValidationStatus = "ERROR";
            githubService.factoryValidationMessage = "PX FACTORY TIMEOUT";

            if (factoryProcess.running)
                factoryProcess.running = false;
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
            githubService.lastError = "PX GITHUB BRIDGE TIMEOUT";

            if (workflowsProcess.running)
                workflowsProcess.running = false;

            if (runsProcess.running)
                runsProcess.running = false;
        }
    }
}
