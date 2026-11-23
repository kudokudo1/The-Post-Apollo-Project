import QtQuick
import Quickshell
import Quickshell.Io

// Research M7: explicit, read-only transformation of EXISTING feed snapshots.
// No new SEC/crawler service. Results are cleared on source or host changes.
Scope {
    id: candidateService

    property bool monitoring: false
    property var secFeed: null
    property var crawlFeed: null
    property string state: "idle"
    property string message: "CANDIDATES // PRESS BUILD PREVIEW"
    property var candidatePreview: null
    property string requestFrame: ""
    property string responseBuffer: ""
    property string errorBuffer: ""
    readonly property string processErrorPrefix: "FINANCE_RESEARCH_CANDIDATES_ERROR "
    property int generation: 0
    property int submittedGeneration: -1
    property bool stdoutFinished: false
    property bool stderrFinished: false
    property bool processExited: false
    property int processExitCode: -1
    readonly property bool loading: state === "loading"

    function clear() {
        generation += 1;
        candidatePreview = null;
        state = "idle";
        message = monitoring
            ? "SOURCE CHANGED // BUILD A NEW PREVIEW"
            : "RESEARCH CANDIDATES DISCONNECTED";
    }
    onMonitoringChanged: clear()
    onSecFeedChanged: clear()
    onCrawlFeedChanged: clear()

    function refresh() {
        if (!monitoring || worker.running || loading)
            return false;
        const sec = secFeed && secFeed.state === "ready"
            ? secFeed.snapshot : null;
        const crawl = crawlFeed && crawlFeed.state === "ready"
            ? crawlFeed.snapshot : null;
        const cik = sec && secFeed ? secFeed.selectedCik : null;
        const frame = JSON.stringify({
            action: "preview", selectedCik: cik,
            secSnapshot: sec, crawlSnapshot: crawl
        }) + "\n";
        if (frame.length > 120000)
            return false;
        generation += 1;
        submittedGeneration = generation;
        requestFrame = frame;
        responseBuffer = "";
        errorBuffer = "";
        stdoutFinished = false;
        stderrFinished = false;
        processExited = false;
        processExitCode = -1;
        completionDeadline.stop();
        candidatePreview = null;
        state = "loading";
        message = "VALIDATING CURRENT SOURCE SNAPSHOTS // READ ONLY";
        worker.exec({
            command: ["/usr/bin/env", "node",
                Quickshell.shellPath(
                    "scripts/finance/research_candidate_preview_bridge.mjs")],
            environment: ({
                ACTUAL_PASSWORD_FILE: null, ACTUAL_SYNC_ID: null,
                ACTUAL_SERVER_URL: null, ACTUAL_SYNC_ID_FILE: null
            })
        });
        return true;
    }

    function acceptResponse(raw, exitCode) {
        if (exitCode !== 0 || typeof raw !== "string" || raw.length > 66000)
            return false;
        const prefix = "FINANCE_RESEARCH_CANDIDATES_RESULT ";
        const lines = raw.split(/\r?\n/);
        if (lines.length !== 2 || lines[1] !== ""
                || lines[0].indexOf(prefix) !== 0)
            return false;
        let data;
        try { data = JSON.parse(lines[0].slice(prefix.length)); }
        catch (error) { return false; }
        if (!data || data.schemaVersion !== 1 || data.readOnly !== true
                || !Array.isArray(data.candidates)
                || data.candidates.length > 36
                || !data.counts
                || !Number.isSafeInteger(data.counts.sec)
                || !Number.isSafeInteger(data.counts.demo)
                || !Number.isSafeInteger(data.counts.attachablePreview)
                || data.counts.sec < 0 || data.counts.sec > 30
                || data.counts.demo < 0 || data.counts.demo > 6
                || data.counts.attachablePreview !== data.counts.sec
                || data.candidates.length !== data.counts.sec + data.counts.demo
                || typeof data.secPresent !== "boolean"
                || typeof data.demoPresent !== "boolean"
                || typeof data.notice !== "string"
                || data.notice.indexOf("NO AUTOMATIC SOURCE VERIFICATION") < 0)
            return false;
        const keys = {};
        let secCount = 0;
        let demoCount = 0;
        for (let i = 0; i < data.candidates.length; i++) {
            const item = data.candidates[i];
            if (!item || typeof item.key !== "string"
                    || keys[item.key]
                    || typeof item.title !== "string"
                    || item.title.length > 160
                    || typeof item.summary !== "string"
                    || item.summary.length > 2000
                    || typeof item.url !== "string"
                    || item.url.length > 1000
                    || typeof item.notice !== "string"
                    || typeof item.sourceLabel !== "string"
                    || typeof item.observedAt !== "string"
                    || item.reviewed !== false
                    || item.authenticatedProvenance !== false)
                return false;
            keys[item.key] = true;
            if (item.kind === "sec-index"
                    && item.eligibleForDraft === true
                    && item.key.indexOf("sec:") === 0
                    && /^https:\/\/www\.sec\.gov\/Archives\/edgar\/data\//.test(item.url))
                secCount++;
            else if (item.kind === "demo-crawl"
                    && item.eligibleForDraft === false
                    && item.key.indexOf("demo:") === 0
                    && /^https:\/\/quotes\.toscrape\.com\//.test(item.url))
                demoCount++;
            else
                return false;
        }
        if (secCount !== data.counts.sec || demoCount !== data.counts.demo
                || (!data.secPresent && secCount > 0)
                || (!data.demoPresent && demoCount > 0))
            return false;
        candidatePreview = data;
        state = "ready";
        message = secCount + " SEC INDEX CANDIDATES // "
            + demoCount + " DEMO ONLY // NOTHING SAVED";
        return true;
    }

    // Only the bridge's fixed, allowlisted codes may reach UI/logs.
    // Never surface raw stderr, URLs, titles, SEC contact, or snapshots.
    function refusalCode(exitCode, response, diagnostic) {
        if (exitCode !== 0) {
            const allowed = /^(INVALID_FRAME|INVALID_REQUEST|INVALID_SOURCE_SNAPSHOT|INVALID_ISSUER_SELECTION|INVALID_SEC_SNAPSHOT|INVALID_SEC_FILING|INVALID_SEC_URL|INVALID_DEMO_SNAPSHOT|INVALID_DEMO_PAGE|INVALID_DEMO_COUNT|INVALID_RESULT|RESULT_TOO_LARGE|PREVIEW_UNAVAILABLE|INVALID_ARGUMENTS)$/;
            const raw = String(diagnostic || "").trim();
            if (raw.indexOf(processErrorPrefix) === 0) {
                const code = raw.slice(processErrorPrefix.length);
                if (allowed.test(code))
                    return code;
            }
            return "PROCESS_FAILED";
        }
        if (!response || response.length === 0)
            return "EMPTY_RESULT_STREAM";
        return "INVALID_RESULT_STREAM";
    }

    // Process exit and StdioCollector completion are separate events.
    // Do not assume stdout has flushed at onExited (especially for 30 rows).
    // No automatic retry, provider call, or persistent storage action.
    function completeAttempt(force) {
        if (!processExited)
            return;
        // A successful bridge may have no stderr; a refused bridge may
        // have no stdout. Await only the output stream relevant to its code.
        const requiredStreamFinished = processExitCode === 0
            ? stdoutFinished : stderrFinished;
        if (!force && !requiredStreamFinished)
            return;
        completionDeadline.stop();

        const fresh = monitoring && submittedGeneration === generation;
        const output = responseBuffer;
        const diagnostic = errorBuffer;
        const code = processExitCode;
        const streamIncomplete = !requiredStreamFinished;

        responseBuffer = "";
        errorBuffer = "";
        requestFrame = "";
        processExited = false;
        stdoutFinished = false;
        stderrFinished = false;
        processExitCode = -1;
        if (!fresh)
            return;

        if (streamIncomplete || !acceptResponse(output, code)) {
            const reason = streamIncomplete ? "STREAM_INCOMPLETE"
                                           : refusalCode(code, output, diagnostic);
            candidatePreview = null;
            state = "failed";
            message = "PREVIEW REFUSED // " + reason;
            // Log only a fixed rejection code. Never log raw source data.
            console.warn("FINANCE_RESEARCH_PREVIEW_REFUSED // " + reason);
        }
    }

    Timer {
        id: completionDeadline
        interval: 1800
        repeat: false
        onTriggered: candidateService.completeAttempt(true)
    }

    Process {
        id: worker
        stdinEnabled: true
        onStarted: {
            // Supply the original frame even if the panel was closed mid-start.
            // Generation checks below discard any obsolete response.
            if (candidateService.requestFrame !== "") {
                worker.write(candidateService.requestFrame);
                candidateService.requestFrame = "";
            }
        }
        stdout: StdioCollector {
            onStreamFinished: {
                candidateService.responseBuffer = text;
                candidateService.stdoutFinished = true;
                candidateService.completeAttempt(false);
            }
        }
        stderr: StdioCollector {
            onStreamFinished: {
                candidateService.errorBuffer = text;
                candidateService.stderrFinished = true;
                candidateService.completeAttempt(false);
            }
        }
        onExited: function(exitCode, exitStatus) {
            candidateService.processExitCode = exitCode;
            candidateService.processExited = true;
            candidateService.completeAttempt(false);
            if (candidateService.processExited)
                completionDeadline.start();
        }
    }
}
