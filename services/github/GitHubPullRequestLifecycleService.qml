import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property bool busy: false
    property string phase: "READY"
    property string operation: ""
    property string repository: ""
    property int pullRequestNumber: 0
    property string pullRequestUrl: ""
    property var evidence: ({})
    property bool mutationSucceeded: false
    property bool evidenceVerified: false
    property string status: "READY"
    property string lastError: ""

    property string pendingRepository: ""
    property string pendingEvidenceTarget: ""
    property bool pendingTargetFromStdout: false

    property bool mutationExitSeen: false
    property bool mutationStdoutSeen: false
    property bool mutationStderrSeen: false
    property int mutationExitCode: -1
    property string mutationStdoutText: ""
    property string mutationStderrText: ""

    property bool evidenceExitSeen: false
    property bool evidenceStdoutSeen: false
    property bool evidenceStderrSeen: false
    property int evidenceExitCode: -1
    property string evidenceStdoutText: ""
    property string evidenceStderrText: ""

    signal pullRequestChanged(string repository, int number, string url)
    signal mutationFinished(
        bool mutationSucceeded,
        bool evidenceVerified,
        string operation,
        var evidence
    )

    function normalizeRepository(value) {
        const slug = String(value || "").trim();

        if (!/^[^/\s]+\/[^/\s]+$/.test(slug))
            return "";

        return slug;
    }

    function normalizePullRequestNumber(value) {
        const number = Number(value || 0);

        if (!Number.isFinite(number) || number <= 0)
            return 0;

        return Math.floor(number);
    }

    function normalizeList(value) {
        const source =
            Array.isArray(value)
            ? value
            : String(value || "").split(",");
        const out = [];
        const seen = {};

        for (let i = 0; i < source.length; ++i) {
            const item = String(source[i] || "").trim();

            if (!item || seen[item.toLowerCase()])
                continue;

            seen[item.toLowerCase()] = true;
            out.push(item);
        }

        return out;
    }

    function appendRepeatedFlag(args, flag, values) {
        const rows = normalizeList(values);

        for (let i = 0; i < rows.length; ++i) {
            args.push(flag);
            args.push(rows[i]);
        }
    }

    function refuse(detail) {
        lastError = String(detail || "PULL REQUEST OPERATION REFUSED");
        status = "REFUSED // " + lastError;
        return false;
    }

    function resetStreams() {
        mutationExitSeen = false;
        mutationStdoutSeen = false;
        mutationStderrSeen = false;
        mutationExitCode = -1;
        mutationStdoutText = "";
        mutationStderrText = "";

        evidenceExitSeen = false;
        evidenceStdoutSeen = false;
        evidenceStderrSeen = false;
        evidenceExitCode = -1;
        evidenceStdoutText = "";
        evidenceStderrText = "";
    }

    function startMutation(name, repo, target, args, targetFromStdout) {
        if (busy)
            return false;

        const cleanRepo = normalizeRepository(repo);

        if (!cleanRepo)
            return refuse("GITHUB REPOSITORY REQUIRED");

        busy = true;
        phase = "MUTATING";
        operation = String(name || "");
        repository = cleanRepo;
        pendingRepository = cleanRepo;
        pendingEvidenceTarget = String(target || "");
        pendingTargetFromStdout = Boolean(targetFromStdout);

        pullRequestNumber = 0;
        pullRequestUrl = "";
        evidence = ({});
        mutationSucceeded = false;
        evidenceVerified = false;
        lastError = "";
        status =
            "PULL REQUEST // "
            + operation.toUpperCase()
            + " // WORKING";

        resetStreams();
        mutationProcess.exec(args);
        watchdog.restart();
        return true;
    }

    function createPullRequest(
        repo,
        title,
        body,
        head,
        base,
        draft,
        labels,
        assignees,
        reviewers,
        milestone
    ) {
        const cleanRepo = normalizeRepository(repo);
        const cleanTitle = String(title || "").trim();
        const cleanHead = String(head || "").trim();
        const cleanBase = String(base || "").trim();

        if (!cleanRepo)
            return refuse("PR CREATE UNAVAILABLE // REPOSITORY MISSING");
        if (!cleanTitle)
            return refuse("PR CREATE UNAVAILABLE // TITLE MISSING");
        if (!cleanHead)
            return refuse("PR CREATE UNAVAILABLE // HEAD MISSING");
        if (!cleanBase)
            return refuse("PR CREATE UNAVAILABLE // BASE MISSING");

        const args = [
            "gh",
            "pr",
            "create",
            "--repo",
            cleanRepo,
            "--title",
            cleanTitle,
            "--body",
            String(body || ""),
            "--head",
            cleanHead,
            "--base",
            cleanBase
        ];

        if (Boolean(draft))
            args.push("--draft");

        appendRepeatedFlag(args, "--label", labels);
        appendRepeatedFlag(args, "--assignee", assignees);
        appendRepeatedFlag(args, "--reviewer", reviewers);

        const cleanMilestone = String(milestone || "").trim();
        if (cleanMilestone) {
            args.push("--milestone");
            args.push(cleanMilestone);
        }

        return startMutation(
            "create",
            cleanRepo,
            "",
            args,
            true
        );
    }

    function editPullRequest(repo, number, title, body, base) {
        const cleanRepo = normalizeRepository(repo);
        const pr = normalizePullRequestNumber(number);

        if (!cleanRepo || !pr)
            return refuse("PR EDIT UNAVAILABLE // TARGET MISSING");

        const args = [
            "gh",
            "pr",
            "edit",
            String(pr),
            "--repo",
            cleanRepo
        ];

        let changed = false;

        if (title !== undefined && title !== null) {
            const cleanTitle = String(title).trim();

            if (!cleanTitle)
                return refuse("PR EDIT REFUSED // TITLE MAY NOT BE EMPTY");

            args.push("--title");
            args.push(cleanTitle);
            changed = true;
        }

        if (body !== undefined && body !== null) {
            args.push("--body");
            args.push(String(body));
            changed = true;
        }

        if (base !== undefined && base !== null) {
            const cleanBase = String(base).trim();

            if (!cleanBase)
                return refuse("PR EDIT REFUSED // BASE MAY NOT BE EMPTY");

            args.push("--base");
            args.push(cleanBase);
            changed = true;
        }

        if (!changed)
            return refuse("PR EDIT REFUSED // NO CHANGES");

        return startMutation(
            "edit",
            cleanRepo,
            String(pr),
            args,
            false
        );
    }

    function updateLabels(repo, number, addLabels, removeLabels) {
        const cleanRepo = normalizeRepository(repo);
        const pr = normalizePullRequestNumber(number);

        if (!cleanRepo || !pr)
            return refuse("PR LABEL UPDATE UNAVAILABLE // TARGET MISSING");

        const args = [
            "gh",
            "pr",
            "edit",
            String(pr),
            "--repo",
            cleanRepo
        ];

        const before = args.length;
        appendRepeatedFlag(args, "--add-label", addLabels);
        appendRepeatedFlag(args, "--remove-label", removeLabels);

        if (args.length === before)
            return refuse("PR LABEL UPDATE REFUSED // NO CHANGES");

        return startMutation(
            "labels",
            cleanRepo,
            String(pr),
            args,
            false
        );
    }

    function updateAssignees(repo, number, addAssignees, removeAssignees) {
        const cleanRepo = normalizeRepository(repo);
        const pr = normalizePullRequestNumber(number);

        if (!cleanRepo || !pr)
            return refuse("PR ASSIGNEE UPDATE UNAVAILABLE // TARGET MISSING");

        const args = [
            "gh",
            "pr",
            "edit",
            String(pr),
            "--repo",
            cleanRepo
        ];

        const before = args.length;
        appendRepeatedFlag(args, "--add-assignee", addAssignees);
        appendRepeatedFlag(args, "--remove-assignee", removeAssignees);

        if (args.length === before)
            return refuse("PR ASSIGNEE UPDATE REFUSED // NO CHANGES");

        return startMutation(
            "assignees",
            cleanRepo,
            String(pr),
            args,
            false
        );
    }

    function updateReviewers(repo, number, addReviewers, removeReviewers) {
        const cleanRepo = normalizeRepository(repo);
        const pr = normalizePullRequestNumber(number);

        if (!cleanRepo || !pr)
            return refuse("PR REVIEWER UPDATE UNAVAILABLE // TARGET MISSING");

        const args = [
            "gh",
            "pr",
            "edit",
            String(pr),
            "--repo",
            cleanRepo
        ];

        const before = args.length;
        appendRepeatedFlag(args, "--add-reviewer", addReviewers);
        appendRepeatedFlag(args, "--remove-reviewer", removeReviewers);

        if (args.length === before)
            return refuse("PR REVIEWER UPDATE REFUSED // NO CHANGES");

        return startMutation(
            "reviewers",
            cleanRepo,
            String(pr),
            args,
            false
        );
    }

    function setMilestone(repo, number, milestone) {
        const cleanRepo = normalizeRepository(repo);
        const pr = normalizePullRequestNumber(number);
        const cleanMilestone = String(milestone || "").trim();

        if (!cleanRepo || !pr || !cleanMilestone)
            return refuse("PR MILESTONE UPDATE UNAVAILABLE // TARGET MISSING");

        return startMutation(
            "milestone",
            cleanRepo,
            String(pr),
            [
                "gh",
                "pr",
                "edit",
                String(pr),
                "--repo",
                cleanRepo,
                "--milestone",
                cleanMilestone
            ],
            false
        );
    }

    function clearMilestone(repo, number) {
        const cleanRepo = normalizeRepository(repo);
        const pr = normalizePullRequestNumber(number);

        if (!cleanRepo || !pr)
            return refuse("PR MILESTONE CLEAR UNAVAILABLE // TARGET MISSING");

        return startMutation(
            "clear-milestone",
            cleanRepo,
            String(pr),
            [
                "gh",
                "pr",
                "edit",
                String(pr),
                "--repo",
                cleanRepo,
                "--remove-milestone"
            ],
            false
        );
    }

    function commentPullRequest(repo, number, body) {
        const cleanRepo = normalizeRepository(repo);
        const pr = normalizePullRequestNumber(number);
        const cleanBody = String(body || "").trim();

        if (!cleanRepo || !pr || !cleanBody)
            return refuse("PR COMMENT UNAVAILABLE // TARGET OR BODY MISSING");

        return startMutation(
            "comment",
            cleanRepo,
            String(pr),
            [
                "gh",
                "pr",
                "comment",
                String(pr),
                "--repo",
                cleanRepo,
                "--body",
                cleanBody
            ],
            false
        );
    }

    function markReady(repo, number) {
        const cleanRepo = normalizeRepository(repo);
        const pr = normalizePullRequestNumber(number);

        if (!cleanRepo || !pr)
            return refuse("PR READY UNAVAILABLE // TARGET MISSING");

        return startMutation(
            "ready",
            cleanRepo,
            String(pr),
            [
                "gh",
                "pr",
                "ready",
                String(pr),
                "--repo",
                cleanRepo
            ],
            false
        );
    }

    function convertToDraft(repo, number) {
        const cleanRepo = normalizeRepository(repo);
        const pr = normalizePullRequestNumber(number);

        if (!cleanRepo || !pr)
            return refuse("PR DRAFT UNAVAILABLE // TARGET MISSING");

        return startMutation(
            "draft",
            cleanRepo,
            String(pr),
            [
                "gh",
                "pr",
                "ready",
                String(pr),
                "--repo",
                cleanRepo,
                "--undo"
            ],
            false
        );
    }

    function reviewPullRequest(repo, number, mode, body) {
        const cleanRepo = normalizeRepository(repo);
        const pr = normalizePullRequestNumber(number);
        const cleanMode = String(mode || "").trim().toLowerCase();
        const cleanBody = String(body || "").trim();

        if (!cleanRepo || !pr)
            return refuse("PR REVIEW UNAVAILABLE // TARGET MISSING");
        if (["approve", "comment", "request-changes"].indexOf(cleanMode) < 0)
            return refuse("PR REVIEW REFUSED // INVALID REVIEW MODE");
        if (cleanMode !== "approve" && !cleanBody)
            return refuse("PR REVIEW REFUSED // BODY REQUIRED");

        const args = [
            "gh",
            "pr",
            "review",
            String(pr),
            "--repo",
            cleanRepo
        ];

        if (cleanMode === "approve")
            args.push("--approve");
        else if (cleanMode === "comment")
            args.push("--comment");
        else
            args.push("--request-changes");

        if (cleanBody) {
            args.push("--body");
            args.push(cleanBody);
        }

        return startMutation(
            "review-" + cleanMode,
            cleanRepo,
            String(pr),
            args,
            false
        );
    }

    function closePullRequest(repo, number, confirmed, comment) {
        const cleanRepo = normalizeRepository(repo);
        const pr = normalizePullRequestNumber(number);

        if (!confirmed)
            return refuse("PR CLOSE REFUSED // EXPLICIT CONFIRMATION REQUIRED");
        if (!cleanRepo || !pr)
            return refuse("PR CLOSE UNAVAILABLE // TARGET MISSING");

        const args = [
            "gh",
            "pr",
            "close",
            String(pr),
            "--repo",
            cleanRepo
        ];

        const cleanComment = String(comment || "").trim();
        if (cleanComment) {
            args.push("--comment");
            args.push(cleanComment);
        }

        return startMutation(
            "close",
            cleanRepo,
            String(pr),
            args,
            false
        );
    }

    function reopenPullRequest(repo, number, comment) {
        const cleanRepo = normalizeRepository(repo);
        const pr = normalizePullRequestNumber(number);

        if (!cleanRepo || !pr)
            return refuse("PR REOPEN UNAVAILABLE // TARGET MISSING");

        const args = [
            "gh",
            "pr",
            "reopen",
            String(pr),
            "--repo",
            cleanRepo
        ];

        const cleanComment = String(comment || "").trim();
        if (cleanComment) {
            args.push("--comment");
            args.push(cleanComment);
        }

        return startMutation(
            "reopen",
            cleanRepo,
            String(pr),
            args,
            false
        );
    }

    function updateBranch(repo, number, rebase, confirmed) {
        const cleanRepo = normalizeRepository(repo);
        const pr = normalizePullRequestNumber(number);

        if (!confirmed)
            return refuse("PR UPDATE BRANCH REFUSED // EXPLICIT CONFIRMATION REQUIRED");
        if (!cleanRepo || !pr)
            return refuse("PR UPDATE BRANCH UNAVAILABLE // TARGET MISSING");

        const args = [
            "gh",
            "pr",
            "update-branch",
            String(pr),
            "--repo",
            cleanRepo
        ];

        if (Boolean(rebase))
            args.push("--rebase");

        return startMutation(
            Boolean(rebase) ? "update-branch-rebase" : "update-branch",
            cleanRepo,
            String(pr),
            args,
            false
        );
    }

    function mergePullRequest(
        repo,
        number,
        method,
        expectedHeadSha,
        confirmed,
        commitTitle,
        commitBody
    ) {
        const cleanRepo = normalizeRepository(repo);
        const pr = normalizePullRequestNumber(number);
        const cleanMethod = String(method || "").trim().toLowerCase();
        const cleanHead = String(expectedHeadSha || "").trim();

        if (!confirmed)
            return refuse("PR MERGE REFUSED // EXPLICIT CONFIRMATION REQUIRED");
        if (!cleanRepo || !pr)
            return refuse("PR MERGE UNAVAILABLE // TARGET MISSING");
        if (["merge", "squash", "rebase"].indexOf(cleanMethod) < 0)
            return refuse("PR MERGE REFUSED // INVALID MERGE METHOD");
        if (!/^[0-9a-fA-F]{40}$/.test(cleanHead))
            return refuse("PR MERGE REFUSED // EXPECTED HEAD SHA REQUIRED");

        const args = [
            "gh",
            "pr",
            "merge",
            String(pr),
            "--repo",
            cleanRepo,
            "--match-head-commit",
            cleanHead,
            "--" + cleanMethod
        ];

        const cleanTitle = String(commitTitle || "").trim();
        const cleanBody = String(commitBody || "").trim();

        if (cleanTitle) {
            args.push("--subject");
            args.push(cleanTitle);
        }

        if (cleanBody) {
            args.push("--body");
            args.push(cleanBody);
        }

        return startMutation(
            "merge-" + cleanMethod,
            cleanRepo,
            String(pr),
            args,
            false
        );
    }

    function createdPullRequestTarget(text) {
        const lines = String(text || "").trim().split("\n");

        for (let i = lines.length - 1; i >= 0; --i) {
            const line = String(lines[i] || "").trim();

            if (/^https:\/\/github\.com\/[^/]+\/[^/]+\/pull\/\d+$/.test(line))
                return line;
        }

        return "";
    }

    function startEvidenceRead(target) {
        const cleanTarget = String(target || "").trim();

        if (!cleanTarget) {
            finishWithoutEvidence(
                "MUTATION SUCCEEDED // PULL REQUEST TARGET UNKNOWN"
            );
            return;
        }

        phase = "VERIFYING";
        pendingEvidenceTarget = cleanTarget;
        status =
            "PULL REQUEST // "
            + operation.toUpperCase()
            + " // VERIFYING";

        evidenceExitSeen = false;
        evidenceStdoutSeen = false;
        evidenceStderrSeen = false;
        evidenceExitCode = -1;
        evidenceStdoutText = "";
        evidenceStderrText = "";

        evidenceProcess.exec([
            "gh",
            "pr",
            "view",
            cleanTarget,
            "--repo",
            pendingRepository,
            "--json",
            "number,title,body,state,url,isDraft,labels,assignees,milestone,author,createdAt,updatedAt,closed,closedAt,mergedAt,mergedBy,baseRefName,baseRefOid,headRefName,headRefOid,headRepository,headRepositoryOwner,isCrossRepository,maintainerCanModify,mergeable,mergeStateStatus,reviewDecision,reviewRequests,latestReviews,statusCheckRollup,autoMergeRequest"
        ]);
    }

    function finishWithoutEvidence(detail) {
        busy = false;
        phase = "READY";
        evidenceVerified = false;
        lastError = String(detail || "PULL REQUEST EVIDENCE UNAVAILABLE");
        status =
            "PULL REQUEST // "
            + operation.toUpperCase()
            + " // MUTATED // EVIDENCE UNVERIFIED";
        watchdog.stop();

        mutationFinished(
            true,
            false,
            operation,
            {
                repository: pendingRepository,
                target: pendingEvidenceTarget,
                error: lastError
            }
        );
    }

    function maybeFinishMutation() {
        if (!busy
                || phase !== "MUTATING"
                || !mutationExitSeen
                || !mutationStdoutSeen
                || !mutationStderrSeen)
            return;

        if (mutationExitCode !== 0) {
            busy = false;
            phase = "READY";
            mutationSucceeded = false;
            evidenceVerified = false;
            lastError =
                String(
                    mutationStderrText
                    || mutationStdoutText
                    || ("PULL REQUEST MUTATION EXIT " + mutationExitCode)
                ).trim();
            status =
                "PULL REQUEST // "
                + operation.toUpperCase()
                + " // ERROR";
            watchdog.stop();
            mutationFinished(false, false, operation, ({}));
            return;
        }

        mutationSucceeded = true;

        const target =
            pendingTargetFromStdout
            ? createdPullRequestTarget(mutationStdoutText)
            : pendingEvidenceTarget;

        startEvidenceRead(target);
    }

    function maybeFinishEvidence() {
        if (!busy
                || phase !== "VERIFYING"
                || !evidenceExitSeen
                || !evidenceStdoutSeen
                || !evidenceStderrSeen)
            return;

        if (evidenceExitCode !== 0) {
            finishWithoutEvidence(
                String(
                    evidenceStderrText
                    || evidenceStdoutText
                    || ("PULL REQUEST EVIDENCE EXIT " + evidenceExitCode)
                ).trim()
            );
            return;
        }

        try {
            const row = JSON.parse(String(evidenceStdoutText || "{}"));

            evidence = {
                operation: operation,
                repository: pendingRepository,
                pullRequest: row
            };
            pullRequestNumber = Number(row.number || 0);
            pullRequestUrl = String(row.url || "");
            evidenceVerified =
                pullRequestNumber > 0
                && pullRequestUrl.length > 0;
            busy = false;
            phase = "READY";
            lastError = "";
            status =
                "PULL REQUEST // "
                + operation.toUpperCase()
                + " // VERIFIED // #"
                + String(pullRequestNumber);
            watchdog.stop();

            pullRequestChanged(
                pendingRepository,
                pullRequestNumber,
                pullRequestUrl
            );
            mutationFinished(
                true,
                evidenceVerified,
                operation,
                evidence
            );
        } catch (parseError) {
            finishWithoutEvidence(
                "PULL REQUEST EVIDENCE PARSE // " + String(parseError)
            );
        }
    }

    Process {
        id: mutationProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.mutationStdoutText = this.text;
                root.mutationStdoutSeen = true;
                root.maybeFinishMutation();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.mutationStderrText = this.text;
                root.mutationStderrSeen = true;
                root.maybeFinishMutation();
            }
        }

        onExited: function(code, exitStatus) {
            root.mutationExitCode = Number(code);
            root.mutationExitSeen = true;
            root.maybeFinishMutation();
        }
    }

    Process {
        id: evidenceProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.evidenceStdoutText = this.text;
                root.evidenceStdoutSeen = true;
                root.maybeFinishEvidence();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.evidenceStderrText = this.text;
                root.evidenceStderrSeen = true;
                root.maybeFinishEvidence();
            }
        }

        onExited: function(code, exitStatus) {
            root.evidenceExitCode = Number(code);
            root.evidenceExitSeen = true;
            root.maybeFinishEvidence();
        }
    }

    Timer {
        id: watchdog
        interval: 120000
        repeat: false

        onTriggered: {
            const wasMutationSucceeded = root.mutationSucceeded;
            root.busy = false;
            root.phase = "READY";
            root.evidenceVerified = false;
            root.lastError =
                wasMutationSucceeded
                ? "PULL REQUEST MUTATED // EVIDENCE TIMEOUT"
                : "PULL REQUEST MUTATION TIMEOUT";
            root.status =
                wasMutationSucceeded
                ? "PULL REQUEST // MUTATED // EVIDENCE UNVERIFIED"
                : "PULL REQUEST // TIMEOUT";

            if (mutationProcess.running)
                mutationProcess.running = false;
            if (evidenceProcess.running)
                evidenceProcess.running = false;

            root.mutationFinished(
                wasMutationSucceeded,
                false,
                root.operation,
                {
                    repository: root.pendingRepository,
                    target: root.pendingEvidenceTarget,
                    error: root.lastError
                }
            );
        }
    }
}
