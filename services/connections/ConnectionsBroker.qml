pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import "ConnectionsBrokerPolicy.js" as BrokerPolicy

// C2a: one discoverable host capability *probe*, no credentials or grants.
// Key storage, user consent, trusted caller identity and provider operations
// are CLOSED until the later reviewed broker is implemented.
Scope {
    id: broker

    property bool checking: false
    property string status: "NOT CHECKED"
    property string label: "CREDENTIAL SERVICE NOT CHECKED"
    property double lastCheckedMs: 0
    readonly property bool available: status === "SERVICE_ACQUIRED"
    readonly property bool credentialActionsEnabled: false

    property string responseBuffer: ""

    function requirement(providerId) {
        return BrokerPolicy.requirement(providerId);
    }

    function authorize(request) {
        // Even if Secret Service is running, this refuses all operations.
        return BrokerPolicy.decision(request);
    }

    function checkAvailability() {
        if (checking || probeProcess.running)
            return false;
        responseBuffer = "";
        checking = true;
        status = "CHECKING";
        label = "CHECKING LOCAL SECRET SERVICE";
        probeProcess.running = true;
        return true;
    }

    function complete(raw, exitCode) {
        var result = null;
        if (exitCode === 0) {
            try { result = JSON.parse(String(raw || "")); }
            catch (error) { result = null; }
        }
        var mapped = BrokerPolicy.normalizedProbe(result);
        status = mapped.status;
        label = mapped.label;
        lastCheckedMs = Date.now();
        checking = false;
        responseBuffer = "";
    }

    Process {
        id: probeProcess
        running: false
        command: ["python3", "-B",
                  Quickshell.shellPath(
                      "services/connections/ConnectionsSecretServiceProbe.py")]
        stdout: StdioCollector {
            onStreamFinished: broker.responseBuffer = String(text || "")
        }
        onExited: function(exitCode, exitStatus) {
            broker.complete(broker.responseBuffer, exitCode);
        }
    }
}
