import QtQuick
import Quickshell
import Quickshell.Io
import "HospitalDoctorSuccessionCapabilityPolicy.js" as CapabilityPolicy

// A lazy, read-only local PX --help probe for the existing RECOVER ROOM view.
// Never runs session-succeed, confirms replacement, creates a Session or
// treats a detected command as authenticated operator authority.
Scope {
    id: root
    property bool enabled: false
    property bool checking: false
    property bool checked: false
    property bool supported: false
    property bool pendingRefresh: false
    property string reason: "PX SUCCESSION SUPPORT // NOT CHECKED"
    property string detail: ""

    function refresh() {
        if (!enabled)
            return false;
        // The previous probe may have started for a different view lifecycle.
        // Discard its response and re-probe rather than promoting stale output.
        checked = false;
        supported = false;
        detail = "";
        if (capabilityProcess.running) {
            pendingRefresh = true;
            reason = "PX SUCCESSION SUPPORT // RECHECK PENDING";
            return false;
        }
        pendingRefresh = false;
        checking = true;
        reason = "PX SUCCESSION SUPPORT // CHECKING";
        capabilityProcess.exec([
            "bash", "-lc",
            'px="$HOME/.local/share/post-apollo-dev-runtime/bin/px"; '
                + '[ -x "$px" ] || px="$HOME/.local/bin/px"; '
                + 'exec "$px" "$@"',
            "hospital-succession-capability",
            "agent", "session-succeed", "--help"
        ]);
        return true;
    }

    onEnabledChanged: {
        if (enabled)
            Qt.callLater(root.refresh);
        else {
            checked = false;
            supported = false;
            checking = false;
            pendingRefresh = false;
            reason = "PX SUCCESSION SUPPORT // NOT CHECKED";
            detail = "";
        }
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
            const result = CapabilityPolicy.evaluate(
                code, capabilityProcess.outputText, capabilityProcess.errorText
            );
            capabilityProcess.outputText = "";
            capabilityProcess.errorText = "";
            if (!root.enabled)
                return;
            if (root.pendingRefresh) {
                root.pendingRefresh = false;
                Qt.callLater(root.refresh);
                return;
            }
            root.supported = result.supported;
            root.reason = result.reason;
            root.detail = result.detail;
            root.checked = true;
            root.checking = false;
        }
    }
}
