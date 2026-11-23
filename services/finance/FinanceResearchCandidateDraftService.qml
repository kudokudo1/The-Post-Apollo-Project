import QtQuick
import Quickshell
import Quickshell.Io

// FinanceW Research M9: one-shot, READ-ONLY citation draft preparation.
// No source fetch, account call, store write, or automatic retry.
Scope {
    id: draftService
    property bool monitoring: false
    property string state: "idle"
    property string message: "NO CITATION PREPARED"
    property var preparedDraft: null
    property string frame: ""
    property string output: ""
    property string errorOutput: ""
    property bool stdoutFinished: false
    property bool stderrFinished: false
    property bool processExited: false
    property int exitCode: -1
    property int generation: 0
    property int dispatchedGeneration: -1
    property string expectedKey: ""
    property string expectedCaseId: ""
    property int expectedRevision: -1
    property string expectedUrl: ""
    readonly property bool loading: state === "loading"

    function clear() {
        generation++;
        completionDeadline.stop();
        preparedDraft = null;
        state = "idle";
        message = "NO CITATION PREPARED";
        expectedKey = "";
        expectedCaseId = "";
        expectedRevision = -1;
        expectedUrl = "";
    }
    onMonitoringChanged: clear()

    function prepare(candidate, investigation, revision) {
        if (!monitoring || worker.running || loading
                || !candidate || !investigation
                || typeof candidate.key !== "string"
                || candidate.kind !== "sec-index"
                || candidate.eligibleForDraft !== true
                || candidate.reviewed !== false
                || candidate.authenticatedProvenance !== false
                || !Number.isSafeInteger(revision) || revision < 0)
            return false;
        const text = JSON.stringify({
            action: "prepare-draft",
            candidateKey: candidate.key,
            candidate: candidate,
            investigation: investigation,
            caseRevision: revision
        }) + "\n";
        if (text.length > 190000)
            return false;

        clear();
        expectedKey = candidate.key;
        expectedCaseId = investigation.id;
        expectedRevision = revision;
        expectedUrl = candidate.url;
        dispatchedGeneration = generation;
        output = "";
        errorOutput = "";
        stdoutFinished = false;
        stderrFinished = false;
        processExited = false;
        exitCode = -1;
        frame = text;
        state = "loading";
        message = "PREPARING LOCAL CITATION // UNSAVED";
        worker.exec({
            command: ["/usr/bin/env", "node", Quickshell.shellPath(
                "scripts/finance/research_candidate_draft_preview.mjs")],
            environment: ({
                ACTUAL_PASSWORD_FILE: null, ACTUAL_SYNC_ID: null,
                ACTUAL_SERVER_URL: null, ACTUAL_SYNC_ID_FILE: null
            })
        });
        return true;
    }

    function acceptResult(raw) {
        if (typeof raw !== "string" || raw.length > 5600)
            return false;
        const prefix = "FINANCE_RESEARCH_DRAFT_RESULT ";
        const lines = raw.split(/\r?\n/);
        if (lines.length !== 2 || lines[1] !== ""
                || lines[0].indexOf(prefix) !== 0)
            return false;
        let data;
        try {data=JSON.parse(lines[0].slice(prefix.length));}
        catch(error){return false;}
        if (!data || data.schemaVersion !== 1
                || data.readOnly !== true || data.preparedOnly !== true
                || data.candidateKey !== expectedKey
                || data.investigationId !== expectedCaseId
                || data.caseRevision !== expectedRevision
                || data.notice !==
                    "UNSAVED DRAFT // SEC INDEX ONLY // FILING NOT INSPECTED"
                || !data.fields || typeof data.fields !== "object"
                || Object.keys(data.fields).length !== 5
                || data.fields.source !== "manual"
                || data.fields.reviewed !== false
                || typeof data.fields.title !== "string"
                || data.fields.title.length < 1 || data.fields.title.length > 160
                || typeof data.fields.summary !== "string"
                || data.fields.summary.length < 1 || data.fields.summary.length > 2000
                || typeof data.fields.url !== "string"
                || data.fields.url !== expectedUrl
                || !/^https:\/\/www\.sec\.gov\/Archives\/edgar\/data\//.test(
                    data.fields.url))
            return false;
        preparedDraft = data;
        state = "ready";
        message = "UNSAVED CITATION DRAFT // ATTACH STILL DISABLED";
        return true;
    }

    function refusalCode(raw) {
        const prefix = "FINANCE_RESEARCH_DRAFT_ERROR ";
        const line = String(raw || "").trim();
        if (line.indexOf(prefix) !== 0)
            return "PROCESS_FAILED";
        const code = line.slice(prefix.length);
        const allow = /^(INVALID_FRAME|INVALID_REQUEST|INVALID_CANDIDATE_DRAFT|CANDIDATE_REVIEW_REQUIRED|CANDIDATE_DRAFT_UNAVAILABLE|INVALID_RESULT|RESULT_TOO_LARGE|INVALID_ARGUMENTS|DRAFT_UNAVAILABLE)$/;
        return allow.test(code) ? code : "PROCESS_FAILED";
    }
    function complete(force) {
        if (!processExited)
            return;
        const requiredStreamFinished = exitCode === 0
            ? stdoutFinished : stderrFinished;
        if (!requiredStreamFinished && !force)
            return;
        completionDeadline.stop();
        const fresh = monitoring
            && dispatchedGeneration === generation;
        const ok = requiredStreamFinished && exitCode === 0;
        const raw = output;
        const diagnostic = errorOutput;
        const code = exitCode;
        processExited = false;
        stdoutFinished = false;
        stderrFinished = false;
        output = "";
        errorOutput = "";
        frame = "";
        exitCode = -1;
        if (!fresh)
            return;
        if (ok && acceptResult(raw))
            return;
        preparedDraft = null;
        state = "failed";
        const reason = !requiredStreamFinished ? "STREAM_INCOMPLETE"
            : code !== 0 ? refusalCode(diagnostic) : "INVALID_RESULT_STREAM";
        message = "DRAFT REFUSED // " + reason;
        // Only a fixed code is reported, never source/case text.
        console.warn("FINANCE_RESEARCH_DRAFT_REFUSED // " + reason);
    }

    Timer {
        id: completionDeadline
        interval: 1800
        repeat: false
        onTriggered: draftService.complete(true)
    }

    Process {
        id: worker
        stdinEnabled: true
        onStarted: {
            if (draftService.frame !== "") {
                worker.write(draftService.frame);
                draftService.frame = "";
            }
        }
        stdout: StdioCollector {
            onStreamFinished: {
                draftService.output = text;
                draftService.stdoutFinished = true;
                draftService.complete(false);
            }
        }
        stderr: StdioCollector {
            onStreamFinished: {
                draftService.errorOutput = text;
                draftService.stderrFinished = true;
                draftService.complete(false);
            }
        }
        onExited: function(code, status) {
            draftService.exitCode = code;
            draftService.processExited = true;
            draftService.complete(false);
            if (draftService.processExited)
                completionDeadline.start();
        }
    }
}
