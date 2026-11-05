import QtQuick
import PostApollo.StageDirector 1.0

// Instantiated ONLY by StationWatchBridgeGate after operator opt-in and
// presence of the native QML module. This runs in Weather's SAME Qt client.
// No browser process, video, compositor scene or input control is granted.
Item {
    id: adapter
    visible: false
    width: 0
    height: 0

    property rect viewport: Qt.rect(0, 0, 0, 0)
    property string sourceId: ""
    readonly property bool paired: nativeWatch.paired
    readonly property string bridgeStatus: nativeWatch.status
    property bool requestSent: false
    property bool closing: false

    function requestCurrent() {
        if (closing || requestSent || !nativeWatch.paired
                || nativeWatch.watchCandidate
                || (sourceId !== "bbc" && sourceId !== "cspan")
                || viewport.width <= 0 || viewport.height <= 0)
            return false;
        // Native implementation only accepts two catalog IDs. Returning
        // true means SENT, not that the compositor accepted a candidate.
        requestSent = nativeWatch.requestWatch(sourceId);
        return requestSent;
    }

    function revokeCurrent() {
        if (nativeWatch.paired && (requestSent || nativeWatch.watchCandidate)) {
            closing = true;
            nativeWatch.close();
        }
        requestSent = false;
    }

    onSourceIdChanged: {
        revokeCurrent();
        if (sourceId === "bbc" || sourceId === "cspan")
            Qt.callLater(requestCurrent);
    }
    onViewportChanged: {
        if (viewport.width > 0 && viewport.height > 0)
            Qt.callLater(requestCurrent);
        // Empty geometry goes to nativeWatch.viewport automatically;
        // never claim a viewport while the QML viewer is hidden.
    }

    WatchBridge {
        id: nativeWatch
        // The enclosing Gate only instantiates this object with optIn=true.
        enabled: true
        viewport: adapter.viewport
        onPairedChanged: {
            if (!paired) {
                adapter.requestSent = false;
                adapter.closing = false;
            } else {
                adapter.requestSent = false;
                Qt.callLater(adapter.requestCurrent);
            }
        }
    }

    Component.onCompleted: Qt.callLater(requestCurrent)
    Component.onDestruction: revokeCurrent()
}
