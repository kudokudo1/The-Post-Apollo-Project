import QtQuick
import Quickshell

Scope {
    id: evidenceProvider

    // Doc 3 boundary:
    // Git/GitHub report facts. Hospital decides what those facts mean.
    property var gitService: null
    property var githubService: null

    readonly property int schemaVersion: 1
    readonly property string providerId: "post-apollo.git-evidence"

    readonly property string repository:
        githubService ? String(githubService.repoSlug || "") : ""

    readonly property string currentHead:
        gitService
        ? String(gitService.headFull || gitService.head || "")
        : ""

    readonly property string currentBranch:
        gitService ? String(gitService.branch || "") : ""

    readonly property string localRepository:
        repositorySlugFromOrigin(
            gitService ? String(gitService.origin || "") : ""
        )

    readonly property var liveDiagnostics:
        diagnosticFacts(
            currentHead,
            inspectorEvidence(currentHead)
        )
    readonly property string diagnosticState:
        String((liveDiagnostics || {}).state || "UNKNOWN")
    readonly property string diagnosticSummary:
        String((liveDiagnostics || {}).summary || "")

    property bool requestBusy: false
    property string requestSha: ""
    property string requestRunId: ""
    property string requestError: ""
    property string requestStartedAt: ""
    property bool requestGitReady: false
    property bool requestGithubReady: false
    property bool requestRunsReady: false
    property bool requestInspectorReady: true
    property var lastPacket: ({})

    signal evidenceCaptured(var packet)
    signal requestStarted(string sha, string runId)
    signal requestFinished(var packet)

    function nowIso() {
        return new Date().toISOString();
    }

    function textValue(value, fallback) {
        if (value === undefined || value === null)
            return fallback || "";

        const text = String(value);
        return text.length > 0 ? text : (fallback || "");
    }

    function repositorySlugFromOrigin(originValue) {
        let value = textValue(originValue, "").trim();

        if (!value
                || value === "NOT CONNECTED"
                || value === "NO ORIGIN")
            return "";

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

    function firstField(object, names, fallback) {
        if (!object || !Array.isArray(names))
            return fallback;

        for (let i = 0; i < names.length; ++i) {
            const key = names[i];

            if (object[key] !== undefined
                    && object[key] !== null
                    && String(object[key]) !== "") {
                return object[key];
            }
        }

        return fallback;
    }

    function runId(run) {
        return textValue(
            firstField(
                run,
                ["databaseId", "id", "runId", "number"],
                ""
            ),
            ""
        );
    }

    function runSha(run) {
        return textValue(
            firstField(
                run,
                ["headSha", "head_sha", "sha", "commitSha"],
                ""
            ),
            ""
        );
    }

    function normalizeWorkflow(workflow) {
        const row = workflow || ({});

        return {
            id: textValue(firstField(row, ["id", "databaseId"], ""), ""),
            name: textValue(firstField(row, ["name", "workflowName"], ""), ""),
            path: textValue(firstField(row, ["path", "workflowPath"], ""), ""),
            state: textValue(firstField(row, ["state", "status"], ""), "")
        };
    }

    function normalizeStep(step, index) {
        const row = step || ({});

        return {
            number: Number(firstField(row, ["number"], index + 1) || (index + 1)),
            name: textValue(firstField(row, ["name"], "STEP " + String(index + 1)), ""),
            status: textValue(firstField(row, ["status"], ""), ""),
            conclusion: textValue(firstField(row, ["conclusion"], ""), ""),
            startedAt: textValue(firstField(row, ["startedAt", "started_at"], ""), ""),
            completedAt: textValue(firstField(row, ["completedAt", "completed_at"], ""), "")
        };
    }

    function normalizeJob(job, index) {
        const row = job || ({});
        const rawSteps = Array.isArray(row.steps) ? row.steps : [];
        const steps = [];

        for (let i = 0; i < rawSteps.length; ++i)
            steps.push(normalizeStep(rawSteps[i], i));

        return {
            id: textValue(firstField(row, ["databaseId", "id"], ""), ""),
            name: textValue(firstField(row, ["name"], "JOB " + String(index + 1)), ""),
            status: textValue(firstField(row, ["status"], ""), ""),
            conclusion: textValue(firstField(row, ["conclusion"], ""), ""),
            startedAt: textValue(firstField(row, ["startedAt", "started_at"], ""), ""),
            completedAt: textValue(firstField(row, ["completedAt", "completed_at"], ""), ""),
            steps: steps
        };
    }

    function normalizeRun(run) {
        const row = run || ({});

        return {
            id: runId(row),
            workflowName: textValue(
                firstField(row, ["workflowName", "workflow_name", "name"], ""),
                ""
            ),
            workflowPath: textValue(
                firstField(row, ["workflowPath", "workflow_path", "path"], ""),
                ""
            ),
            event: textValue(firstField(row, ["event"], ""), ""),
            status: textValue(firstField(row, ["status"], ""), ""),
            conclusion: textValue(firstField(row, ["conclusion"], ""), ""),
            headBranch: textValue(
                firstField(row, ["headBranch", "head_branch", "branch"], ""),
                ""
            ),
            headSha: runSha(row),
            createdAt: textValue(firstField(row, ["createdAt", "created_at"], ""), ""),
            startedAt: textValue(firstField(row, ["startedAt", "started_at"], ""), ""),
            updatedAt: textValue(firstField(row, ["updatedAt", "updated_at"], ""), ""),
            url: textValue(firstField(row, ["url", "htmlUrl", "html_url"], ""), "")
        };
    }

    function normalizedWorkflows() {
        const source =
            githubService && Array.isArray(githubService.workflows)
            ? githubService.workflows
            : [];
        const rows = [];

        for (let i = 0; i < source.length; ++i)
            rows.push(normalizeWorkflow(source[i]));

        return rows;
    }

    function runsForSha(sha) {
        const target = textValue(sha, "");
        const exactSource =
            githubService
            && textValue(githubService.evidenceRunsSha, "") === target
            && Array.isArray(githubService.evidenceRuns)
            ? githubService.evidenceRuns
            : null;
        const source =
            exactSource !== null
            ? exactSource
            : githubService && Array.isArray(githubService.runs)
            ? githubService.runs
            : [];
        const rows = [];

        if (!target)
            return rows;

        for (let i = 0; i < source.length; ++i) {
            const normalized = normalizeRun(source[i]);

            if (normalized.headSha === target)
                rows.push(normalized);
        }

        return rows;
    }

    function matchingSummaryForInspector(targetSha) {
        const id =
            githubService
            ? textValue(githubService.inspectorRunId, "")
            : "";

        if (!id)
            return null;

        const matching = runsForSha(targetSha);

        for (let i = 0; i < matching.length; ++i) {
            if (matching[i].id === id)
                return matching[i];
        }

        return null;
    }

    function inspectorEvidence(targetSha) {
        if (!githubService)
            return null;

        const summary = matchingSummaryForInspector(targetSha);

        if (!summary)
            return null;

        const detail =
            githubService.inspectedRun
            ? normalizeRun(githubService.inspectedRun)
            : ({});
        const sourceJobs =
            Array.isArray(githubService.inspectorJobs)
            ? githubService.inspectorJobs
            : [];
        const jobs = [];

        for (let i = 0; i < sourceJobs.length; ++i)
            jobs.push(normalizeJob(sourceJobs[i], i));

        return {
            run: {
                id: summary.id,
                workflowName: detail.workflowName || summary.workflowName,
                workflowPath: detail.workflowPath || summary.workflowPath,
                event: detail.event || summary.event,
                status: detail.status || summary.status,
                conclusion: detail.conclusion || summary.conclusion,
                headBranch: detail.headBranch || summary.headBranch,
                headSha: detail.headSha || summary.headSha,
                createdAt: detail.createdAt || summary.createdAt,
                startedAt: detail.startedAt || summary.startedAt,
                updatedAt: detail.updatedAt || summary.updatedAt,
                url: detail.url || summary.url
            },
            jobs: jobs,
            logs: textValue(githubService.inspectorLogText, ""),
            busy: Boolean(githubService.inspectorBusy),
            error: textValue(githubService.inspectorError, "")
        };
    }

    function summarizeRuns(rows) {
        const source = Array.isArray(rows) ? rows : [];
        const summary = {
            total: source.length,
            queued: 0,
            inProgress: 0,
            completed: 0,
            success: 0,
            failure: 0,
            cancelled: 0,
            timedOut: 0,
            neutral: 0,
            otherConclusion: 0,
            missingSha: 0
        };

        for (let i = 0; i < source.length; ++i) {
            const run = source[i] || {};
            const status = textValue(run.status, "").toLowerCase();
            const conclusion = textValue(run.conclusion, "").toLowerCase();

            if (!textValue(run.headSha, ""))
                summary.missingSha += 1;

            if (status === "queued")
                summary.queued += 1;
            else if (status === "in_progress")
                summary.inProgress += 1;
            else if (status === "completed")
                summary.completed += 1;

            if (conclusion === "success")
                summary.success += 1;
            else if (conclusion === "failure")
                summary.failure += 1;
            else if (conclusion === "cancelled")
                summary.cancelled += 1;
            else if (conclusion === "timed_out")
                summary.timedOut += 1;
            else if (conclusion === "neutral")
                summary.neutral += 1;
            else if (conclusion)
                summary.otherConclusion += 1;
        }

        return summary;
    }

    function stalenessFacts(targetSha, inspected) {
        const exactQuerySha =
            githubService ? textValue(githubService.evidenceRunsSha, "") : "";
        const inspectedSha =
            inspected && inspected.run
            ? textValue(inspected.run.headSha, "")
            : "";

        return {
            localHeadMovedFromTarget:
                Boolean(targetSha)
                && Boolean(currentHead)
                && currentHead !== targetSha,
            exactQueryTargetsRequestedSha:
                Boolean(targetSha)
                && exactQuerySha === targetSha,
            exactQuerySha: exactQuerySha,
            inspectedRunTargetsRequestedSha:
                !inspectedSha || inspectedSha === targetSha,
            inspectedRunSha: inspectedSha
        };
    }

    function diagnosticFacts(targetSha, inspected) {
        const target = textValue(targetSha, "");
        const githubRepository = textValue(repository, "");
        const checkoutRepository = textValue(localRepository, "");
        const localOrigin =
            gitService ? textValue(gitService.origin, "") : "";
        const exactQuerySha =
            githubService
            ? textValue(githubService.evidenceRunsSha, "")
            : "";
        const inspectedSha =
            inspected && inspected.run
            ? textValue(inspected.run.headSha, "")
            : "";
        const pxState =
            githubService
            ? textValue(githubService.pxRuntimeState, "UNKNOWN")
            : "UNAVAILABLE";

        const repositoryMatchesLocalOrigin =
            Boolean(githubRepository)
            && Boolean(checkoutRepository)
            && githubRepository === checkoutRepository;
        const targetMatchesCurrentHead =
            Boolean(target)
            && Boolean(currentHead)
            && target === currentHead;
        const exactQueryMatches =
            !target
            || !exactQuerySha
            || exactQuerySha === target;
        const inspectedRunMatches =
            !target
            || !inspectedSha
            || inspectedSha === target;

        const issues = [];

        if (!githubRepository)
            issues.push("GITHUB REPOSITORY UNKNOWN");

        if (!checkoutRepository)
            issues.push("LOCAL ORIGIN NOT GITHUB");

        if (githubRepository
                && checkoutRepository
                && !repositoryMatchesLocalOrigin)
            issues.push("LOCAL ORIGIN != GITHUB REPOSITORY");

        if (!target)
            issues.push("TARGET SHA UNKNOWN");

        if (!currentHead)
            issues.push("LOCAL HEAD UNKNOWN");
        else if (target && !targetMatchesCurrentHead)
            issues.push("LOCAL HEAD MOVED");

        if (!exactQueryMatches)
            issues.push("EXACT QUERY SHA DRIFT");

        if (!inspectedRunMatches)
            issues.push("INSPECTED RUN SHA DRIFT");

        if (pxState === "MISSING")
            issues.push("PX MISSING");
        else if (pxState === "STALE")
            issues.push("PX STALE");
        else if (pxState === "ERROR")
            issues.push("PX IDENTITY ERROR");

        let state = "READY";

        if (!githubRepository
                || !target
                || !currentHead
                || pxState === "MISSING"
                || pxState === "ERROR") {
            state = "ERROR";
        } else if (checkoutRepository
                && !repositoryMatchesLocalOrigin) {
            state = "MISMATCH";
        } else if (!exactQueryMatches
                || !inspectedRunMatches) {
            state = "MISMATCH";
        } else if (!checkoutRepository
                || !targetMatchesCurrentHead
                || pxState === "STALE"
                || pxState === "SOURCE_MISSING") {
            state = "ATTENTION";
        }

        return {
            state: state,
            summary:
                state
                + (
                    issues.length > 0
                    ? " // " + issues.join(" + ")
                    : " // EVIDENCE SEAMS ALIGNED"
                  ),
            issues: issues,
            githubRepository: githubRepository,
            localRepository: checkoutRepository,
            localOrigin: localOrigin,
            repositoryMatchesLocalOrigin:
                repositoryMatchesLocalOrigin,
            targetSha: target,
            currentHead: currentHead,
            targetMatchesCurrentHead:
                targetMatchesCurrentHead,
            exactQuerySha: exactQuerySha,
            exactQueryMatches: exactQueryMatches,
            inspectedRunSha: inspectedSha,
            inspectedRunMatches: inspectedRunMatches,
            pxRuntimeState: pxState,
            pxRuntimeDetail:
                githubService
                ? textValue(githubService.pxRuntimeDetail, "")
                : ""
        };
    }

    function buildEvidencePacket(sha) {
        const targetSha = textValue(sha, currentHead);
        const matchingRuns = runsForSha(targetSha);
        const inspected = inspectorEvidence(targetSha);
        const runSummary = summarizeRuns(matchingRuns);
        const staleness = stalenessFacts(targetSha, inspected);
        const diagnostics =
            diagnosticFacts(targetSha, inspected);
        const gitAvailable =
            gitService ? Boolean(gitService.available) : false;
        const githubAvailable =
            githubService ? Boolean(githubService.available) : false;

        return {
            schemaVersion: schemaVersion,
            provider: providerId,
            capturedAt: nowIso(),

            target: {
                repository: repository,
                repoRoot:
                    gitService ? textValue(gitService.repoRoot, "") : "",
                origin:
                    gitService ? textValue(gitService.origin, "") : "",
                branch:
                    gitService ? textValue(gitService.branch, "") : "",
                sha: targetSha
            },

            localGit: {
                available: gitAvailable,
                refreshing:
                    gitService ? Boolean(gitService.refreshing) : false,
                headAtCapture: currentHead,
                headMatchesTarget:
                    Boolean(targetSha) && currentHead === targetSha,
                worktree:
                    gitService ? textValue(gitService.worktree, "") : "",
                upstream:
                    gitService ? textValue(gitService.upstream, "") : "",
                ahead:
                    gitService ? Number(gitService.ahead || 0) : 0,
                behind:
                    gitService ? Number(gitService.behind || 0) : 0,
                lastError:
                    gitService ? textValue(gitService.lastError, "") : ""
            },

            facts: {
                targetIsCurrentLocalHead:
                    Boolean(targetSha)
                    && Boolean(currentHead)
                    && targetSha === currentHead,
                worktreeDirty:
                    gitService
                    ? textValue(gitService.worktree, "").indexOf("DIRTY") === 0
                    : false,
                runSummary: runSummary,
                staleness: staleness
            },

            diagnostics: diagnostics,

            github: {
                available: githubAvailable,
                refreshing:
                    githubService ? Boolean(githubService.refreshing) : false,
                workflowCount:
                    githubService ? Number(githubService.workflowCount || 0) : 0,
                workflows: normalizedWorkflows(),
                matchingRunCount: matchingRuns.length,
                matchingRuns: matchingRuns,
                inspectedRun: inspected,
                lastError:
                    githubService ? textValue(githubService.lastError, "") : ""
            },

            completeness: {
                repositoryKnown: Boolean(repository),
                targetShaKnown: Boolean(targetSha),
                localHeadKnown: Boolean(currentHead),
                githubAvailable: githubAvailable,
                exactRunQuery:
                    githubService
                    && textValue(githubService.evidenceRunsSha, "") === targetSha
                    && !Boolean(githubService.evidenceRunsBusy),
                matchingRunCount: matchingRuns.length,
                inspectedRunIncluded: Boolean(inspected),
                inspectorBusy:
                    githubService ? Boolean(githubService.inspectorBusy) : false,
                inspectorError:
                    githubService
                    ? textValue(githubService.inspectorError, "")
                    : "",
                requestError: requestError
            }
        };
    }

    function findRequestedRun(runIdValue, sha) {
        const needle = textValue(runIdValue, "");
        const rows = runsForSha(sha);

        if (!needle)
            return null;

        for (let i = 0; i < rows.length; ++i) {
            if (rows[i].id === needle)
                return rows[i];
        }

        return null;
    }

    function requestEvidence(sha, runIdValue) {
        if (requestBusy)
            return false;

        const targetSha = textValue(sha, currentHead);
        const targetRunId = textValue(runIdValue, "");

        if (!targetSha)
            return false;

        requestBusy = true;
        requestSha = targetSha;
        requestRunId = targetRunId;
        requestError = "";
        requestStartedAt = nowIso();
        requestGitReady = !gitService;
        requestGithubReady = !githubService;
        requestRunsReady = !githubService;
        requestInspectorReady = !targetRunId;
        lastPacket = ({});

        requestStarted(targetSha, targetRunId);

        if (gitService) {
            if (gitService.refreshing) {
                requestGitReady = false;
            } else {
                gitService.refresh();
                requestGitReady = !gitService.refreshing;
            }
        }

        if (githubService) {
            if (githubService.refreshing) {
                requestGithubReady = false;
            } else {
                githubService.refresh();
                requestGithubReady = !githubService.refreshing;
            }

            const queryStarted =
                githubService.requestEvidenceRuns(targetSha);

            if (!queryStarted) {
                requestRunsReady = true;
                requestError =
                    textValue(
                        githubService.evidenceRunsError,
                        "EXACT-SHA EVIDENCE QUERY BUSY"
                    );
            }
        }

        maybeFinishRequest();
        return true;
    }

    function maybeStartRequestedInspector() {
        if (!requestBusy
                || !requestRunsReady
                || requestInspectorReady
                || !requestRunId) {
            return;
        }

        if (!githubService) {
            requestError = "RUN INSPECTOR UNAVAILABLE";
            requestInspectorReady = true;
            return;
        }

        const requested = findRequestedRun(requestRunId, requestSha);

        if (!requested) {
            requestError =
                "REQUESTED RUN NOT FOUND FOR TARGET SHA // "
                + requestRunId;
            requestInspectorReady = true;
            return;
        }

        if (githubService.inspectorBusy)
            return;

        requestInspectorReady = false;
        githubService.inspectRun(requestRunId);
    }

    function maybeFinishRequest() {
        if (!requestBusy)
            return;

        maybeStartRequestedInspector();

        if (!requestGitReady
                || !requestGithubReady
                || !requestRunsReady
                || !requestInspectorReady) {
            return;
        }

        const packet = buildEvidencePacket(requestSha);

        packet.request = {
            startedAt: requestStartedAt,
            finishedAt: nowIso(),
            sha: requestSha,
            runId: requestRunId,
            error: requestError
        };

        lastPacket = packet;
        requestBusy = false;
        evidenceCaptured(packet);
        requestFinished(packet);
    }

    function capture(sha) {
        const packet = buildEvidencePacket(sha);
        evidenceCaptured(packet);
        return packet;
    }

    Connections {
        target: evidenceProvider.gitService

        function onRefreshed() {
            if (!evidenceProvider.requestBusy)
                return;

            evidenceProvider.requestGitReady = true;
            evidenceProvider.maybeFinishRequest();
        }

        function onRefreshingChanged() {
            if (!evidenceProvider.requestBusy || target.refreshing)
                return;

            evidenceProvider.requestGitReady = true;
            evidenceProvider.maybeFinishRequest();
        }
    }

    Connections {
        target: evidenceProvider.githubService

        function onRefreshingChanged() {
            if (!evidenceProvider.requestBusy || target.refreshing)
                return;

            evidenceProvider.requestGithubReady = true;
            evidenceProvider.maybeFinishRequest();
        }

        function onEvidenceRunsReady(sha, runs, error) {
            if (!evidenceProvider.requestBusy
                    || String(sha || "") !== evidenceProvider.requestSha) {
                return;
            }

            evidenceProvider.requestRunsReady = true;

            if (String(error || ""))
                evidenceProvider.requestError = String(error);

            evidenceProvider.maybeFinishRequest();
        }

        function onInspectorBusyChanged() {
            if (!evidenceProvider.requestBusy
                    || !evidenceProvider.requestRunId
                    || target.inspectorBusy) {
                return;
            }

            if (String(target.inspectorRunId || "")
                    === evidenceProvider.requestRunId) {
                evidenceProvider.requestInspectorReady = true;

                if (String(target.inspectorError || ""))
                    evidenceProvider.requestError =
                        String(target.inspectorError);
            }

            evidenceProvider.maybeFinishRequest();
        }
    }
}
