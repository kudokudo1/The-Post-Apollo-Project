import QtQuick
import Quickshell
import Quickshell.Io

// M13i // Read-only, DISABLED encrypted recovery provider seam.
// This is not a keyring client or decrypted-draft UI.
// Only an explicit inspectProvider() invocation can run the read-only
// D-Bus NameHasOwner probe; loading the component does NOT start a process.
// No FileView, secret-tool, key, draft content, opt-in, or write path here.
Scope {
    id: bridge

    readonly property bool encryptedRecoveryEnabled: false
    readonly property bool userOptedIn: false
    readonly property bool trustedKeyReleaseVerified: false
    readonly property bool canPersistDraft: false
    readonly property bool canDecryptDraft: false
    readonly property bool canRestoreDraft: false
    readonly property bool canDeleteDraft: false
    readonly property bool canExportDraft: false
    readonly property bool canWriteTaskSource: false
    readonly property bool productionActivation: false

    property string providerStatus: "NOT_CHECKED"
    property bool providerPresent: false
    property bool checking: false
    property string reason: ""
    property bool replySeen: false
    signal observed()

    function inspectProvider() {
        if (checking || probe.running)
            return false;
        checking = true;
        replySeen = false;
        providerStatus = "CHECKING";
        providerPresent = false;
        reason = "";
        probe.exec(["python3", "-B", "-I",
            Quickshell.shellPath("services/hub/TaskRecoveryProviderHostM13i.py"),
            "--probe"]);
        observed();
        return true;
    }

    function acceptHostLine(line) {
        // Never display arbitrary host data. Parse one strict status-only
        // envelope, ignoring any diagnostic or private text.
        if (!checking || replySeen || typeof line !== "string"
                || line.length > 512) {
            providerStatus = "INVALID_HOST_REPLY";
            providerPresent = false;
            reason = "UNEXPECTED_HOST_OUTPUT";
            replySeen = false;
            observed();
            return;
        }
        try {
            var msg = JSON.parse(line);
            var required = [
                "protocol", "kind", "status", "providerPresent",
                "keyringUnlocked", "recoveryEnabled", "writeAuthorized",
                "persistAuthorized", "decryptAuthorized", "productionActivation"
            ];
            if (!msg || typeof msg !== "object" || Array.isArray(msg)
                    || Object.keys(msg).sort().join(",")
                      !== required.slice().sort().join(",")
                    || msg.protocol !== 1
                    || msg.kind !== "M13I_PROVIDER_STATUS"
                    || ["SERVICE_ACQUIRED", "SERVICE_NOT_RUNNING",
                        "PROBE_TOOL_MISSING", "SESSION_BUS_UNAVAILABLE",
                        "UNEXPECTED_RESPONSE"].indexOf(msg.status) < 0
                    || msg.providerPresent !== (msg.status === "SERVICE_ACQUIRED")
                    || msg.keyringUnlocked !== false
                    || msg.recoveryEnabled !== false
                    || msg.writeAuthorized !== false
                    || msg.persistAuthorized !== false
                    || msg.decryptAuthorized !== false
                    || msg.productionActivation !== false)
                throw new Error("UNSAFE_HOST_RESPONSE");
            replySeen = true;
            providerStatus = msg.status;
            providerPresent = msg.providerPresent;
            reason = "";
            observed();
        } catch (e) {
            replySeen = false;
            providerStatus = "INVALID_HOST_REPLY";
            providerPresent = false;
            reason = "UNSAFE_HOST_RESPONSE";
            observed();
        }
    }

    function hostExited(code) {
        if (!checking)
            return;
        if (code !== 0 || !replySeen) {
            providerStatus = "PROBE_UNVERIFIED";
            providerPresent = false;
            reason = "HOST_EXIT_WITHOUT_VALID_RESULT";
        }
        checking = false;
        observed();
    }

    Process {
        id: probe
        stdout: SplitParser {
            splitMarker: "\n"
            onRead: function(line) { bridge.acceptHostLine(line); }
        }
        stderr: StdioCollector {}
        onExited: function(code, exitStatus) { bridge.hostExited(code); }
    }
}
