import QtQuick
import Quickshell

// Standalone Team 5 runtime probe.
//
// Load this file explicitly as a Quickshell configuration when validating the
// provider. It does not import or instantiate AppControl.
//
// Expected healthy behavior:
// - persistent bridge reports READY when libatspi registration succeeds;
// - snapshots may contain LIBATSPI, DEVTOOLS and/or KITTY records depending on
//   what applications are actually running;
// - fallback discovery remains available when the bridge is not ready;
// - the probe exits after printing a final snapshot.
Scope {
    id: probeRoot

    property int snapshotCount: 0

    TabSurfaceProvider {
        id: provider
        active: true

        onSnapshotChanged: {
            probeRoot.snapshotCount += 1;

            console.log(
                "TEAM5 PROBE snapshot",
                probeRoot.snapshotCount,
                "tabs=" + tabs.length,
                "controls=" + controls.length,
                "bridgeReady=" + bridgeReady
            );

            for (let i = 0; i < tabs.length; i++) {
                const entry = tabs[i];
                const evidence = identityEvidence(entry);

                console.log(
                    "TEAM5 PROBE tab",
                    i,
                    evidence.provider,
                    evidence.providerKey,
                    String(entry.tabTitle || entry.name || ""),
                    "pids=" + evidence.processPids.join(",")
                );
            }
        }

        onDiagnosticsChanged: {
            console.log(
                "TEAM5 PROBE diagnostics",
                diagnostics.join(" | ")
            );
        }

        onBridgeErrorChanged: {
            if (bridgeError.length > 0)
                console.log(
                    "TEAM5 PROBE bridge error",
                    bridgeError
                );
        }

        onErrorTextChanged: {
            if (errorText.length > 0)
                console.log(
                    "TEAM5 PROBE fallback error",
                    errorText
                );
        }
    }

    Timer {
        interval: 8000
        running: true
        repeat: false

        onTriggered: {
            console.log(
                "TEAM5 PROBE final",
                "snapshots=" + probeRoot.snapshotCount,
                "tabs=" + provider.tabs.length,
                "controls=" + provider.controls.length,
                "bridgeReady=" + provider.bridgeReady,
                "loading=" + provider.loading
            );

            Qt.quit();
        }
    }
}
