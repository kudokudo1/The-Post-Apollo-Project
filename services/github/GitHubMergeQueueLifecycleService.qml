import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property bool busy: false
    property string phase: "READY"
    property string operation: ""
    property string status: "MERGE QUEUE // READY"
    property string lastError: ""
    property var preview: ({})
    property var evidence: ({})
    property bool mutationSucceeded: false
    property bool evidenceVerified: false

    property bool exitSeen: false
    property bool stdoutSeen: false
    property bool stderrSeen: false
    property int exitCode: -1
    property string stdoutText: ""
    property string stderrText: ""

    signal previewReady(var preview)
    signal previewFailed(string detail)
    signal queueChanged(string repository, int pullRequestNumber, bool queued, var evidence)
    signal mutationFinished(bool mutationSucceeded, bool evidenceVerified, string operation, var evidence)

    function normalizeRepository(value) {
        const slug = String(value || "").trim();
        return /^[^/\s]+\/[^/\s]+$/.test(slug) ? slug : "";
    }

    function normalizePullRequestNumber(value) {
        const n = Number(value || 0);
        return Number.isFinite(n) && n > 0 ? Math.floor(n) : 0;
    }

    function normalizeHeadSha(value) {
        const s = String(value || "").trim();
        return /^[0-9a-fA-F]{40}$/.test(s) ? s.toLowerCase() : "";
    }

    function refuse(detail) {
        lastError = String(detail || "MERGE QUEUE OPERATION REFUSED");
        status = "MERGE QUEUE // REFUSED // " + lastError;
        return false;
    }

    function resetIo() {
        exitSeen = false;
        stdoutSeen = false;
        stderrSeen = false;
        exitCode = -1;
        stdoutText = "";
        stderrText = "";
    }

    function clearPreview() {
        preview = ({});
    }

    function previewEnqueue(repository, number, expectedHeadSha) {
        return startPreview("enqueue", repository, number, expectedHeadSha);
    }

    function previewDequeue(repository, number) {
        return startPreview("dequeue", repository, number, "");
    }

    function startPreview(action, repository, number, expectedHeadSha) {
        if (busy)
            return false;

        const r = normalizeRepository(repository);
        const n = normalizePullRequestNumber(number);
        const h = action === "enqueue" ? normalizeHeadSha(expectedHeadSha) : "";

        clearPreview();
        lastError = "";

        if (!r || !n)
            return refuse("PREVIEW REFUSED // PULL REQUEST TARGET MISSING");
        if (action === "enqueue" && !h)
            return refuse("ENQUEUE PREVIEW REFUSED // EXPECTED HEAD SHA REQUIRED");

        busy = true;
        phase = "PREVIEW";
        operation = action;
        status = "MERGE QUEUE // " + action.toUpperCase() + " // PREVIEWING";
        resetIo();

        worker.exec([
            "bash", "-lc",
            [
                'repo="$1"; number="$2"; expected="$3"',
                'owner="$(printf "%s" "$repo" | cut -d/ -f1)"',
                'name="$(printf "%s" "$repo" | cut -d/ -f2-)"',
                "pq='query($owner:String!,$name:String!,$number:Int!){repository(owner:$owner,name:$name){pullRequest(number:$number){id number url state isDraft headRefOid baseRefName mergeable mergeStateStatus reviewDecision mergeQueueEntry{id position state enqueuedAt estimatedTimeToMerge jump solo enqueuer{login} baseCommit{oid} headCommit{oid}}}}}'",
                'pp="$(gh api graphql -F owner="$owner" -F name="$name" -F number="$number" -f query="$pq")" || exit $?',
                'pr="$(printf "%s" "$pp" | jq -c ".data.repository.pullRequest")"',
                '[ "$pr" != "null" ] || { printf "PULL REQUEST NOT FOUND\\n" >&2; exit 22; }',
                'state="$(printf "%s" "$pr" | jq -r ".state")"',
                'draft="$(printf "%s" "$pr" | jq -r ".isDraft")"',
                'head="$(printf "%s" "$pr" | jq -r ".headRefOid")"',
                'base="$(printf "%s" "$pr" | jq -r ".baseRefName")"',
                '[ "$state" = "OPEN" ] || { printf "PULL REQUEST IS NOT OPEN\\n" >&2; exit 23; }',
                '[ "$draft" != "true" ] || { printf "DRAFT PULL REQUEST CANNOT ENTER MERGE QUEUE\\n" >&2; exit 24; }',
                'if [ -n "$expected" ] && [ "$(printf "%s" "$head" | tr "A-F" "a-f")" != "$(printf "%s" "$expected" | tr "A-F" "a-f")" ]; then printf "PULL REQUEST HEAD MOVED\\n" >&2; exit 25; fi',
                "qq='query($owner:String!,$name:String!,$branch:String!){repository(owner:$owner,name:$name){mergeQueue(branch:$branch){id url nextEntryEstimatedTimeToMerge configuration{checkResponseTimeout maximumEntriesToBuild maximumEntriesToMerge mergeMethod mergingStrategy minimumEntriesToMerge minimumEntriesToMergeWaitTime}}}}'",
                'qp="$(gh api graphql -F owner="$owner" -F name="$name" -F branch="$base" -f query="$qq")" || exit $?',
                'queue="$(printf "%s" "$qp" | jq -c ".data.repository.mergeQueue")"',
                '[ "$queue" != "null" ] || { printf "NATIVE MERGE QUEUE NOT CONFIGURED\\n" >&2; exit 27; }',
                'jq -nc --arg repository "$repo" --arg expectedHead "$expected" --argjson pullRequest "$pr" --argjson mergeQueue "$queue" \'{repository:$repository,expectedHead:$expectedHead,pullRequest:$pullRequest,mergeQueue:$mergeQueue}\''
            ].join("\\n"),
            "pa-merge-queue-preview", r, String(n), h
        ]);

        watchdog.restart();
        return true;
    }

    function parsePreview() {
        const row = JSON.parse(String(stdoutText || "{}"));
        const pr = row.pullRequest || {};
        const queue = row.mergeQueue || {};
        const entry = pr.mergeQueueEntry || null;
        const head = normalizeHeadSha(pr.headRefOid);
        const expected = normalizeHeadSha(row.expectedHead);

        if (!pr.id || !pr.number || !head || !pr.baseRefName || !queue.id)
            throw new Error("PREVIEW IDENTITY INCOMPLETE");
        if (operation === "enqueue" && expected !== head)
            throw new Error("PREVIEW HEAD MISMATCH");
        if (operation === "enqueue" && entry)
            throw new Error("PULL REQUEST IS ALREADY QUEUED");
        if (operation === "dequeue" && !entry)
            throw new Error("PULL REQUEST IS NOT CURRENTLY QUEUED");

        preview = {
            action: operation,
            repository: String(row.repository || ""),
            number: Number(pr.number || 0),
            pullRequestId: String(pr.id || ""),
            url: String(pr.url || ""),
            headSha: head,
            baseBranch: String(pr.baseRefName || ""),
            mergeable: String(pr.mergeable || ""),
            mergeStateStatus: String(pr.mergeStateStatus || ""),
            reviewDecision: String(pr.reviewDecision || ""),
            queueId: String(queue.id || ""),
            queueUrl: String(queue.url || ""),
            queueConfiguration: queue.configuration || {},
            entry: entry
        };
    }

    function executeEnqueue() {
        if (busy)
            return false;
        if (String(preview.action || "") !== "enqueue")
            return refuse("ENQUEUE REFUSED // ENQUEUE PREVIEW REQUIRED");
        return startMutation("enqueue");
    }

    function executeDequeue(confirmed) {
        if (busy)
            return false;
        if (!confirmed)
            return refuse("DEQUEUE REFUSED // EXPLICIT CONFIRMATION REQUIRED");
        if (String(preview.action || "") !== "dequeue")
            return refuse("DEQUEUE REFUSED // DEQUEUE PREVIEW REQUIRED");
        return startMutation("dequeue");
    }

    function startMutation(action) {
        if (!preview.pullRequestId || !preview.number || !preview.repository)
            return refuse("MERGE QUEUE PREVIEW IDENTITY MISSING");

        busy = true;
        phase = "MUTATING";
        operation = action;
        mutationSucceeded = false;
        evidenceVerified = false;
        evidence = ({});
        lastError = "";
        status = "MERGE QUEUE // " + action.toUpperCase() + " // WORKING";
        resetIo();

        if (action === "enqueue") {
            worker.exec([
                "bash", "-lc",
                [
                    'id="$1"; head="$2"',
                    "q='mutation($pullRequestId:ID!,$expectedHeadOid:GitObjectID!){enqueuePullRequest(input:{pullRequestId:$pullRequestId,expectedHeadOid:$expectedHeadOid,jump:false}){mergeQueueEntry{id position state enqueuedAt estimatedTimeToMerge jump solo pullRequest{number headRefOid}}}}'",
                    'exec gh api graphql -F pullRequestId="$id" -F expectedHeadOid="$head" -f query="$q"'
                ].join("\\n"),
                "pa-merge-queue-enqueue",
                String(preview.pullRequestId),
                String(preview.headSha)
            ]);
        } else {
            worker.exec([
                "bash", "-lc",
                [
                    'id="$1"',
                    "q='mutation($id:ID!){dequeuePullRequest(input:{id:$id}){mergeQueueEntry{id position state pullRequest{number}}}}'",
                    'exec gh api graphql -F id="$id" -f query="$q"'
                ].join("\\n"),
                "pa-merge-queue-dequeue",
                String(preview.pullRequestId)
            ]);
        }

        watchdog.restart();
        return true;
    }

    function startVerify() {
        phase = "VERIFYING";
        status = "MERGE QUEUE // " + operation.toUpperCase() + " // VERIFYING";
        resetIo();

        worker.exec([
            "bash", "-lc",
            [
                'repo="$1"; number="$2"; branch="$3"',
                'owner="$(printf "%s" "$repo" | cut -d/ -f1)"',
                'name="$(printf "%s" "$repo" | cut -d/ -f2-)"',
                "q='query($owner:String!,$name:String!,$number:Int!,$branch:String!){repository(owner:$owner,name:$name){pullRequest(number:$number){id number url state isDraft headRefOid baseRefName mergeQueueEntry{id position state enqueuedAt estimatedTimeToMerge jump solo enqueuer{login} baseCommit{oid} headCommit{oid}}} mergeQueue(branch:$branch){id url nextEntryEstimatedTimeToMerge configuration{checkResponseTimeout maximumEntriesToBuild maximumEntriesToMerge mergeMethod mergingStrategy minimumEntriesToMerge minimumEntriesToMergeWaitTime}}}}'",
                'exec gh api graphql -F owner="$owner" -F name="$name" -F number="$number" -F branch="$branch" -f query="$q"'
            ].join("\\n"),
            "pa-merge-queue-verify",
            String(preview.repository),
            String(preview.number),
            String(preview.baseBranch)
        ]);

        watchdog.restart();
    }

    function finishUnverified(detail) {
        busy = false;
        phase = "READY";
        evidenceVerified = false;
        lastError = String(detail || "MERGE QUEUE EVIDENCE UNAVAILABLE");
        status = "MERGE QUEUE // " + operation.toUpperCase() + " // MUTATED // EVIDENCE UNVERIFIED";
        watchdog.stop();

        mutationFinished(true, false, operation, {
            repository: preview.repository,
            pullRequestNumber: preview.number,
            headSha: preview.headSha,
            error: lastError
        });
    }

    function handleFinished() {
        if (!exitSeen || !stdoutSeen || !stderrSeen)
            return;

        watchdog.stop();
        const out = String(stdoutText || "").trim();
        const err = String(stderrText || "").trim();

        if (exitCode !== 0) {
            if (phase === "PREVIEW") {
                busy = false;
                phase = "READY";
                clearPreview();
                lastError = err || out || ("MERGE QUEUE PREVIEW EXIT " + exitCode);
                status = "MERGE QUEUE // PREVIEW ERROR";
                previewFailed(lastError);
                return;
            }
            if (phase === "VERIFYING") {
                finishUnverified(err || out || ("MERGE QUEUE EVIDENCE EXIT " + exitCode));
                return;
            }
            busy = false;
            phase = "READY";
            mutationSucceeded = false;
            evidenceVerified = false;
            lastError = err || out || ("MERGE QUEUE MUTATION EXIT " + exitCode);
            status = "MERGE QUEUE // " + operation.toUpperCase() + " // ERROR";
            mutationFinished(false, false, operation, ({}));
            return;
        }

        if (phase === "PREVIEW") {
            try {
                parsePreview();
                busy = false;
                phase = "READY";
                status = "MERGE QUEUE // " + operation.toUpperCase() + " // PREVIEW READY // #" + String(preview.number);
                previewReady(preview);
            } catch (e) {
                busy = false;
                phase = "READY";
                clearPreview();
                lastError = "MERGE QUEUE PREVIEW PARSE // " + String(e);
                status = "MERGE QUEUE // PREVIEW ERROR";
                previewFailed(lastError);
            }
            return;
        }

        if (phase === "MUTATING") {
            mutationSucceeded = true;
            startVerify();
            return;
        }

        try {
            const parsed = JSON.parse(out || "{}");
            const repository = ((parsed.data || {}).repository) || {};
            const pr = repository.pullRequest || {};
            const entry = pr.mergeQueueEntry || null;
            const currentHead = normalizeHeadSha(pr.headRefOid);
            const queued = Boolean(entry);
            const expectedQueued = operation === "enqueue";

            evidence = {
                operation: operation,
                repository: preview.repository,
                pullRequestNumber: Number(pr.number || 0),
                pullRequestUrl: String(pr.url || ""),
                expectedHeadSha: preview.headSha,
                currentHeadSha: currentHead,
                baseBranch: String(pr.baseRefName || ""),
                queued: queued,
                entry: entry,
                queue: repository.mergeQueue || {}
            };

            if (currentHead !== preview.headSha)
                throw new Error("PULL REQUEST HEAD MOVED DURING OPERATION");
            if (queued !== expectedQueued)
                throw new Error(expectedQueued ? "ENQUEUE NOT VISIBLE AFTER MUTATION" : "DEQUEUE NOT VISIBLE AFTER MUTATION");

            busy = false;
            phase = "READY";
            evidenceVerified = true;
            lastError = "";
            status = "MERGE QUEUE // " + operation.toUpperCase() + " // VERIFIED // #" + String(preview.number);
            queueChanged(preview.repository, preview.number, queued, evidence);
            mutationFinished(true, true, operation, evidence);
            clearPreview();
        } catch (e) {
            finishUnverified("MERGE QUEUE EVIDENCE PARSE // " + String(e));
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
                root.finishUnverified("MERGE QUEUE MUTATED // EVIDENCE TIMEOUT");
                return;
            }

            root.busy = false;
            root.phase = "READY";
            root.lastError =
                "MERGE QUEUE "
                + root.operation.toUpperCase()
                + " TIMEOUT";
            root.status = "MERGE QUEUE // TIMEOUT";

            if (timedOutPhase === "PREVIEW")
                root.previewFailed(root.lastError);
            else
                root.mutationFinished(false, false, root.operation, ({}));
        }
    }
}
