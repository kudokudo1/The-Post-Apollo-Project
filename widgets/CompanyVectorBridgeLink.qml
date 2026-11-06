import QtQuick

// Company M26 // lazy optional adapter to SwayPX M25 PostApollo.CompanyVector.
// No static module import: a normal desktop with only M15/M17 installed must
// continue to load Company. Only an explicit integration opt-in attempts to
// instantiate the separately built, ABI-compatible Qt/QML plugin.
// This object never connects its own Wayland socket, launches a process,
// takes input focus, or claims that map pixels have been embedded.
Item {
    id: link
    visible: false
    width: 0
    height: 0

    property bool bridgeEnabled: false
    property rect frameRect: Qt.rect(0, 0, 0, 0)
    property rect mapRect: Qt.rect(0, 0, 0, 0)
    property var bridgeObject: null
    property string status: "DISABLED"
    readonly property bool wireBound:
        bridgeObject !== null && Boolean(bridgeObject.wireBound)
    readonly property bool viewportCandidate:
        bridgeObject !== null && Boolean(bridgeObject.viewportCandidate)
    readonly property bool launchCandidate:
        bridgeObject !== null && Boolean(bridgeObject.launchCandidate)

    function attachBridge() {
        if (!bridgeEnabled || bridgeObject !== null)
            return false;
        try {
            // This string, unlike a top-level QML import, is evaluated only
            // on explicit opt-in. Failure leaves existing Company operational.
            const object = Qt.createQmlObject(
                'import QtQuick\n'
                    + 'import PostApollo.CompanyVector 1.0\n'
                    + 'CompanyVectorBridge { enabled: false }',
                link, "CompanyVectorBridgeM26Optional");
            if (!object) {
                status = "OPTIONAL_BRIDGE_UNAVAILABLE";
                return false;
            }
            bridgeObject = object;
            pushGeometry();
            object.enabled = true;
            status = object.status;
            return true;
        } catch (error) {
            bridgeObject = null;
            status = "OPTIONAL_BRIDGE_UNAVAILABLE";
            return false;
        }
    }

    function detachBridge() {
        const object = bridgeObject;
        bridgeObject = null;
        if (object) {
            object.close();
            object.enabled = false;
            object.destroy();
        }
        status = "DISABLED";
    }

    function pushGeometry() {
        const object = bridgeObject;
        if (!object) return;
        object.frameRect = frameRect;
        // A zero mapRect is a deliberate hidden/invalid candidate.
        // M25 sends eight zeroes and cannot preserve stale crop geometry.
        object.mapRect = mapRect;
    }

    // Called only by the existing explicit OFFLINE TEST / ONLINE STREETS
    // action. Failure must not suppress or replace the M15 launcher.
    function requestIntent(online) {
        const object = bridgeObject;
        if (!bridgeEnabled || !object || !object.wireBound)
            return false;
        return object.requestLaunch(Boolean(online));
    }

    // Quickshell only passes the attached QProcess child PID here. The
    // optional native C++ bridge opens a genuine kernel pidfd and transfers
    // it over the existing QPA wl_client. Protocol v1 or missing plugin
    // returns false without interfering with the standalone native map.
    function reportChildPid(pid) {
        const object = bridgeObject;
        if (!bridgeEnabled || !object || !object.wireBound
                || typeof object.reportNativeChildPid !== "function")
            return false;
        const actual = Number(pid);
        if (!isFinite(actual) || actual <= 0
                || actual >= 2147483648 || Math.floor(actual) !== actual)
            return false;
        return object.reportNativeChildPid(actual);
    }

    function closeIntent() {
        const object = bridgeObject;
        if (bridgeEnabled && object)
            object.close();
    }

    onBridgeEnabledChanged: {
        if (bridgeEnabled)
            attachBridge();
        else
            detachBridge();
    }
    onFrameRectChanged: pushGeometry()
    onMapRectChanged: pushGeometry()
    Component.onCompleted: if (bridgeEnabled) attachBridge()
    Component.onDestruction: detachBridge()

    Connections {
        target: link.bridgeObject
        ignoreUnknownSignals: true
        function onStatusChanged() {
            if (link.bridgeObject)
                link.status = link.bridgeObject.status;
        }
    }
}
