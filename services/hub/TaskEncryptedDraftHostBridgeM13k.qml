import QtQuick
import Quickshell
import Quickshell.Io

// M13k // Synthetic draft host IPC boundary, NEVER active for real TASKS.
// Only a separate private test bus + private HOME may call the host.
// All production/decrypt/restore permissions remain literally false.
// Component creation performs no keyring, filesystem or process operation.
Scope {
    id: bridge

    readonly property bool encryptedRecoveryEnabled: false
    readonly property bool userOptedIn: false
    readonly property bool canPersistUserDraft: false
    readonly property bool canDecryptUserDraft: false
    readonly property bool canRestoreUserDraft: false
    readonly property bool canWriteTaskSource: false
    readonly property bool productionActivation: false
    readonly property bool syntheticCIEligible:
        String(Quickshell.env("POST_APOLLO_M13K_ISOLATED") || "") === "1"
        && String(Quickshell.env("POST_APOLLO_M13G_DISPOSABLE") || "") === "1"

    property bool busy: false
    property bool pendingSend: false
    property bool replySeen: false
    property string status: "DISABLED_NOT_STARTED"
    property bool syntheticVerified: false
    signal observed()

    function startSynthetic() {
        if (!syntheticCIEligible || busy || host.running) {
            status = "REFUSED_NOT_PRIVATE_TEST";
            syntheticVerified = false;
            observed();
            return false;
        }
        busy = true;
        pendingSend = true;
        replySeen = false;
        syntheticVerified = false;
        status = "STARTING_PRIVATE_SYNTHETIC_TEST";
        host.exec(["node",
            Quickshell.shellPath("tests/tasks/fixtures/TaskEncryptedDraftHostM13k.cjs"),
            "--single-request"]);
        observed();
        return true;
    }

    function acceptLine(line) {
        if (!busy || replySeen || typeof line !== "string" || line.length > 512) {
            status = "REFUSED_HOST_OUTPUT";
            syntheticVerified = false;
            replySeen = false;
            observed();
            return;
        }
        try {
            var msg = JSON.parse(line);
            var expected = ["protocol", "kind", "status",
                "syntheticRoundTripVerified", "productionActivation",
                "sourceTrusted", "persistAuthorized", "writeAuthorized",
                "restoreAuthorized", "replayAuthorized", "deleteAuthorized",
                "keyReleaseAuthorized"];
            if (!msg || typeof msg !== "object" || Array.isArray(msg)
                    || Object.keys(msg).sort().join(",")
                       !== expected.slice().sort().join(",")
                    || msg.protocol !== 1 || msg.kind !== "M13K_SYNTHETIC_HOST"
                    || typeof msg.status !== "string" || msg.status.length > 72
                    || msg.syntheticRoundTripVerified !==
                      (msg.status === "M13K_SYNTHETIC_ENCRYPTED_RESTART_PASS")
                    || msg.productionActivation !== false
                    || msg.sourceTrusted !== false
                    || msg.persistAuthorized !== false
                    || msg.writeAuthorized !== false
                    || msg.restoreAuthorized !== false
                    || msg.replayAuthorized !== false
                    || msg.deleteAuthorized !== false
                    || msg.keyReleaseAuthorized !== false)
                throw new Error("UNSAFE_RESPONSE");
            replySeen = true;
            status = msg.status;
            syntheticVerified = msg.syntheticRoundTripVerified;
        } catch (e) {
            replySeen = false;
            status = "REFUSED_HOST_RESPONSE";
            syntheticVerified = false;
        }
        observed();
    }

    function afterExit(code) {
        if (!busy) return;
        busy = false;
        pendingSend = false;
        if (code !== 0 || !replySeen) {
            status = "REFUSED_HOST_EXIT_UNVERIFIED";
            syntheticVerified = false;
        }
        observed();
    }

    Process {
        id: host
        stdinEnabled: true
        stdout: SplitParser {
            splitMarker: "\n"
            onRead: function(line) { bridge.acceptLine(line); }
        }
        stderr: StdioCollector {}
        onRunningChanged: {
            if (running && bridge.pendingSend) {
                bridge.pendingSend = false;
                host.write(JSON.stringify({
                    protocol:1, kind:"RUN_SYNTHETIC_DRAFT", consent:"CI_ONLY"
                }) + "\n");
            }
        }
        onExited: function(code, exitStatus) { bridge.afterExit(code); }
    }
}
