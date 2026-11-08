import QtQuick
import Quickshell
import Quickshell.Io
import "HospitalWorkerAttachmentCapabilityPolicy.js" as CapabilityPolicy

// Operator-click-only mutation against the separately gated PX atomic endpoint.
// No bind, Session update, launch, browser control or automatic retry.
Scope {
    id: root
    property bool running: false
    property string lastError: ""
    property var lastResult: null
    property var pending: ({})
    property bool capabilityChecking: false
    property bool capabilityChecked: false
    property bool capabilityAvailable: false
    property string capabilityReason: "PX ATTACH SUPPORT // NOT CHECKED"
    property string capabilityDetail: ""

    function probeCapability() {
        if (running || process.running || capabilityProcess.running)
            return false;
        capabilityChecked = false;
        capabilityAvailable = false;
        capabilityReason = "PX ATTACH SUPPORT // CHECKING";
        capabilityDetail = "";
        capabilityChecking = true;
        capabilityProcess.exec([
            "bash", "-lc",
            'px="$HOME/.local/share/post-apollo-dev-runtime/bin/px"; '
                + '[ -x "$px" ] || px="$HOME/.local/bin/px"; '
                + 'exec "$px" "$@"',
            "hospital-attach-capability",
            "agent", "session-attach", "--help"
        ]);
        return true;
    }


    signal attached(var result)
    signal refused(string reason)

    function attach(candidate) {
        const v = candidate || {};
        const mode = String(v.mode || "").trim();
        const required = [
            "roomId", "sessionId", "assignmentId", "doctorId",
            "providerId", "repository", "branch", "bedPath"
        ];
        // Never call a missing/old PX version. This client cannot authorize
        // execution; the backend must still revalidate exact identities.
        if (running || process.running || capabilityChecking
                || !capabilityChecked || !capabilityAvailable) {
            lastError = "ATTACH REFUSED // PX ATOMIC ENDPOINT NOT VERIFIED";
            return false;
        }
        if (mode !== "create" && mode !== "reuse") {
            lastError = "ATTACH REFUSED // UNKNOWN MODE";
            return false;
        }
        for (let i = 0; i < required.length; ++i) {
            if (!String(v[required[i]] || "").trim()) {
                lastError = "ATTACH REFUSED // MISSING " + required[i];
                return false;
            }
        }

        pending = {
            roomId: String(v.roomId),
            sessionId: String(v.sessionId),
            assignmentId: String(v.assignmentId),
            doctorId: String(v.doctorId),
            providerId: String(v.providerId),
            repository: String(v.repository),
            branch: String(v.branch),
            bedPath: String(v.bedPath),
            mode: mode
        };
        lastResult = null;
        lastError = "";
        running = true;
        process.exec([
            "bash", "-lc",
            'px="$HOME/.local/share/post-apollo-dev-runtime/bin/px"; '
                + '[ -x "$px" ] || px="$HOME/.local/bin/px"; '
                + 'exec "$px" "$@"',
            "hospital-confirm-attach",
            "agent", "session-attach",
            "--room-id", pending.roomId,
            "--session-id", pending.sessionId,
            "--assignment-id", pending.assignmentId,
            "--doctor-id", pending.doctorId,
            "--provider-id", pending.providerId,
            "--repository", pending.repository,
            "--branch", pending.branch,
            "--working-directory", pending.bedPath,
            "--mode", pending.mode,
            "--confirm", "--json"
        ]);
        return true;
    }

    Process {
        id: capabilityProcess
        property string outputText: ""
        property string errorText: ""
        stdout: StdioCollector {
            onStreamFinished: capabilityProcess.outputText = String(this.text || "")
        }
        stderr: StdioCollector {
            onStreamFinished: capabilityProcess.errorText = String(this.text || "")
        }
        onExited: function(code, exitStatus) {
            const probe = CapabilityPolicy.evaluate(
                code, capabilityProcess.outputText, capabilityProcess.errorText
            );
            capabilityProcess.outputText = "";
            capabilityProcess.errorText = "";
            root.capabilityAvailable = probe.supported;
            root.capabilityChecked = true;
            root.capabilityReason = probe.reason;
            root.capabilityDetail = probe.errorDetail;
            root.capabilityChecking = false;
        }
    }

    Process {
        id: process
        property string outputText: ""
        property string errorText: ""
        stdout: StdioCollector {
            onStreamFinished: process.outputText = String(this.text || "")
        }
        stderr: StdioCollector {
            onStreamFinished: process.errorText = String(this.text || "")
        }
        onExited: function(code, exitStatus) {
            const expected = root.pending || {};
            const output = process.outputText;
            const error = process.errorText;
            process.outputText = "";
            process.errorText = "";
            root.pending = ({});
            root.running = false;
            let reason = "";
            let payload = null;
            if (Number(code) !== 0) {
                reason = "PX ATTACH REFUSED // "
                    + String(error || output || "EXIT " + code)
                        .trim().slice(0, 260);
            } else {
                try {
                    payload = JSON.parse(String(output || "{}"));
                    if (String(payload.roomId || "") !== expected.roomId
                        || String(payload.sessionId || "") !== expected.sessionId
                        || String(payload.assignmentId || "") !== expected.assignmentId
                        || String(payload.doctorId || "") !== expected.doctorId
                        || String(payload.providerId || "") !== expected.providerId
                        || payload.providerLaunched !== false
                        || payload.browserChatConnected !== false
                        || payload.authorityVerified !== false
                        || (payload.mode !== "CREATED" && payload.mode !== "REUSED"))
                        throw new Error("PX RESULT DID NOT MATCH CONFIRMED IDENTITIES");
                } catch (parseError) {
                    reason = "PX ATTACH RESPONSE INVALID // " + String(parseError);
                }
            }
            if (reason) {
                root.lastError = reason;
                root.lastResult = null;
                root.refused(reason);
            } else {
                root.lastError = "";
                root.lastResult = payload;
                root.attached(payload);
            }
        }
    }
}
