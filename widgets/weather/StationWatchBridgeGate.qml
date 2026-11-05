import QtQuick

// M32 // NEVER import PostApollo.StageDirector in the ordinary Weather source.
// Optional native QML is loaded only when the operator has installed and
// explicitly enabled the matching SwayPX plugin on a Qt Wayland session.
Item {
    id: gate
    visible: false
    width: 0
    height: 0

    property bool optIn: false
    property bool hostOpen: false
    property rect viewport: Qt.rect(0, 0, 0, 0)
    property string sourceId: ""

    readonly property bool connected:
        nativeLoader.status === Loader.Ready && nativeLoader.item !== null
        && nativeLoader.item.paired === true
    readonly property string bridgeStatus:
        !optIn ? "DISABLED"
        : !hostOpen ? "HOST_CLOSED"
        : nativeLoader.status === Loader.Error ? "OPTIONAL_MODULE_UNAVAILABLE"
        : nativeLoader.status === Loader.Ready && nativeLoader.item
          ? nativeLoader.item.bridgeStatus : "AWAITING_MODULE"

    Loader {
        id: nativeLoader
        // On a machine without the optional plugin the source file is never
        // evaluated, so an ordinary Weather Station still compiles/opens.
        active: gate.optIn && gate.hostOpen
        source: active ? Qt.resolvedUrl("StationWatchNativeAdapter.qml") : ""
        onLoaded: {
            if (!item) return;
            item.viewport = Qt.binding(function() { return gate.viewport; });
            item.sourceId = Qt.binding(function() { return gate.sourceId; });
        }
    }
}
