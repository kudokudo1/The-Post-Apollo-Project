import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property bool busy: false
    property string phase: "READY"
    property string operation: ""
    property string repository: ""
    property int issueNumber: 0
    property string issueUrl: ""
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

    signal issueChanged(string repository, int number, string url)
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

    function normalizeIssueNumber(value) {
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
        lastError = String(detail || "ISSUE OPERATION REFUSED");
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

        issueNumber = 0;
        issueUrl = "";
        evidence = ({});
        mutationSucceeded = false;
        evidenceVerified = false;
        lastError = "";
        status =
            "ISSUE // "
            + operation.toUpperCase()
            + " // WORKING";

        resetStreams();
        mutationProcess.exec(args);
        watchdog.restart();
        return true;
    }

    function createIssue(repo, title, body, labels, assignees, milestone) {
        const cleanRepo = normalizeRepository(repo);
        const cleanTitle = String(title || "").trim();

        if (!cleanRepo)
            return refuse("ISSUE CREATE UNAVAILABLE // REPOSITORY MISSING");
        if (!cleanTitle)
            return refuse("ISSUE CREATE UNAVAILABLE // TITLE MISSING");

        const args = [
            "gh",
            "issue",
            "create",
            "--repo",
            cleanRepo,
            "--title",
            cleanTitle,
            "--body",
            String(body || "")
        ];

        appendRepeatedFlag(args, "--label", labels);
        appendRepeatedFlag(args, "--assignee", assignees);

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

    function editIssue(repo, number, title, body) {
        const cleanRepo = normalizeRepository(repo);
        const issue = normalizeIssueNumber(number);

        if (!cleanRepo || !issue)
            return refuse("ISSUE EDIT UNAVAILABLE // TARGET MISSING");

        const args = [
            "gh",
            "issue",
            "edit",
            String(issue),
            "--repo",
            cleanRepo
        ];

        let changed = false;

        if (title !== undefined && title !== null) {
            const cleanTitle = String(title).trim();

            if (!cleanTitle)
                return refuse("ISSUE EDIT REFUSED // TITLE MAY NOT BE EMPTY");

            args.push("--title");
            args.push(cleanTitle);
            changed = true;
        }

        if (body !== undefined && body !== null) {
            args.push("--body");
            args.push(String(body));
            changed = true;
        }

        if (!changed)
            return refuse("ISSUE EDIT REFUSED // NO CHANGES");

        return startMutation(
            "edit",
            cleanRepo,
            String(issue),
            args,
            false
        );
    }

    function updateLabels(repo, number, addLabels, removeLabels) {
        const cleanRepo = normalizeRepository(repo);
        const issue = normalizeIssueNumber(number);

        if (!cleanRepo || !issue)
            return refuse("LABEL UPDATE UNAVAILABLE // TARGET MISSING");

        const args = [
            "gh",
            "issue",
            "edit",
            String(issue),
            "--repo",
            cleanRepo
        ];

        const before = args.length;
        appendRepeatedFlag(args, "--add-label", addLabels);
        appendRepeatedFlag(args, "--remove-label", removeLabels);

        if (args.length === before)
            return refuse("LABEL UPDATE REFUSED // NO CHANGES");

        return startMutation(
            "labels",
            cleanRepo,
            String(issue),
            args,
            false
        );
    }

    function updateAssignees(repo, number, addAssignees, removeAssignees) {
        const cleanRepo = normalizeRepository(repo);
        const issue = normalizeIssueNumber(number);

        if (!cleanRepo || !issue)
            return refuse("ASSIGNEE UPDATE UNAVAILABLE // TARGET MISSING");

        const args = [
            "gh",
            "issue",
            "edit",
            String(issue),
            "--repo",
            cleanRepo
        ];

        const before = args.length;
        appendRepeatedFlag(args, "--add-assignee", addAssignees);
        appendRepeatedFlag(args, "--remove-assignee", removeAssignees);

        if (args.length === before)
            return refuse("ASSIGNEE UPDATE REFUSED // NO CHANGES");

        return startMutation(
            "assignees",
            cleanRepo,
            String(issue),
            args,
            false
        );
    }

    function setMilestone(repo, number, milestone) {
        const cleanRepo = normalizeRepository(repo);
        const issue = normalizeIssueNumber(number);
        const cleanMilestone = String(milestone || "").trim();

        if (!cleanRepo || !issue || !cleanMilestone)
            return refuse("MILESTONE UPDATE UNAVAILABLE // TARGET MISSING");

        return startMutation(
            "milestone",
            cleanRepo,
            String(issue),
            [
                "gh",
                "issue",
                "edit",
                String(issue),
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
        const issue = normalizeIssueNumber(number);

        if (!cleanRepo || !issue)
            return refuse("MILESTONE CLEAR UNAVAILABLE // TARGET MISSING");

        return startMutation(
            "clear-milestone",
            cleanRepo,
            String(issue),
            [
                "gh",
                "issue",
                "edit",
                String(issue),
                "--repo",
                cleanRepo,
                "--remove-milestone"
            ],
            false
        );
    }

    function commentIssue(repo, number, body) {
        const cleanRepo = normalizeRepository(repo);
        const issue = normalizeIssueNumber(number);
        const cleanBody = String(body || "").trim();

        if (!cleanRepo || !issue || !cleanBody)
            return refuse("ISSUE COMMENT UNAVAILABLE // TARGET OR BODY MISSING");

        return startMutation(
            "comment",
            cleanRepo,
            String(issue),
            [
                "gh",
                "issue",
                "comment",
                String(issue),
                "--repo",
                cleanRepo,
                "--body",
                cleanBody
            ],
            false
        );
    }

    function closeIssue(repo, number, confirmed, reason, comment) {
        const cleanRepo = normalizeRepository(repo);
        const issue = normalizeIssueNumber(number);
        const cleanReason =
            String(reason || "completed").trim().toLowerCase();

        if (!confirmed)
            return refuse("ISSUE CLOSE REFUSED // EXPLICIT CONFIRMATION REQUIRED");
        if (!cleanRepo || !issue)
            return refuse("ISSUE CLOSE UNAVAILABLE // TARGET MISSING");
        if (["completed", "not planned"].indexOf(cleanReason) < 0)
            return refuse("ISSUE CLOSE REFUSED // INVALID REASON");

        const args = [
            "gh",
            "issue",
            "close",
            String(issue),
            "--repo",
            cleanRepo,
            "--reason",
            cleanReason
        ];

        const cleanComment = String(comment || "").trim();
        if (cleanComment) {
            args.push("--comment");
            args.push(cleanComment);
        }

        return startMutation(
            "close",
            cleanRepo,
            String(issue),
            args,
            false
        );
    }

    function reopenIssue(repo, number, comment) {
        const cleanRepo = normalizeRepository(repo);
        const issue = normalizeIssueNumber(number);

        if (!cleanRepo || !issue)
            return refuse("ISSUE REOPEN UNAVAILABLE // TARGET MISSING");

        const args = [
            "gh",
            "issue",
            "reopen",
            String(issue),
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
            String(issue),
            args,
            false
        );
    }

    function createdIssueTarget(text) {
        const lines = String(text || "").trim().split("\n");

        for (let i = lines.length - 1; i >= 0; --i) {
            const line = String(lines[i] || "").trim();

            if (/^https:\/\/github\.com\/[^/]+\/[^/]+\/issues\/\d+$/.test(line))
                return line;
        }

        return "";
    }

    function startEvidenceRead(target) {
        const cleanTarget = String(target || "").trim();

        if (!cleanTarget) {
            finishWithoutEvidence("MUTATION SUCCEEDED // ISSUE TARGET UNKNOWN");
            return;
        }

        phase = "VERIFYING";
        pendingEvidenceTarget = cleanTarget;
        status =
            "ISSUE // "
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
            "issue",
            "view",
            cleanTarget,
            "--repo",
            pendingRepository,
            "--json",
            "number,title,body,state,stateReason,url,labels,assignees,milestone,author,createdAt,updatedAt,closed,closedAt"
        ]);
    }

    function finishWithoutEvidence(detail) {
        busy = false;
        phase = "READY";
        evidenceVerified = false;
        lastError = String(detail || "ISSUE EVIDENCE UNAVAILABLE");
        status =
            "ISSUE // "
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
                    || ("ISSUE MUTATION EXIT " + mutationExitCode)
                ).trim();
            status =
                "ISSUE // "
                + operation.toUpperCase()
                + " // ERROR";
            watchdog.stop();
            mutationFinished(false, false, operation, ({}));
            return;
        }

        mutationSucceeded = true;

        const target =
            pendingTargetFromStdout
            ? createdIssueTarget(mutationStdoutText)
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
                    || ("ISSUE EVIDENCE EXIT " + evidenceExitCode)
                ).trim()
            );
            return;
        }

        try {
            const row = JSON.parse(String(evidenceStdoutText || "{}"));

            evidence = {
                operation: operation,
                repository: pendingRepository,
                issue: row
            };
            issueNumber = Number(row.number || 0);
            issueUrl = String(row.url || "");
            evidenceVerified = issueNumber > 0 && issueUrl.length > 0;
            busy = false;
            phase = "READY";
            lastError = "";
            status =
                "ISSUE // "
                + operation.toUpperCase()
                + " // VERIFIED // #"
                + String(issueNumber);
            watchdog.stop();

            issueChanged(
                pendingRepository,
                issueNumber,
                issueUrl
            );
            mutationFinished(
                true,
                evidenceVerified,
                operation,
                evidence
            );
        } catch (parseError) {
            finishWithoutEvidence(
                "ISSUE EVIDENCE PARSE // " + String(parseError)
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
                ? "ISSUE MUTATED // EVIDENCE TIMEOUT"
                : "ISSUE MUTATION TIMEOUT";
            root.status =
                wasMutationSucceeded
                ? "ISSUE // MUTATED // EVIDENCE UNVERIFIED"
                : "ISSUE // TIMEOUT";

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
