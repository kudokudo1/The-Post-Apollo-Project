import QtQuick
import Quickshell
import "widgets/weather"

// Actual Quickshell loading the ordinary gate with NO optional module.
ShellRoot {
    id: root
    property bool done: false
    FloatingWindow {
        title: "M32-WATCH-DEFAULT-OFF"
        visible: true
        implicitWidth: 320
        implicitHeight: 200
        StationWatchBridgeGate {
            id: gate
            optIn: false
            hostOpen: true
            viewport: Qt.rect(16, 16, 160, 95)
            sourceId: "bbc"
        }
    }
    Timer {
        interval: 210
        repeat: false
        running: true
        onTriggered: {
            if (gate.bridgeStatus === "DISABLED" && !gate.connected) {
                console.log("M32_PASS // OPTIONAL_NATIVE_PLUGIN_ABSENT_DEFAULT_OFF");
            } else {
                console.error("M32_FAIL // unexpected gate " + gate.bridgeStatus);
            }
            root.done = true;
        }
    }
    Timer {
        interval: 140
        repeat: false
        running: root.done
        onTriggered: Qt.quit()
    }
}
