import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property bool busy: false
    property string phase: "READY"
    property string operation: ""
    property string status: "PR THREAD ACTIONS // READY"
    property string lastError: ""

    property string repository: ""
    property int pullRequestNumber: 0
    property string threadId: ""
    property string topLevelCommentId: ""
    property string replyBody: ""
    property var preflightThread: ({})
    property int preflightCommentCount: 0
    property string createdReplyId: ""

    property bool mutationSucceeded: false
    property bool evidenceVerified: false
    property var evidence: ({})

    property bool stdoutSeen: false
    property bool stderrSeen: false
    property bool exitSeen: false
    property int exitCode: -1
    property string stdoutText: ""
    property string stderrText: ""

    signal threadChanged(
        string repository,
        int pullRequestNumber,
        string threadId,
        var evidence
    )
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

    function normalizeThreadId(value) {
        return String(value || "").trim();
    }

    function normalizeCommentId(value) {
        const id = String(value || "").trim();
        return /^\d+$/.test(id) ? id : "";
    }

    function refuse(detail) {
        lastError = String(detail || "PR THREAD ACTION REFUSED");
        status = "PR THREAD ACTIONS // REFUSED // " + lastError;
        return false;
    }

    function resetIo() {
        stdoutSeen = false;
        stderrSeen = false;
        exitSeen = false;
        exitCode = -1;
        stdoutText = "";
        stderrText = "";
    }

    function replyToThread(
        repo,
        number,
        reviewThreadId,
        topCommentFullDatabaseId,
        body
    ) {
        const text = String(body || "").trim();

        if (!text)
            return refuse("THREAD REPLY REFUSED // BODY REQUIRED");

        return start(
            "reply",
            repo,
            number,
            reviewThreadId,
            topCommentFullDatabaseId,
            text,
            true
        );
    }

    function resolveThread(repo, number, reviewThreadId, confirmed) {
        if (!confirmed)
            return refuse("THREAD RESOLVE REFUSED // EXPLICIT CONFIRMATION REQUIRED");

        return start(
            "resolve",
            repo,
            number,
            reviewThreadId,
            "",
            "",
            false
        );
    }

    function unresolveThread(repo, number, reviewThreadId, confirmed) {
        if (!confirmed)
            return refuse("THREAD UNRESOLVE REFUSED // EXPLICIT CONFIRMATION REQUIRED");

        return start(
            "unresolve",
            repo,
            number,
            reviewThreadId,
            "",
            "",
            false
        );
    }

    function start(
        action,
        repo,
        number,
        reviewThreadId,
        topCommentFullDatabaseId,
        body,
        requireComment
    ) {
        if (busy)
            return false;

        const cleanRepo = normalizeRepository(repo);
        const pr = normalizePullRequestNumber(number);
        const cleanThread = normalizeThreadId(reviewThreadId);
        const cleanComment =
            requireComment
            ? normalizeCommentId(topCommentFullDatabaseId)
            : "";

        if (!cleanRepo || !pr || !cleanThread)
            return refuse("PR THREAD ACTION REFUSED // TARGET MISSING");
        if (requireComment && !cleanComment)
            return refuse("THREAD REPLY REFUSED // TOP-LEVEL COMMENT ID REQUIRED");

        busy = true;
        phase = "PREFLIGHT";
        operation = String(action || "");
        repository = cleanRepo;
        pullRequestNumber = pr;
        threadId = cleanThread;
        topLevelCommentId = cleanComment;
        replyBody = String(body || "");
        preflightThread = ({});
        preflightCommentCount = 0;
        createdReplyId = "";
        mutationSucceeded = false;
        evidenceVerified = false;
        evidence = ({});
        lastError = "";
        status =
            "PR THREAD ACTIONS // "
            + operation.toUpperCase()
            + " // PREFLIGHT";

        readThread();
        return true;
    }

    function readThread() {
        resetIo();

        const owner = repository.split("/")[0];
        const name = repository.slice(owner.length + 1);

        worker.exec([
            "gh",
            "api",
            "graphql",
            "-F", "owner=" + owner,
            "-F", "name=" + name,
            "-F", "number=" + String(pullRequestNumber),
            "-f",
            "query="
            + "query($owner:String!,$name:String!,$number:Int!){"
            + "repository(owner:$owner,name:$name){"
            + "pullRequest(number:$number){"
            + "id number url state headRefOid "
            + "reviewThreads(first:100){nodes{"
            + "id isResolved isOutdated viewerCanReply viewerCanResolve viewerCanUnresolve "
            + "path line originalLine resolvedBy{login} "
            + "comments(first:100){totalCount nodes{"
            + "id fullDatabaseId body author{login} createdAt updatedAt"
            + "}}"
            + "}}"
            + "}}"
            + "}"
        ]);

        watchdog.restart();
    }

    function threadFromResponse(text) {
        const parsed = JSON.parse(String(text || "{}"));
        const pr =
            ((((parsed || {}).data || {}).repository || {}).pullRequest)
            || null;

        if (!pr)
            throw new Error("PULL REQUEST NOT FOUND");

        const nodes =
            (((pr.reviewThreads || {}).nodes)
                && Array.isArray((pr.reviewThreads || {}).nodes))
            ? pr.reviewThreads.nodes
            : [];
        let found = null;

        for (let i = 0; i < nodes.length; ++i) {
            if (String((nodes[i] || {}).id || "") === threadId) {
                found = nodes[i];
                break;
            }
        }

        if (!found)
            throw new Error("REVIEW THREAD NOT FOUND IN FRESH PR READ");

        return {
            pullRequest: {
                id: String(pr.id || ""),
                number: Number(pr.number || 0),
                url: String(pr.url || ""),
                state: String(pr.state || ""),
                headRefOid: String(pr.headRefOid || "")
            },
            thread: found
        };
    }

    function firstCommentId(thread) {
        const nodes =
            ((((thread || {}).comments || {}).nodes)
                && Array.isArray(((thread || {}).comments || {}).nodes))
            ? (thread.comments.nodes)
            : [];

        if (nodes.length === 0)
            return "";

        return String((nodes[0] || {}).fullDatabaseId || "");
    }

    function commentCount(thread) {
        return Number((((thread || {}).comments || {}).totalCount) || 0);
    }

    function preflightAllowed(thread) {
        if (operation === "reply") {
            if (!Boolean(thread.viewerCanReply))
                throw new Error("VIEWER CANNOT REPLY TO REVIEW THREAD");

            const firstId = normalizeCommentId(firstCommentId(thread));

            if (!firstId || firstId !== topLevelCommentId)
                throw new Error("TOP-LEVEL COMMENT ID DOES NOT MATCH FRESH THREAD");

            return;
        }

        if (operation === "resolve") {
            if (Boolean(thread.isResolved))
                throw new Error("REVIEW THREAD IS ALREADY RESOLVED");
            if (!Boolean(thread.viewerCanResolve))
                throw new Error("VIEWER CANNOT RESOLVE REVIEW THREAD");
            return;
        }

        if (operation === "unresolve") {
            if (!Boolean(thread.isResolved))
                throw new Error("REVIEW THREAD IS ALREADY UNRESOLVED");
            if (!Boolean(thread.viewerCanUnresolve))
                throw new Error("VIEWER CANNOT UNRESOLVE REVIEW THREAD");
            return;
        }

        throw new Error("UNKNOWN REVIEW THREAD ACTION");
    }

    function startMutation() {
        phase = "MUTATING";
        status =
            "PR THREAD ACTIONS // "
            + operation.toUpperCase()
            + " // WORKING";
        resetIo();

        if (operation === "reply") {
            worker.exec([
                "gh",
                "api",
                "--method", "POST",
                "repos/"
                    + repository
                    + "/pulls/"
                    + String(pullRequestNumber)
                    + "/comments/"
                    + topLevelCommentId
                    + "/replies",
                "-f", "body=" + replyBody
            ]);
        } else if (operation === "resolve") {
            worker.exec([
                "gh",
                "api",
                "graphql",
                "-F", "threadId=" + threadId,
                "-f",
                "query="
                + "mutation($threadId:ID!){"
                + "resolveReviewThread(input:{threadId:$threadId}){"
                + "thread{id isResolved}"
                + "}}"
            ]);
        } else {
            worker.exec([
                "gh",
                "api",
                "graphql",
                "-F", "threadId=" + threadId,
                "-f",
                "query="
                + "mutation($threadId:ID!){"
                + "unresolveReviewThread(input:{threadId:$threadId}){"
                + "thread{id isResolved}"
                + "}}"
            ]);
        }

        watchdog.restart();
    }

    function startVerification() {
        phase = "VERIFYING";
        status =
            "PR THREAD ACTIONS // "
            + operation.toUpperCase()
            + " // VERIFYING";
        readThread();
    }

    function finishUnverified(detail) {
        busy = false;
        phase = "READY";
        evidenceVerified = false;
        lastError =
            String(detail || "PR THREAD EVIDENCE UNAVAILABLE");
        status =
            "PR THREAD ACTIONS // "
            + operation.toUpperCase()
            + " // MUTATED // EVIDENCE UNVERIFIED";
        watchdog.stop();

        mutationFinished(
            true,
            false,
            operation,
            {
                repository: repository,
                pullRequestNumber: pullRequestNumber,
                threadId: threadId,
                error: lastError
            }
        );
    }

    function verifyResult(fresh) {
        const thread = fresh.thread || {};
        const comments =
            ((((thread || {}).comments || {}).nodes)
                && Array.isArray(((thread || {}).comments || {}).nodes))
            ? thread.comments.nodes
            : [];

        if (operation === "reply") {
            if (!createdReplyId)
                throw new Error("REPLY MUTATION DID NOT RETURN COMMENT ID");

            let found = false;

            for (let i = 0; i < comments.length; ++i) {
                if (String((comments[i] || {}).fullDatabaseId || "")
                        === createdReplyId) {
                    found = true;
                    break;
                }
            }

            if (!found)
                throw new Error("REPLY NOT VISIBLE AFTER MUTATION");

            if (commentCount(thread) <= preflightCommentCount)
                throw new Error("THREAD COMMENT COUNT DID NOT ADVANCE");
        } else if (operation === "resolve") {
            if (!Boolean(thread.isResolved))
                throw new Error("RESOLVE NOT VISIBLE AFTER MUTATION");
        } else if (operation === "unresolve") {
            if (Boolean(thread.isResolved))
                throw new Error("UNRESOLVE NOT VISIBLE AFTER MUTATION");
        }

        evidence = {
            operation: operation,
            repository: repository,
            pullRequest: fresh.pullRequest,
            thread: thread,
            createdReplyId: createdReplyId
        };
        evidenceVerified = true;
        busy = false;
        phase = "READY";
        lastError = "";
        status =
            "PR THREAD ACTIONS // "
            + operation.toUpperCase()
            + " // VERIFIED";
        watchdog.stop();

        threadChanged(
            repository,
            pullRequestNumber,
            threadId,
            evidence
        );
        mutationFinished(
            true,
            true,
            operation,
            evidence
        );
    }

    function handleFinished() {
        if (!busy || !stdoutSeen || !stderrSeen || !exitSeen)
            return;

        watchdog.stop();

        const output = String(stdoutText || "").trim();
        const error = String(stderrText || "").trim();

        if (exitCode !== 0) {
            if (phase === "VERIFYING") {
                finishUnverified(
                    error
                    || output
                    || ("PR THREAD EVIDENCE EXIT " + exitCode)
                );
                return;
            }

            busy = false;
            phase = "READY";
            mutationSucceeded = false;
            evidenceVerified = false;
            lastError =
                error
                || output
                || ("PR THREAD ACTION EXIT " + exitCode);
            status = "PR THREAD ACTIONS // ERROR";
            mutationFinished(false, false, operation, ({}));
            return;
        }

        if (phase === "PREFLIGHT") {
            try {
                const fresh = threadFromResponse(output);
                preflightAllowed(fresh.thread);
                preflightThread = fresh.thread;
                preflightCommentCount =
                    commentCount(fresh.thread);
                startMutation();
            } catch (preflightError) {
                busy = false;
                phase = "READY";
                lastError =
                    "PR THREAD PREFLIGHT // "
                    + String(preflightError);
                status = "PR THREAD ACTIONS // REFUSED";
                mutationFinished(false, false, operation, ({}));
            }
            return;
        }

        if (phase === "MUTATING") {
            if (operation === "reply") {
                try {
                    const response =
                        JSON.parse(output || "{}");
                    createdReplyId =
                        normalizeCommentId(response.id);

                    if (!createdReplyId)
                        throw new Error("REPLY COMMENT ID MISSING");
                } catch (replyError) {
                    mutationSucceeded = true;
                    finishUnverified(
                        "REPLY MUTATED // RESPONSE PARSE // "
                        + String(replyError)
                    );
                    return;
                }
            }

            mutationSucceeded = true;
            startVerification();
            return;
        }

        try {
            verifyResult(threadFromResponse(output));
        } catch (verifyError) {
            finishUnverified(
                "PR THREAD VERIFY // "
                + String(verifyError)
            );
        }
    }

    Process {
        id: worker

        stdout: StdioCollector {
            onStreamFinished: {
                root.stdoutText = this.text;
                root.stdoutSeen = true;
                root.handleFinished();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.stderrText = this.text;
                root.stderrSeen = true;
                root.handleFinished();
            }
        }

        onExited: function(code, exitStatus) {
            root.exitCode = Number(code);
            root.exitSeen = true;
            root.handleFinished();
        }
    }

    Timer {
        id: watchdog
        interval: 120000
        repeat: false

        onTriggered: {
            const timedOutPhase = root.phase;
            const mutated =
                timedOutPhase === "VERIFYING"
                && root.mutationSucceeded;

            if (worker.running)
                worker.running = false;

            if (mutated) {
                root.finishUnverified(
                    "PR THREAD MUTATED // EVIDENCE TIMEOUT"
                );
                return;
            }

            root.busy = false;
            root.phase = "READY";
            root.lastError =
                "PR THREAD "
                + root.operation.toUpperCase()
                + " // "
                + timedOutPhase
                + " TIMEOUT";
            root.status = "PR THREAD ACTIONS // TIMEOUT";
            root.mutationFinished(
                false,
                false,
                root.operation,
                ({})
            );
        }
    }
}
