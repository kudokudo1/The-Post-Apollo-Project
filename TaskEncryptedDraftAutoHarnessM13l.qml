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
            if (!harness.started || harness.finished || bridge.busy)
                return;
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
        onTriggered: harness.finish("M13L_NATIVE_QML_IPC_REFUSED")
    }

    Component.onCompleted: {
        Qt.callLater(function() {
            if (harness.finished) return;
            harness.started = true;
            if (!bridge.syntheticCIEligible || !bridge.startSynthetic())
                harness.finish("M13L_NATIVE_QML_IPC_REFUSED");
        });
    }
}
