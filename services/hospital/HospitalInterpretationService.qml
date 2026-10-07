import QtQuick
import Quickshell.Io

Scope {
    id: root

    required property var registryService
    required property var contextService

    property bool enabled: false
    property bool busy: false
    property string interpreterId: "hermes"
    property real minimumConfidence: 0.68
    property string lastStatus: "AI // OFF"
    property string lastError: ""
    property var pendingSuggestion: null
    property string pendingOperatorText: ""

    property bool exitSeen: false
    property bool stdoutSeen: false
    property bool stderrSeen: false
    property int exitCode: -1
    property string stdoutText: ""
    property string stderrText: ""
    property bool cancelled: false

    signal suggestionReady(var suggestion)
    signal suggestionAccepted(var suggestion)
    signal suggestionDismissed()
    signal interpretationFinished(bool success, string detail)

    readonly property bool hasSuggestion:
        pendingSuggestion !== null

    readonly property var interpreter:
        registryService
        ? registryService.specialistById(interpreterId)
        : null

    readonly property bool interpreterReady:
        interpreter
        && !!interpreter.callable
        && String(interpreter.presence || "").toUpperCase() === "READY"
        && String(
            interpreter.endpoint
            || interpreter.command
            || ""
        ).trim().length > 0

    readonly property string suggestionLabel: {
        const suggestion = pendingSuggestion || {};

        if (!hasSuggestion)
            return "";

        const intent =
            String(suggestion.intent || "").toUpperCase();

        if (intent === "ROUTE")
            return "ROUTE // "
                + String(suggestion.target || "").toUpperCase();

        if (intent === "HANDOFF")
            return "HANDOFF // "
                + String(suggestion.mode || "").toUpperCase()
                + " // "
                + String(
                    suggestion.specialistName
                    || suggestion.specialistId
                    || "SPECIALIST"
                ).toUpperCase();

        return "NO SAFE SUGGESTION";
    }

    function setEnabled(value) {
        const desired = Boolean(value);

        if (!desired) {
            enabled = false;
            dismissSuggestion();

            if (busy)
                cancel();

            lastError = "";
            lastStatus = "AI // OFF";
            return true;
        }

        if (!interpreterReady) {
            enabled = false;
            lastError =
                "AI INTERPRETATION UNAVAILABLE // HERMES IS NOT READY";
            lastStatus = "AI // UNAVAILABLE";
            return false;
        }

        enabled = true;
        lastError = "";
        lastStatus = "AI // SUGGESTION ONLY";
        return true;
    }

    function buildPrompt(operatorText) {
        const text = String(operatorText || "").trim();
        const contextLabel =
            contextService && contextService.active
            ? String(contextService.label || "ACTIVE")
            : "NONE";

        return [
            "You are a strict intent classifier for the Post-Apollo Hospital UI.",
            "Do not use tools. Do not inspect files, git, the network, or the machine.",
            "You have zero authority to execute actions.",
            "Return exactly one compact JSON object and nothing else.",
            "",
            "Allowed outputs:",
            '{"intent":"route","target":"archive|reports|rounds|staff|phone|intercom|surgery","confidence":0.0,"reason":"short"}',
            '{"intent":"handoff","mode":"phone|intercom","specialistId":"codex|hermes","confidence":0.0,"reason":"short"}',
            '{"intent":"none","confidence":0.0,"reason":"short"}',
            "",
            "Rules:",
            "- Use route only when the operator is clearly asking to open or move to a Hospital surface.",
            "- Use handoff only when the operator clearly asks to contact Codex or Hermes.",
            "- Never invent a specialist.",
            "- If uncertain, return intent none.",
            "- Confidence must be between 0 and 1.",
            "",
            "CURRENT LIVE CONTEXT: " + contextLabel,
            "OPERATOR: " + text
        ].join("\n");
    }

    function interpret(textValue) {
        const text = String(textValue || "").trim();

        if (!enabled) {
            lastError = "AI INTERPRETATION IS OFF";
            interpretationFinished(false, lastError);
            return false;
        }

        if (busy) {
            lastError = "AI INTERPRETATION BUSY";
            interpretationFinished(false, lastError);
            return false;
        }

        if (!interpreterReady) {
            lastError =
                "AI INTERPRETATION UNAVAILABLE // HERMES IS NOT READY";
            lastStatus = "AI // UNAVAILABLE";
            interpretationFinished(false, lastError);
            return false;
        }

        const specialist = interpreter || {};
        const command =
            String(
                specialist.endpoint
                || specialist.command
                || ""
            ).trim();

        if (!command) {
            lastError =
                "AI INTERPRETATION UNAVAILABLE // NO HERMES COMMAND";
            interpretationFinished(false, lastError);
            return false;
        }

        dismissSuggestion();

        pendingOperatorText = text;
        busy = true;
        cancelled = false;
        lastError = "";
        lastStatus = "AI // INTERPRETING";

        exitSeen = false;
        stdoutSeen = false;
        stderrSeen = false;
        exitCode = -1;
        stdoutText = "";
        stderrText = "";

        interpreterProcess.exec([
            command,
            "chat",
            "--oneshot",
            "--safe-mode",
            "--quiet",
            "--source",
            "tool",
            "--max-turns",
            "1",
            "-q",
            buildPrompt(text)
        ]);
        interpreterWatchdog.restart();
        return true;
    }

    function cancel() {
        if (!busy)
            return false;

        cancelled = true;
        interpreterWatchdog.stop();

        if (interpreterProcess.running)
            interpreterProcess.running = false;

        busy = false;
        lastStatus = enabled
            ? "AI // SUGGESTION ONLY"
            : "AI // OFF";
        return true;
    }

    function extractJson(textValue) {
        const raw = String(textValue || "").trim();
        const start = raw.indexOf("{");
        const end = raw.lastIndexOf("}");

        if (start < 0 || end <= start)
            return null;

        try {
            return JSON.parse(raw.slice(start, end + 1));
        } catch (error) {
            return null;
        }
    }

    function normalizedSuggestion(value) {
        const row = value || {};
        const intent =
            String(row.intent || "").trim().toLowerCase();
        const confidenceRaw = Number(row.confidence);
        const confidence =
            Number.isFinite(confidenceRaw)
            ? Math.max(0, Math.min(1, confidenceRaw))
            : 0;
        const reason =
            String(row.reason || "").trim().slice(0, 180);

        if (confidence < minimumConfidence) {
            return {
                valid: false,
                detail:
                    "AI // LOW CONFIDENCE // "
                    + String(Math.round(confidence * 100))
                    + "%"
            };
        }

        if (intent === "route") {
            const target =
                String(row.target || "").trim().toLowerCase();
            const allowed = [
                "archive",
                "reports",
                "rounds",
                "staff",
                "phone",
                "intercom",
                "surgery"
            ];

            if (allowed.indexOf(target) < 0) {
                return {
                    valid: false,
                    detail: "AI // REFUSED UNKNOWN ROUTE"
                };
            }

            return {
                valid: true,
                suggestion: {
                    intent: "route",
                    target: target,
                    confidence: confidence,
                    reason: reason,
                    operatorText: pendingOperatorText
                }
            };
        }

        if (intent === "handoff") {
            const mode =
                String(row.mode || "").trim().toLowerCase();
            const specialistId =
                String(row.specialistId || "").trim().toLowerCase();

            if (mode !== "phone" && mode !== "intercom") {
                return {
                    valid: false,
                    detail: "AI // REFUSED UNKNOWN HANDOFF MODE"
                };
            }

            const specialist =
                registryService.specialistById(specialistId);

            if (!specialist) {
                return {
                    valid: false,
                    detail: "AI // REFUSED UNKNOWN SPECIALIST"
                };
            }

            return {
                valid: true,
                suggestion: {
                    intent: "handoff",
                    mode: mode,
                    specialistId: specialistId,
                    specialistName:
                        String(
                            specialist.name
                            || specialist.id
                            || specialistId
                        ),
                    confidence: confidence,
                    reason: reason,
                    operatorText: pendingOperatorText
                }
            };
        }

        return {
            valid: false,
            detail: "AI // NO SAFE SUGGESTION"
        };
    }

    function maybeFinish() {
        if (!busy || !exitSeen || !stdoutSeen || !stderrSeen)
            return;

        busy = false;
        interpreterWatchdog.stop();

        if (cancelled) {
            cancelled = false;
            return;
        }

        if (exitCode !== 0) {
            lastError =
                String(
                    stderrText
                    || stdoutText
                    || ("HERMES EXIT " + String(exitCode))
                ).trim();
            lastStatus = "AI // FAILED";
            interpretationFinished(
                false,
                "AI // FAILED // " + lastError
            );
            return;
        }

        const parsed = extractJson(stdoutText);
        const normalized =
            normalizedSuggestion(parsed);

        if (!normalized.valid) {
            lastError = "";
            lastStatus = String(
                normalized.detail
                || "AI // NO SAFE SUGGESTION"
            );
            interpretationFinished(false, lastStatus);
            return;
        }

        pendingSuggestion =
            normalized.suggestion || null;
        lastError = "";
        lastStatus =
            "AI // REVIEW REQUIRED";
        suggestionReady(pendingSuggestion);
        interpretationFinished(
            true,
            "AI SUGGESTION // "
            + suggestionLabel
        );
    }

    function acceptSuggestion() {
        if (!pendingSuggestion)
            return false;

        const suggestion = pendingSuggestion;
        pendingSuggestion = null;
        lastStatus = enabled
            ? "AI // SUGGESTION ONLY"
            : "AI // OFF";
        suggestionAccepted(suggestion);
        return true;
    }

    function dismissSuggestion() {
        if (!pendingSuggestion)
            return false;

        pendingSuggestion = null;
        lastStatus = enabled
            ? "AI // SUGGESTION ONLY"
            : "AI // OFF";
        suggestionDismissed();
        return true;
    }

    Process {
        id: interpreterProcess

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
        id: interpreterWatchdog

        interval: 30000
        repeat: false

        onTriggered: {
            if (!root.busy)
                return;

            root.cancelled = true;
            root.busy = false;
            root.lastError = "AI INTERPRETATION TIMEOUT";
            root.lastStatus = "AI // TIMEOUT";

            if (interpreterProcess.running)
                interpreterProcess.running = false;

            root.interpretationFinished(
                false,
                root.lastError
            );
        }
    }
}
