import QtQuick
import Quickshell
import Quickshell.Io

// Research M9b: validates a proposed citation against M1/M6 and returns
// a revised VOLATILE case JSON value. Never opens or writes research storage.
Scope {
    id: appendService
    property bool monitoring: false
    property string state: "idle"
    property string message: "NO SCRATCH CITATION ADDED"
    property var result: null
    property string frame: ""
    property string output: ""
    property string errorOutput: ""
    property bool stdoutFinished: false
    property bool stderrFinished: false
    property bool processExited: false
    property int exitCode: -1
    property int generation: 0
    property int submittedGeneration: -1
    property string expectedKey: ""
    property string expectedId: ""
    property string expectedUrl: ""
    property string expectedTitle: ""
    property string expectedSummary: ""
    property var expectedCase: null
    property int expectedCount: -1
    readonly property bool loading: state === "loading"

    function clear() {
        generation++;
        deadline.stop();
        result = null;
        state = "idle";
        message = "NO SCRATCH CITATION ADDED";
        expectedKey = "";
        expectedId = "";
        expectedUrl = "";
        expectedTitle = "";
        expectedSummary = "";
        expectedCase = null;
        expectedCount = -1;
    }
    onMonitoringChanged: clear()

    function append(candidate, prepared, scratchCase, fields) {
        if (!monitoring || worker.running || loading
                || !candidate || candidate.kind !== "sec-index"
                || candidate.eligibleForDraft !== true
                || candidate.reviewed !== false
                || candidate.authenticatedProvenance !== false
                || !prepared || prepared.readOnly !== true
                || prepared.preparedOnly !== true
                || prepared.caseRevision !== 0
                || prepared.candidateKey !== candidate.key
                || !scratchCase || typeof scratchCase.id !== "string"
                || !scratchCase.id.startsWith("scratch_")
                || !Array.isArray(scratchCase.evidence)
                || scratchCase.evidence.length >= 40
                || !fields || typeof fields.title !== "string"
                || typeof fields.summary !== "string"
                || typeof fields.url !== "string"
                || fields.url !== candidate.url
                || scratchCase.evidence.some(x => x.url === fields.url))
            return false;
        const req = JSON.stringify({
            action: "append-to-memory",
            scratchCase: scratchCase, candidate: candidate,
            prepared: prepared,
            edits: {
                title: fields.title,
                summary: fields.summary,
                url: fields.url
            },
            revision: 0
        }) + "\n";
        if (req.length > 210000)
            return false;
        clear();
        expectedId = scratchCase.id;
        expectedKey = candidate.key;
        expectedUrl = fields.url;
        expectedTitle = fields.title;
        expectedSummary = fields.summary;
        expectedCase = JSON.parse(JSON.stringify(scratchCase));
        expectedCount = scratchCase.evidence.length;
        submittedGeneration = generation;
        stdoutFinished = false;
        stderrFinished = false;
        processExited = false;
        exitCode = -1;
        output = "";
        errorOutput = "";
        frame = req;
        state = "loading";
        message = "VALIDATING CITATION // MEMORY ONLY";
        worker.exec({
            command: ["/usr/bin/env", "node", Quickshell.shellPath(
                "scripts/finance/research_scratch_citation_preview.mjs")],
            environment: ({
                ACTUAL_PASSWORD_FILE: null, ACTUAL_SYNC_ID: null,
                ACTUAL_SERVER_URL: null, ACTUAL_SYNC_ID_FILE: null
            })
        });
        return true;
    }

    function accept(raw) {
        if (typeof raw !== "string" || raw.length > 210000)
            return false;
        const prefix = "FINANCE_RESEARCH_SCRATCH_RESULT ";
        const lines = raw.split(/\r?\n/);
        if (lines.length !== 2 || lines[1] !== ""
                || lines[0].indexOf(prefix) !== 0)
            return false;
        let data;
        try {data=JSON.parse(lines[0].slice(prefix.length));}
        catch (e) {return false;}
        const item=data && data.scratchCase;
        const before=expectedCase;
        if (!before || !item || typeof item !== "object"
                || data.schemaVersion !== 1
                || data.memoryOnly !== true
                || data.persisted !== false
                || data.caseRevision !== 0
                || data.candidateKey !== expectedKey
                || data.previousCount !== expectedCount
                || typeof data.addedId !== "string"
                || !/^scratch_e_[0-9a-f-]{36}$/.test(data.addedId)
                || item.id !== expectedId
                || item.title !== before.title
                || item.question !== before.question
                || item.createdAt !== before.createdAt
                || item.schemaVersion !== 1
                || !Array.isArray(item.evidence)
                || item.evidence.length !== expectedCount + 1
                || JSON.stringify(item.evidence.slice(0, expectedCount))
                    !== JSON.stringify(before.evidence))
            return false;
        const evidence=item.evidence[expectedCount];
        if (!evidence || evidence.id !== data.addedId
                || evidence.source !== "manual"
                || evidence.reviewed !== false
                || evidence.url !== expectedUrl
                || evidence.title !== expectedTitle
                || evidence.summary !== expectedSummary
                || typeof evidence.observedAt !== "string"
                || !/^\d{4}-\d{2}-\d{2}T/.test(evidence.observedAt))
            return false;
        result = data;
        state = "ready";
        message = "SCRATCH CITATION ADDED // NOT SAVED";
        return true;
    }

    function refusal(raw) {
        const prefix = "FINANCE_RESEARCH_SCRATCH_ERROR ";
        const msg = String(raw || "").trim();
        if (msg.indexOf(prefix) !== 0)
            return "PROCESS_FAILED";
        const code = msg.slice(prefix.length);
        const allow = /^(INVALID_FRAME|INVALID_REQUEST|INVALID_CANDIDATE_DRAFT|CANDIDATE_REVIEW_REQUIRED|INVALID_CANDIDATE|CANDIDATE_MISMATCH|INVALID_SCRATCH_EVIDENCE|SCRATCH_LIMIT_OR_REVISION|INVALID_RESULT|RESULT_TOO_LARGE|INVALID_ARGUMENTS|SCRATCH_UNAVAILABLE)$/;
        return allow.test(code) ? code : "PROCESS_FAILED";
    }

    function complete(force) {
        if (!processExited)
            return;
        const streamReady = exitCode === 0 ? stdoutFinished : stderrFinished;
        if (!force && !streamReady) return;
        deadline.stop();
        const fresh = monitoring && submittedGeneration === generation;
        const code = exitCode;
        const response = output;
        const diagnostic = errorOutput;
        const missing = !streamReady;
        processExited = false;
        stdoutFinished = false;
        stderrFinished = false;
        exitCode = -1;
        output = "";
        errorOutput = "";
        frame = "";
        if (!fresh) return;
        if (code === 0 && !missing && accept(response)) return;
        result = null;
        state = "failed";
        const reason = missing ? "STREAM_INCOMPLETE"
            : code !== 0 ? refusal(diagnostic) : "INVALID_RESULT_STREAM";
        message = "SCRATCH APPEND REFUSED // " + reason;
        // Fixed diagnostics only. No source URL, text, or local-case data.
        console.warn("FINANCE_RESEARCH_SCRATCH_REFUSED // " + reason);
    }

    Timer {
        id: deadline
        interval: 1800
        repeat: false
        onTriggered: appendService.complete(true)
    }
    Process {
        id: worker
        stdinEnabled: true
        onStarted: {
            if (appendService.frame !== "") {
                worker.write(appendService.frame);
                appendService.frame = "";
            }
        }
        stdout: StdioCollector {
            onStreamFinished: {
                appendService.output = text;
                appendService.stdoutFinished = true;
                appendService.complete(false);
            }
        }
        stderr: StdioCollector {
            onStreamFinished: {
                appendService.errorOutput = text;
                appendService.stderrFinished = true;
                appendService.complete(false);
            }
        }
        onExited: function(code, status) {
            appendService.exitCode = code;
            appendService.processExited = true;
            appendService.complete(false);
            if (appendService.processExited)
                deadline.start();
        }
    }
}
