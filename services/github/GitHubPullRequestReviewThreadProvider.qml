import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property string repositorySlug: ""
    property int pullRequestNumber: 0
    property int maxThreads: 100
    property int maxCommentsPerThread: 100

    property bool busy: false
    property var threads: []
    property var pullRequest: ({})
    property int totalThreadCount: 0
    property bool threadsTruncated: false
    property bool commentsTruncated: false
    property string status: "PR THREADS // READY"
    property string lastError: ""

    property bool stdoutSeen: false
    property bool stderrSeen: false
    property bool exitSeen: false
    property int exitCode: -1
    property string stdoutText: ""
    property string stderrText: ""

    signal refreshed()

    readonly property int threadCount: threads.length
    readonly property int unresolvedCount: countWhere("UNRESOLVED")
    readonly property int resolvedCount: countWhere("RESOLVED")
    readonly property int outdatedCount: countWhere("OUTDATED")
    readonly property int activeUnresolvedCount: countWhere("ACTIVE_UNRESOLVED")
    readonly property int replyableCount: countWhere("REPLYABLE")
    readonly property int resolvableCount: countWhere("RESOLVABLE")

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

    function threadAt(index) {
        const i = Number(index);

        if (isNaN(i) || i < 0 || i >= threads.length)
            return null;

        return threads[i];
    }

    function threadsForPath(path) {
        const target = String(path || "");
        const out = [];

        for (let i = 0; i < threads.length; ++i) {
            if (String((threads[i] || {}).path || "") === target)
                out.push(threads[i]);
        }

        return out;
    }

    function unresolvedThreads() {
        const out = [];

        for (let i = 0; i < threads.length; ++i) {
            if (!(threads[i] || {}).isResolved)
                out.push(threads[i]);
        }

        return out;
    }

    function countWhere(kind) {
        let count = 0;

        for (let i = 0; i < threads.length; ++i) {
            const row = threads[i] || {};
            const matched =
                kind === "UNRESOLVED"
                ? !row.isResolved
                : kind === "RESOLVED"
                ? !!row.isResolved
                : kind === "OUTDATED"
                ? !!row.isOutdated
                : kind === "ACTIVE_UNRESOLVED"
                ? !row.isResolved && !row.isOutdated
                : kind === "REPLYABLE"
                ? !!row.viewerCanReply
                : kind === "RESOLVABLE"
                ? !!row.viewerCanResolve
                : false;

            if (matched)
                ++count;
        }

        return count;
    }

    function normalizeComment(value) {
        const row = value || {};
        const author = row.author || {};
        const review = row.pullRequestReview || {};
        const reviewAuthor = review.author || {};
        const replyTo = row.replyTo || {};

        return {
            id: String(row.id || ""),
            fullDatabaseId: String(row.fullDatabaseId || ""),
            body: String(row.body || ""),
            bodyText: String(row.bodyText || row.body || ""),
            resourcePath: String(row.resourcePath || ""),
            authorLogin: String(author.login || ""),
            authorAvatarUrl: String(author.avatarUrl || ""),
            authorUrl: String(author.url || ""),
            authorAssociation: String(row.authorAssociation || ""),
            state: String(row.state || ""),
            createdAt: String(row.createdAt || ""),
            updatedAt: String(row.updatedAt || ""),
            publishedAt: String(row.publishedAt || ""),
            path: String(row.path || ""),
            line: row.line === null || row.line === undefined ? -1 : Number(row.line),
            originalLine:
                row.originalLine === null || row.originalLine === undefined
                ? -1
                : Number(row.originalLine),
            startLine:
                row.startLine === null || row.startLine === undefined
                ? -1
                : Number(row.startLine),
            originalStartLine:
                row.originalStartLine === null || row.originalStartLine === undefined
                ? -1
                : Number(row.originalStartLine),
            diffHunk: String(row.diffHunk || ""),
            outdated: Boolean(row.outdated),
            commitOid: String(((row.commit || {}).oid) || ""),
            originalCommitOid:
                String(((row.originalCommit || {}).oid) || ""),
            replyToId: String(replyTo.id || ""),
            replyToFullDatabaseId: String(replyTo.fullDatabaseId || ""),
            reviewId: String(review.id || ""),
            reviewState: String(review.state || ""),
            reviewAuthorLogin: String(reviewAuthor.login || "")
        };
    }

    function normalizeThread(value) {
        const row = value || {};
        const source =
            ((row.comments || {}).nodes
                && Array.isArray((row.comments || {}).nodes))
            ? row.comments.nodes
            : [];
        const comments = [];

        for (let i = 0; i < source.length; ++i)
            comments.push(normalizeComment(source[i]));

        const commentTotal = Number((row.comments || {}).totalCount || 0);
        const pageInfo = (row.comments || {}).pageInfo || {};
        const latest =
            comments.length > 0
            ? comments[comments.length - 1]
            : null;

        return {
            id: String(row.id || ""),
            isResolved: Boolean(row.isResolved),
            isOutdated: Boolean(row.isOutdated),
            isCollapsed: Boolean(row.isCollapsed),
            path: String(row.path || ""),
            line:
                row.line === null || row.line === undefined
                ? -1
                : Number(row.line),
            originalLine:
                row.originalLine === null || row.originalLine === undefined
                ? -1
                : Number(row.originalLine),
            startLine:
                row.startLine === null || row.startLine === undefined
                ? -1
                : Number(row.startLine),
            originalStartLine:
                row.originalStartLine === null || row.originalStartLine === undefined
                ? -1
                : Number(row.originalStartLine),
            diffSide: String(row.diffSide || ""),
            startDiffSide: String(row.startDiffSide || ""),
            subjectType: String(row.subjectType || ""),
            viewerCanReply: Boolean(row.viewerCanReply),
            viewerCanResolve: Boolean(row.viewerCanResolve),
            viewerCanUnresolve: Boolean(row.viewerCanUnresolve),
            resolvedBy: String(((row.resolvedBy || {}).login) || ""),
            commentCount: commentTotal,
            commentsTruncated:
                Boolean(pageInfo.hasNextPage)
                || commentTotal > comments.length,
            comments: comments,
            latestComment: latest,
            latestCommentAuthor:
                latest
                ? String(latest.authorLogin || "")
                : "",
            latestCommentAt:
                latest
                ? String(latest.updatedAt || latest.createdAt || "")
                : "",
            primaryState:
                row.isResolved
                ? "RESOLVED"
                : row.isOutdated
                ? "OUTDATED"
                : "UNRESOLVED"
        };
    }

    function clear() {
        threads = [];
        pullRequest = ({});
        totalThreadCount = 0;
        threadsTruncated = false;
        commentsTruncated = false;
    }

    function parseResponse(text) {
        const parsed = JSON.parse(String(text || "{}"));
        const repository = ((parsed.data || {}).repository) || {};
        const pr = repository.pullRequest;

        if (!pr)
            throw new Error("PULL REQUEST NOT FOUND");

        const connection = pr.reviewThreads || {};
        const source =
            connection.nodes && Array.isArray(connection.nodes)
            ? connection.nodes
            : [];
        const out = [];
        let anyCommentsTruncated = false;

        for (let i = 0; i < source.length; ++i) {
            const thread = normalizeThread(source[i]);
            out.push(thread);

            if (thread.commentsTruncated)
                anyCommentsTruncated = true;
        }

        pullRequest = {
            id: String(pr.id || ""),
            number: Number(pr.number || 0),
            title: String(pr.title || ""),
            url: String(pr.url || ""),
            state: String(pr.state || ""),
            isDraft: Boolean(pr.isDraft),
            headRefOid: String(pr.headRefOid || ""),
            baseRefName: String(pr.baseRefName || "")
        };
        threads = out;
        totalThreadCount = Number(connection.totalCount || 0);
        threadsTruncated =
            Boolean((connection.pageInfo || {}).hasNextPage)
            || totalThreadCount > threads.length;
        commentsTruncated = anyCommentsTruncated;
    }

    function refresh(repository, number) {
        if (busy)
            return false;

        const cleanRepo = normalizeRepository(
            repository || repositorySlug
        );
        const pr = normalizePullRequestNumber(
            number || pullRequestNumber
        );

        clear();
        lastError = "";

        if (!cleanRepo || !pr) {
            lastError = "PR THREADS // REPOSITORY OR PULL REQUEST MISSING";
            status = lastError;
            return false;
        }

        repositorySlug = cleanRepo;
        pullRequestNumber = pr;
        busy = true;
        status = "PR THREADS // READING";
        stdoutSeen = false;
        stderrSeen = false;
        exitSeen = false;
        exitCode = -1;
        stdoutText = "";
        stderrText = "";

        const owner = cleanRepo.split("/")[0];
        const name = cleanRepo.slice(owner.length + 1);

        commandProcess.exec([
            "gh",
            "api",
            "graphql",
            "-F", "owner=" + owner,
            "-F", "name=" + name,
            "-F", "number=" + String(pr),
            "-F", "threadLimit=" + String(Math.max(1, Math.min(100, maxThreads))),
            "-F", "commentLimit=" + String(Math.max(1, Math.min(100, maxCommentsPerThread))),
            "-f",
            "query="
            + "query($owner:String!,$name:String!,$number:Int!,$threadLimit:Int!,$commentLimit:Int!){"
            + "repository(owner:$owner,name:$name){"
            + "pullRequest(number:$number){"
            + "id number title url state isDraft headRefOid baseRefName "
            + "reviewThreads(first:$threadLimit){"
            + "totalCount pageInfo{hasNextPage endCursor} nodes{"
            + "id isResolved isOutdated isCollapsed path line originalLine startLine originalStartLine "
            + "diffSide startDiffSide subjectType viewerCanReply viewerCanResolve viewerCanUnresolve "
            + "resolvedBy{login} "
            + "comments(first:$commentLimit){"
            + "totalCount pageInfo{hasNextPage endCursor} nodes{"
            + "id fullDatabaseId body bodyText resourcePath "
            + "author{login avatarUrl url} authorAssociation state createdAt updatedAt publishedAt "
            + "path line originalLine startLine originalStartLine diffHunk outdated "
            + "commit{oid} originalCommit{oid} "
            + "replyTo{id fullDatabaseId} "
            + "pullRequestReview{id state author{login}}"
            + "}}"
            + "}}"
            + "}}"
            + "}"
        ]);

        watchdog.restart();
        return true;
    }

    function maybeFinish() {
        if (!busy || !stdoutSeen || !stderrSeen || !exitSeen)
            return;

        busy = false;
        watchdog.stop();

        if (exitCode !== 0) {
            lastError =
                String(
                    stderrText
                    || stdoutText
                    || ("PR THREAD QUERY EXIT " + exitCode)
                ).trim();
            status = "PR THREADS // ERROR";
            refreshed();
            return;
        }

        try {
            parseResponse(stdoutText);
            lastError = "";
            status =
                "PR THREADS // READY // "
                + String(unresolvedCount)
                + " UNRESOLVED // "
                + String(threadCount)
                + " TOTAL";
        } catch (error) {
            clear();
            lastError = "PR THREAD RESPONSE PARSE // " + String(error);
            status = "PR THREADS // ERROR";
        }

        refreshed();
    }

    Process {
        id: commandProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.stdoutText = this.text;
                root.stdoutSeen = true;
                root.maybeFinish();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.stderrText = this.text;
                root.stderrSeen = true;
                root.maybeFinish();
            }
        }

        onExited: function(code, exitStatus) {
            root.exitCode = Number(code);
            root.exitSeen = true;
            root.maybeFinish();
        }
    }

    Timer {
        id: watchdog
        interval: 120000
        repeat: false

        onTriggered: {
            root.busy = false;
            root.lastError = "PR THREAD QUERY TIMEOUT";
            root.status = "PR THREADS // ERROR";
            if (commandProcess.running)
                commandProcess.running = false;
            root.refreshed();
        }
    }
}
