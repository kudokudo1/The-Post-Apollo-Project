import QtQuick
import Quickshell
import "./services/hub"

// M13l // Standalone, windowless, NON-PRODUCTION native acceptance scene.
// Runs ONLY the fixed M13k synthetic host request against a private keyring.
// Never import or instantiate ApolloHubTodoStore; no actual TASKS data.
Scope {
    id: harness
    property bool started: false
    property bool finished: false

    function finish(status) {
        if (finished) return;
        finished = true;
        // Print only constant markers. No secret, path or draft material.
        if (status === "M13L_NATIVE_QML_IPC_PASS")
            console.warn("M13L_NATIVE_QML_IPC_PASS");
        else
            console.warn("M13L_NATIVE_QML_IPC_REFUSED");
        Qt.quit();
    }

    TaskEncryptedDraftHostBridgeM13k {
        id: bridge
        onObserved: {
            if (!harness.started || harness.finished)
                return;
            if (bridge.busy) {
                if (bridge.replySeen)
                    console.warn("M13L_PHASE_REPLY_PARSED");
                else
                    console.warn("M13L_PHASE_BRIDGE_BUSY");
                return;
            }
            console.warn("M13L_PHASE_BRIDGE_SETTLED");
            if (bridge.status === "REFUSED_HOST_EXIT_UNVERIFIED")
                console.warn("M13L_PHASE_HOST_EXIT_UNVERIFIED");
            else if (bridge.status === "REFUSED_HOST_RESPONSE")
                console.warn("M13L_PHASE_HOST_RESPONSE_INVALID");
            else if (bridge.status === "REFUSED_NOT_PRIVATE_TEST")
                console.warn("M13L_PHASE_PRIVATE_GATE_REFUSED");
            else if (bridge.status === "REFUSED_REQUEST_TIMEOUT")
                console.warn("M13L_PHASE_HOST_REQUEST_TIMEOUT");
            else if (bridge.status === "REFUSED_REQUEST_SHAPE")
                console.warn("M13L_PHASE_HOST_REQUEST_INVALID");
            else if (bridge.status === "REFUSED_NOT_DISPOSABLE_SESSION")
                console.warn("M13L_PHASE_HOST_PRIVATE_SESSION_REFUSED");
            else if (bridge.status === "REFUSED_SYNTHETIC_ENCRYPT")
                console.warn("M13L_PHASE_HOST_ENCRYPT_REFUSED");
            else if (bridge.status === "REFUSED_SYNTHETIC_REOPEN")
                console.warn("M13L_PHASE_HOST_REOPEN_REFUSED");
            else if (bridge.status === "REFUSED_SYNTHETIC_MISSING_KEY")
                console.warn("M13L_PHASE_HOST_MISSING_KEY_GATE_REFUSED");
            else if (bridge.status === "REFUSED_SYNTHETIC_CLEANUP_UNVERIFIED")
                console.warn("M13L_PHASE_HOST_CLEANUP_UNVERIFIED");
            if (bridge.status === "M13K_SYNTHETIC_ENCRYPTED_RESTART_PASS"
                    && bridge.syntheticVerified
                    && !bridge.canWriteTaskSource
                    && !bridge.canPersistUserDraft
                    && !bridge.productionActivation)
                harness.finish("M13L_NATIVE_QML_IPC_PASS");
            else if (bridge.status.indexOf("REFUSED_") === 0)
                harness.finish("M13L_NATIVE_QML_IPC_REFUSED");
        }
    }

    Timer {
        interval: 45000
        repeat: false
        running: true
        onTriggered: {
            console.warn("M13L_PHASE_QML_TIMER_EXPIRED");
            harness.finish("M13L_NATIVE_QML_IPC_REFUSED");
        }
    }

    // The earlier Qt.callLater startup did not produce observable start
    // evidence on Fedora, while the watchdog Timer demonstrably fired.
    // A separate, single-shot 100ms Timer is an explicit event-loop dispatch
    // with no automatic keyring access outside M13k's private-session gate.
    Timer {
        interval: 100
        running: true
        repeat: false
        onTriggered: {
            console.warn("M13L_PHASE_BOOT_TIMER_FIRED");
            if (harness.finished) return;
            harness.started = true;
            console.warn("M13L_PHASE_START_ATTEMPT");
            if (!bridge.syntheticCIEligible) {
                console.warn("M13L_PHASE_ENV_GATE_DENIED");
                harness.finish("M13L_NATIVE_QML_IPC_REFUSED");
            } else {
                console.warn("M13L_PHASE_PRIVATE_GATE_READY");
                if (!bridge.startSynthetic()) {
                    console.warn("M13L_PHASE_PROCESS_START_REJECTED");
                    harness.finish("M13L_NATIVE_QML_IPC_REFUSED");
                } else {
                    console.warn("M13L_PHASE_PROCESS_START_ACCEPTED");
                }
            }
        }
    }

    // Five-second bounded status: helps separate a process that never
    // started/sent stdin from one waiting for keyring or a response.
    Timer {
        interval: 5000
        running: true
        repeat: false
        onTriggered: {
            if (harness.finished) return;
            if (!harness.started)
                console.warn("M13L_PHASE_T5_BOOT_NOT_DISPATCHED");
            else if (bridge.busy && bridge.pendingSend)
                console.warn("M13L_PHASE_T5_STDIN_NOT_SENT");
            else if (bridge.busy && bridge.replySeen)
                console.warn("M13L_PHASE_T5_REPLY_WAITING_EXIT");
            else if (bridge.busy)
                console.warn("M13L_PHASE_T5_AWAITING_REPLY");
            else
                console.warn("M13L_PHASE_T5_SETTLED_NO_RESULT");
        }
    }

    Component.onCompleted:
        console.warn("M13L_PHASE_QML_COMPONENT_LOADED")
}
