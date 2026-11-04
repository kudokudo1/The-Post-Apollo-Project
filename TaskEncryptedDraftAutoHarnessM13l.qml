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
            console.log("M13L_NATIVE_QML_IPC_PASS");
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
                    console.log("M13L_PHASE_REPLY_PARSED");
                else
                    console.log("M13L_PHASE_BRIDGE_BUSY");
                return;
            }
            console.log("M13L_PHASE_BRIDGE_SETTLED");
            if (bridge.status === "REFUSED_HOST_EXIT_UNVERIFIED")
                console.warn("M13L_PHASE_HOST_EXIT_UNVERIFIED");
            else if (bridge.status === "REFUSED_HOST_RESPONSE")
                console.warn("M13L_PHASE_HOST_RESPONSE_INVALID");
            else if (bridge.status === "REFUSED_NOT_PRIVATE_TEST")
                console.warn("M13L_PHASE_PRIVATE_GATE_REFUSED");
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

    Component.onCompleted: {
        console.log("M13L_PHASE_QML_COMPONENT_LOADED");
        Qt.callLater(function() {
            if (harness.finished) return;
            harness.started = true;
            console.log("M13L_PHASE_START_ATTEMPT");
            if (!bridge.syntheticCIEligible) {
                console.warn("M13L_PHASE_ENV_GATE_DENIED");
                harness.finish("M13L_NATIVE_QML_IPC_REFUSED");
            } else if (!bridge.startSynthetic()) {
                console.warn("M13L_PHASE_PROCESS_START_REJECTED");
                harness.finish("M13L_NATIVE_QML_IPC_REFUSED");
            } else {
                console.log("M13L_PHASE_PROCESS_START_ACCEPTED");
            }
        });
    }
}
