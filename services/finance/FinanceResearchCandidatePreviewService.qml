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
    property int generation: 0
    property int submittedGeneration: -1
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
            onStreamFinished: candidateService.responseBuffer = text
        }
        onExited: function(exitCode, exitStatus) {
            Qt.callLater(function() {
                const fresh = candidateService.monitoring
                    && candidateService.submittedGeneration
                       === candidateService.generation;
                const output = candidateService.responseBuffer;
                candidateService.responseBuffer = "";
                candidateService.requestFrame = "";
                if (!fresh) return;
                if (!candidateService.acceptResponse(output, exitCode)) {
                    candidateService.candidatePreview = null;
                    candidateService.state = "failed";
                    candidateService.message =
                        "PREVIEW REFUSED // RECHECK SOURCE SNAPSHOTS";
                }
            });
        }
    }
}
